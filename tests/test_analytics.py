import pytest
from bot.analytics import _latest_value, _day1_views, _avg, build_analytics_summary

# ── _latest_value ──────────────────────────────────────────────────────────

def test_latest_value_returns_most_recent_non_null():
    snaps = [{"views": 100}, {"views": None}, {"views": 200}]
    assert _latest_value(snaps, "views") == 200

def test_latest_value_skips_nulls():
    snaps = [{"views": 100}, {"views": None}]
    assert _latest_value(snaps, "views") == 100

def test_latest_value_all_null_returns_none():
    snaps = [{"views": None}, {"views": None}]
    assert _latest_value(snaps, "views") is None

def test_latest_value_empty_snapshots():
    assert _latest_value([], "views") is None

# ── _day1_views ────────────────────────────────────────────────────────────

def test_day1_views_picks_closest_to_hour_24():
    snaps = [
        {"hours_since_post": 6, "views_at_hour": 1000},
        {"hours_since_post": 24, "views_at_hour": 4500},
        {"hours_since_post": 48, "views_at_hour": 7000},
    ]
    assert _day1_views(snaps) == 4500

def test_day1_views_no_timed_snapshots_returns_none():
    snaps = [{"hours_since_post": None, "views_at_hour": 5000}]
    assert _day1_views(snaps) is None

def test_day1_views_no_views_at_hour_returns_none():
    snaps = [{"hours_since_post": 24, "views_at_hour": None}]
    assert _day1_views(snaps) is None

def test_day1_views_empty_returns_none():
    assert _day1_views([]) is None

# ── _avg ───────────────────────────────────────────────────────────────────

def test_avg_ignores_nulls():
    assert _avg([10, None, 30]) == 20.0

def test_avg_all_nulls_returns_none():
    assert _avg([None, None]) is None

def test_avg_empty_returns_none():
    assert _avg([]) is None

# ── build_analytics_summary ────────────────────────────────────────────────

MINIMAL_CACHE = {
    "V1": {
        "id": "V1", "name": "Day 1",
        "snapshots": [
            {"hours_since_post": 24, "views_at_hour": 4722, "views": None},
            {"hours_since_post": None, "views": 5548, "skipRate": 50.0,
             "likeRate": 3.0, "watchTime": 10, "ret3s": 55.0, "follows": 5},
        ],
    },
    "V2": {
        "id": "V2", "name": "Day 2",
        "snapshots": [
            {"hours_since_post": 24, "views_at_hour": 5454, "views": None},
            {"hours_since_post": None, "views": 8305, "skipRate": 48.0,
             "likeRate": 4.0, "watchTime": 12, "ret3s": 60.0, "follows": 10},
        ],
    },
}

def test_summary_contains_per_video_table():
    summary = build_analytics_summary(MINIMAL_CACHE)
    assert "Per-Video Metrics" in summary
    assert "Day 1" in summary
    assert "Day 2" in summary

def test_summary_contains_averages():
    summary = build_analytics_summary(MINIMAL_CACHE)
    assert "Averages" in summary

def test_summary_contains_rankings():
    summary = build_analytics_summary(MINIMAL_CACHE)
    assert "Rankings" in summary

def test_summary_multiplier_calculated():
    summary = build_analytics_summary(MINIMAL_CACHE)
    # V1: 5548 / 4722 ≈ 1.2x
    assert "1.2x" in summary

def test_summary_dash_for_missing_data():
    cache = {"V1": {"id": "V1", "name": "Day 1", "snapshots": [
        {"hours_since_post": None, "views": 1000},
    ]}}
    summary = build_analytics_summary(cache)
    assert "—" in summary

def test_summary_empty_cache():
    summary = build_analytics_summary({})
    assert "Per-Video Metrics" in summary
    # No rows, no crash
