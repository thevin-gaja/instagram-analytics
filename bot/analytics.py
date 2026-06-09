from typing import Optional


def _latest_value(snapshots: list, field: str):
    """Return the most recent non-null value for a field across snapshots."""
    for snap in reversed(snapshots):
        val = snap.get(field)
        if val is not None:
            return val
    return None


def _day1_views(snapshots: list) -> Optional[float]:
    """Return views_at_hour from the snapshot closest to hour 24."""
    timed = [s for s in snapshots
             if s.get("hours_since_post") is not None and s.get("views_at_hour") is not None]
    if not timed:
        return None
    closest = min(timed, key=lambda s: abs(s["hours_since_post"] - 24))
    return closest["views_at_hour"]


def _avg(values: list) -> Optional[float]:
    nums = [v for v in values if v is not None]
    return round(sum(nums) / len(nums), 1) if nums else None


def build_analytics_summary(cache: dict) -> str:
    rows = []
    for vid_id, video in cache.items():
        snaps = video.get("snapshots", [])
        cur_views = _latest_value(snaps, "views")
        d1 = _day1_views(snaps)
        multiplier = round(cur_views / d1, 1) if cur_views and d1 else None
        follows = _latest_value(snaps, "follows")
        f_per_1k = round(follows / cur_views * 1000, 2) if follows and cur_views else None
        rows.append({
            "id": vid_id,
            "name": video.get("name", vid_id),
            "day1_views": d1,
            "current_views": cur_views,
            "day1_multiplier": multiplier,
            "watch_time": _latest_value(snaps, "watchTime"),
            "skip_rate": _latest_value(snaps, "skipRate"),
            "like_rate": _latest_value(snaps, "likeRate"),
            "ret3s": _latest_value(snaps, "ret3s"),
            "follows_per_1k": f_per_1k,
        })

    def fmt(v, suffix=""):
        return f"{v}{suffix}" if v is not None else "—"

    lines = ["# Instagram Reels Analytics Summary", ""]

    lines.append("## Per-Video Metrics")
    lines.append("| ID | Name | Day-1 Views | Current Views | Day-1 Multiplier | Watch Time | Skip Rate | Like Rate | Ret3s | Follows/1K |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        lines.append(
            f"| {r['id']} | {r['name']} | {fmt(r['day1_views'])} | {fmt(r['current_views'])} "
            f"| {fmt(r['day1_multiplier'], 'x')} | {fmt(r['watch_time'], 's')} "
            f"| {fmt(r['skip_rate'], '%')} | {fmt(r['like_rate'], '%')} "
            f"| {fmt(r['ret3s'], '%')} | {fmt(r['follows_per_1k'])} |"
        )

    lines += ["", "## Averages (across videos with data)"]
    for field, label in [
        ("day1_views", "Day-1 views"),
        ("current_views", "Current views"),
        ("watch_time", "Watch time (s)"),
        ("skip_rate", "Skip rate (%)"),
        ("like_rate", "Like rate (%)"),
        ("ret3s", "3s retention (%)"),
        ("follows_per_1k", "Follows per 1K views"),
    ]:
        avg = _avg([r[field] for r in rows])
        lines.append(f"- {label}: {avg if avg is not None else '—'}")

    lines += ["", "## Chronological Trend (V1 = oldest)"]
    lines.append("| ID | Name | Skip Rate | Watch Time | Ret3s |")
    lines.append("|---|---|---|---|---|")
    for r in rows:
        lines.append(
            f"| {r['id']} | {r['name']} | {fmt(r['skip_rate'], '%')} "
            f"| {fmt(r['watch_time'], 's')} | {fmt(r['ret3s'], '%')} |"
        )

    lines += ["", "## Rankings"]
    for field, label, direction in [
        ("skip_rate", "Skip Rate", "lower"),
        ("like_rate", "Like Rate", "higher"),
        ("watch_time", "Watch Time", "higher"),
        ("ret3s", "3s Retention", "higher"),
        ("day1_views", "Day-1 Views", "higher"),
        ("current_views", "Current Views", "higher"),
    ]:
        with_data = [(r["name"], r[field]) for r in rows if r[field] is not None]
        if not with_data:
            continue
        sorted_rows = sorted(with_data, key=lambda x: x[1], reverse=(direction == "higher"))
        top = ", ".join(f"{n} ({v})" for n, v in sorted_rows[:3])
        bottom = ", ".join(f"{n} ({v})" for n, v in sorted_rows[-3:])
        lines.append(f"**{label}** — Best: {top} | Worst: {bottom}")

    return "\n".join(lines)
