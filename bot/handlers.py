import io
from datetime import datetime, timezone, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from bot.github_store import load_cache, save_cache
from bot.vision import extract_metrics
from bot.analysis import next_video_id, build_snapshot, rank_snapshot, format_report

CHOOSING_TYPE, ENTERING_NAME, CHOOSING_VIDEO = range(3)


async def photo_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point: user sends a photo."""
    photo = update.message.photo[-1]  # highest resolution
    file = await context.bot.get_file(photo.file_id)
    buf = io.BytesIO()
    await file.download_to_memory(buf)
    context.user_data["image_bytes"] = buf.getvalue()

    keyboard = [[
        InlineKeyboardButton("✨ New video", callback_data="new"),
        InlineKeyboardButton("📂 Existing video", callback_data="existing"),
    ]]
    await update.message.reply_text(
        "Got it! Is this a new video or an existing one?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return CHOOSING_TYPE


async def new_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """User tapped 'New video'."""
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("What do you want to call this video?")
    return ENTERING_NAME


async def existing_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """User tapped 'Existing video' — show list of known videos."""
    await update.callback_query.answer()
    cache, _ = load_cache(context.bot_data["repo"])
    keyboard = [
        [InlineKeyboardButton(f"{vid_id} · {v['name']}", callback_data=f"vid_{vid_id}")]
        for vid_id, v in cache.items()
    ]
    await update.callback_query.edit_message_text(
        "Which video is this?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return CHOOSING_VIDEO


async def name_entered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """User typed the new video name."""
    context.user_data["video_name"] = update.message.text.strip()
    context.user_data["is_new"] = True
    msg = await update.message.reply_text("⏳ Processing...")
    await _process_and_reply(context, chat_id=update.message.chat_id)
    await msg.delete()
    return ConversationHandler.END


async def video_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """User tapped an existing video button."""
    await update.callback_query.answer()
    context.user_data["video_id"] = update.callback_query.data.replace("vid_", "")
    context.user_data["is_new"] = False
    await update.callback_query.edit_message_text("⏳ Processing...")
    await _process_and_reply(context, chat_id=update.callback_query.message.chat_id)
    return ConversationHandler.END


async def _process_and_reply(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """Extract metrics, save snapshot, send report."""
    repo = context.bot_data["repo"]
    api_key = context.bot_data["anthropic_key"]
    image_bytes = context.user_data["image_bytes"]
    is_new = context.user_data["is_new"]

    metrics = extract_metrics(image_bytes, api_key)
    cache, sha = load_cache(repo)
    now = datetime.now(timezone.utc).isoformat()

    if is_new:
        vid_id = next_video_id(cache)
        name = context.user_data["video_name"]
        hours = metrics.get("hours_since_post")
        posted_at = (
            (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
            if hours is not None
            else now
        )
        cache[vid_id] = {
            "id": vid_id,
            "name": name,
            "posted_at": posted_at,
            "snapshots": [],
        }
    else:
        vid_id = context.user_data["video_id"]
        posted_at = cache[vid_id].get("posted_at")

    snapshot = build_snapshot(metrics, now, posted_at)
    cache[vid_id]["snapshots"].append(snapshot)
    rankings = rank_snapshot(snapshot, vid_id, cache)
    save_cache(repo, cache, sha, f"snapshot: {vid_id} hour={snapshot.get('hours_since_post', '?')}")

    report = format_report(vid_id, cache[vid_id]["name"], snapshot, rankings, is_new)
    await context.bot.send_message(chat_id=chat_id, text=report)


def build_conversation_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[MessageHandler(filters.PHOTO, photo_received)],
        states={
            CHOOSING_TYPE: [
                CallbackQueryHandler(new_chosen, pattern="^new$"),
                CallbackQueryHandler(existing_chosen, pattern="^existing$"),
            ],
            ENTERING_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, name_entered)
            ],
            CHOOSING_VIDEO: [
                CallbackQueryHandler(video_selected, pattern="^vid_")
            ],
        },
        fallbacks=[],
        per_user=True,
    )
