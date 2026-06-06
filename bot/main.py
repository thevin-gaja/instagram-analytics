import os
from telegram.ext import Application
from bot.github_store import get_repo
from bot.handlers import build_conversation_handler


def main() -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    anthropic_key = os.environ["ANTHROPIC_API_KEY"]
    github_token = os.environ["GITHUB_TOKEN"]
    github_repo = os.environ["GITHUB_REPO"]

    repo = get_repo(github_token, github_repo)

    app = Application.builder().token(token).build()
    app.bot_data["repo"] = repo
    app.bot_data["anthropic_key"] = anthropic_key

    app.add_handler(build_conversation_handler())

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
