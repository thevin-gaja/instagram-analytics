import json
import pytest
from bot.migrate import migrate

FLAT_CACHE = {
    "D1": {
        "day": "D1",
        "story": "Agency launch",
        "views": 7056,
        "reached": 3418,
        "reelLength": 12,
        "watchTime": 9,
        "follows": 6,
        "topSource": "Feed (28.1%)",
        "skipRate": 59.8,
        "likeRate": 4.4,
        "shareRate": 1.0,
        "saveRate": 0.2,
        "repostRate": 0.4,
        "commentRate": 0.6,
        "ret3s": 49,
        "retEnd": 25,
        "profileVisits": 538,
        "likes": 186,
        "comments": 26,
        "reposts": 17,
        "shares": 42,
        "saves": 7,
        "nonFollower": 78.2,
        "ageBracket": "18-24 (57.4%)"
    }
}


def test_migrate_creates_snapshots_array():
    result = migrate(FLAT_CACHE)
    assert "snapshots" in result["D1"]
    assert isinstance(result["D1"]["snapshots"], list)
    assert len(result["D1"]["snapshots"]) == 1


def test_migrate_preserves_metrics_in_snapshot():
    result = migrate(FLAT_CACHE)
    snap = result["D1"]["snapshots"][0]
    assert snap["views"] == 7056
    assert snap["skipRate"] == 59.8
    assert snap["ageBracket"] == "18-24 (57.4%)"


def test_migrate_sets_null_temporal_fields():
    result = migrate(FLAT_CACHE)
    snap = result["D1"]["snapshots"][0]
    assert snap["hours_since_post"] is None
    assert snap["views_at_hour"] is None
    assert snap["captured_at"] is None


def test_migrate_uses_story_as_name():
    result = migrate(FLAT_CACHE)
    assert result["D1"]["name"] == "Agency launch"


def test_migrate_sets_null_posted_at():
    result = migrate(FLAT_CACHE)
    assert result["D1"]["posted_at"] is None


def test_migrate_is_idempotent():
    first = migrate(FLAT_CACHE)
    second = migrate(first)
    assert first == second


def test_migrate_preserves_already_migrated_entries():
    already_migrated = {
        "D1": {
            "id": "D1",
            "name": "Agency launch",
            "posted_at": None,
            "snapshots": [{"views": 7056, "hours_since_post": None}]
        }
    }
    result = migrate(already_migrated)
    assert result["D1"]["snapshots"][0]["views"] == 7056
    assert len(result["D1"]["snapshots"]) == 1
