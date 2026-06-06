import pytest
from bot.analysis import build_snapshot, rank_snapshot, format_report, next_video_id

# ── next_video_id ──────────────────────────────────────────────────────────

def test_next_video_id_from_existing():
    cache = {"D1": {}, "D2": {}, "D6": {}}
    assert next_video_id(cache) == "D7"

def test_next_video_id_empty_cache():
    assert next_video_id({}) == "D1"

# ── build_snapshot ─────────────────────────────────────────────────────────

def test_build_snapshot_uses_hours_from_metrics():
    metrics = {"hours_since_post": 6, "views": 2000, "views_at_hour": 1800}
    snap = build_snapshot(metrics, "2024-01-01T18:00:00+00:00", None)
    assert snap["hours_since_post"] == 6
    assert snap["views"] == 2000
    assert snap["views_at_hour"] == 1800

def test_build_snapshot_calculates_hours_when_missing():
    metrics = {"hours_since_post": None, "views": 1500}
    snap = build_snapshot(
        metrics,
        "2024-01-01T18:00:00+00:00",
        "2024-01-01T12:00:00+00:00"
    )
    assert snap["hours_since_post"] == 6.0

def test_build_snapshot_null_hours_when_no_posted_at():
    metrics = {"hours_since_post": None, "views": 1500}
    snap = build_snapshot(metrics, "2024-01-01T18:00:00+00:00", None)
    assert snap["hours_since_post"] is None

def test_build_snapshot_includes_all_flat_fields():
    metrics = {"skipRate": 45.0, "likeRate": 3.2}
    snap = build_snapshot(metrics, "2024-01-01T18:00:00+00:00", None)
    assert "skipRate" in snap
    assert "likeRate" in snap

# ── rank_snapshot ──────────────────────────────────────────────────────────

CACHE_TWO_VIDEOS = {
    "D1": {
        "id": "D1", "name": "A", "posted_at": None,
        "snapshots": [{"hours_since_post": 6, "views": 5000, "views_at_hour": 4500, "skipRate": 55.0}]
    },
    "D2": {
        "id": "D2", "name": "B", "posted_at": None,
        "snapshots": [{"hours_since_post": 6, "views": 3000, "views_at_hour": 2800, "skipRate": 48.0}]
    },
}

def test_rank_snapshot_views_at_hour():
    snap = {"hours_since_post": 6, "views_at_hour": 2800, "views": 3000, "skipRate": 48.0}
    rankings = rank_snapshot(snap, "D2", CACHE_TWO_VIDEOS)
    # D1 has 4500, D2 has 2800 → D2 is #2
    assert rankings["views_at_hour"]["rank"] == 2
    assert rankings["views_at_hour"]["total"] == 2

def test_rank_snapshot_skip_rate_lower_is_better():
    snap = {"hours_since_post": 6, "skipRate": 48.0, "views": 3000}
    rankings = rank_snapshot(snap, "D2", CACHE_TWO_VIDEOS)
    # D1 has 55%, D2 has 48% → D2 is #1 (lower is better)
    assert rankings["skipRate"]["rank"] == 1

def test_rank_snapshot_no_comparables_returns_empty():
    cache = {"D1": {"id": "D1", "snapshots": []}}
    snap = {"hours_since_post": 6, "views": 1000}
    rankings = rank_snapshot(snap, "D1", cache)
    assert rankings == {}

def test_rank_snapshot_ignores_out_of_window_hours():
    # D1 has a snapshot at hour 24 — too far from hour 6 (window = max(6*0.25,1) = 1.5h)
    cache = {
        "D1": {"id": "D1", "snapshots": [{"hours_since_post": 24, "views": 9999}]},
    }
    snap = {"hours_since_post": 6, "views": 2000}
    rankings = rank_snapshot(snap, "D2", cache)
    assert "views" not in rankings

# ── format_report ──────────────────────────────────────────────────────────

def test_format_report_new_video():
    snap = {"hours_since_post": 6, "views_at_hour": 2324, "views": 2635}
    rankings = {"views_at_hour": {"rank": 2, "total": 5}}
    report = format_report("D7", "Meeting with KSI", snap, rankings, is_new=True)
    assert "Saved" in report
    assert "D7" in report
    assert "Hour 6" in report
    assert "#2 of 5" in report

def test_format_report_existing_video():
    snap = {"hours_since_post": 12, "views": 5000}
    rankings = {}
    report = format_report("D2", "Going after creators", snap, {}, is_new=False)
    assert "Updated" in report

def test_format_report_rank_1_shows_best_ever():
    snap = {"hours_since_post": 6, "skipRate": 40.0}
    rankings = {"skipRate": {"rank": 1, "total": 4}}
    report = format_report("D7", "Test", snap, rankings, is_new=True)
    assert "best ever" in report
