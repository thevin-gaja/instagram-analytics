FLAT_FIELDS = [
    "views", "reached", "reelLength", "watchTime", "follows", "topSource",
    "skipRate", "likeRate", "shareRate", "saveRate", "repostRate", "commentRate",
    "ret3s", "retEnd", "profileVisits", "likes", "comments", "reposts",
    "shares", "saves", "nonFollower", "ageBracket",
]


def migrate(cache: dict) -> dict:
    """Convert flat video entries to time-series format. Idempotent."""
    result = {}
    for vid_id, data in cache.items():
        if "snapshots" in data:
            result[vid_id] = data
            continue
        snapshot = {
            "captured_at": None,
            "hours_since_post": None,
            "views_at_hour": None,
            **{k: data.get(k) for k in FLAT_FIELDS},
        }
        result[vid_id] = {
            "id": vid_id,
            "name": data.get("story", data.get("name", "")),
            "posted_at": None,
            "snapshots": [snapshot],
        }
    return result
