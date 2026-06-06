from datetime import datetime, timezone
from typing import Optional

FLAT_METRICS = [
    "views", "reached", "reelLength", "watchTime", "follows", "topSource",
    "skipRate", "likeRate", "shareRate", "saveRate", "repostRate", "commentRate",
    "ret3s", "retEnd", "profileVisits", "likes", "comments", "reposts",
    "shares", "saves", "nonFollower", "ageBracket", "views_at_hour",
]

RANKED_METRICS = {
    "views_at_hour": "higher",
    "views": "higher",
    "reached": "higher",
    "skipRate": "lower",
    "likeRate": "higher",
    "follows": "higher",
    "shareRate": "higher",
}

METRIC_LABELS = {
    "views_at_hour": ("📊", "views at this stage"),
    "views": ("📊", "total views"),
    "skipRate": ("⏭️", "skip rate"),
    "likeRate": ("❤️", "like rate"),
    "reached": ("👁️", "reach"),
    "follows": ("➕", "follows"),
    "shareRate": ("↗️", "share rate"),
}


def next_video_id(cache: dict) -> str:
    """Return the next sequential video ID (D7, D8, ...)."""
    nums = [int(k[1:]) for k in cache if k.startswith("D") and k[1:].isdigit()]
    return f"D{max(nums) + 1}" if nums else "D1"


def build_snapshot(metrics: dict, captured_at: str, posted_at: Optional[str]) -> dict:
    """Build a snapshot dict from extracted metrics and timing context."""
    hours_since_post = metrics.get("hours_since_post")
    if hours_since_post is None and posted_at:
        try:
            posted = datetime.fromisoformat(posted_at.replace("Z", "+00:00"))
            captured = datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
            delta = (captured - posted).total_seconds() / 3600
            hours_since_post = round(delta, 1)
        except (ValueError, TypeError):
            pass

    return {
        "captured_at": captured_at,
        "hours_since_post": hours_since_post,
        **{k: metrics.get(k) for k in FLAT_METRICS},
    }


def _comparable_values(metric: str, hours: Optional[float], vid_id: str, cache: dict) -> list:
    """Collect metric values from other videos' snapshots within the time window."""
    result = []
    for other_id, video in cache.items():
        if other_id == vid_id:
            continue
        for snap in video.get("snapshots", []):
            val = snap.get(metric)
            snap_hours = snap.get("hours_since_post")
            if val is None:
                continue
            if hours is not None and snap_hours is not None:
                window = max(hours * 0.25, 1.0)
                if abs(snap_hours - hours) > window:
                    continue
            result.append(val)
    return result


def rank_snapshot(snapshot: dict, vid_id: str, cache: dict) -> dict:
    """Compute rankings for key metrics against comparable snapshots."""
    hours = snapshot.get("hours_since_post")
    rankings = {}
    for metric, direction in RANKED_METRICS.items():
        val = snapshot.get(metric)
        if val is None:
            continue
        comparables = _comparable_values(metric, hours, vid_id, cache)
        if not comparables:
            continue
        all_vals = sorted(comparables + [val], reverse=(direction == "higher"))
        rank = all_vals.index(val) + 1
        rankings[metric] = {"rank": rank, "total": len(all_vals)}
    return rankings


def format_report(vid_id: str, name: str, snapshot: dict, rankings: dict, is_new: bool) -> str:
    """Format the Telegram comparison report message."""
    action = "Saved" if is_new else "Updated"
    hours = snapshot.get("hours_since_post")
    hour_label = f"Hour {int(hours)}" if hours is not None else "snapshot"

    lines = [f"✅ {action} — {vid_id} · {hour_label}", ""]

    views_at_hour = snapshot.get("views_at_hour")
    views = snapshot.get("views")
    if views_at_hour and hours:
        lines.append(f"{int(views_at_hour):,} views at hour {int(hours)}")
    elif views:
        lines.append(f"{int(views):,} total views")

    for metric, (icon, label) in METRIC_LABELS.items():
        r = rankings.get(metric)
        if r is None:
            continue
        val = snapshot.get(metric)
        if val is None:
            continue
        rank, total = r["rank"], r["total"]
        pct_suffix = "%" if metric in ("skipRate", "likeRate", "shareRate") else ""
        rank_str = "your best ever" if rank == 1 and total > 1 else f"#{rank} of {total} videos at this stage"
        lines.append(f"{icon} {label} {val}{pct_suffix} → {rank_str}")

    return "\n".join(lines)
