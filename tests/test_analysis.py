import pytest
from bot.analysis import build_snapshot, rank_snapshot, format_report, next_video_id, format_batch_report

# ── next_video_id ──────────────────────────────────────────────────────────

def test_next_video_id_from_existing():
    cache = {"V1": {}, "V2": {}, "V6": {}}
    assert next_video_id(cache) == "V7"

def test_next_video_id_empty_cache():
    assert next_video_id({}) == "V1"

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
    "V1": {
        "id": "V1", "name": "A", "posted_at": None,
        "snapshots": [{"hours_since_post": 6, "views": 5000, "views_at_hour": 4500, "skipRate": 55.0}]
    },
    "V2": {
        "id": "V2", "name": "B", "posted_at": None,
        "snapshots": [{"hours_since_post": 6, "views": 3000, "views_at_hour": 2800, "skipRate": 48.0}]
    },
}

def test_rank_snapshot_views_at_hour():
    snap = {"hours_since_post": 6, "views_at_hour": 2800, "views": 3000, "skipRate": 48.0}
    rankings = rank_snapshot(snap, "V2", CACHE_TWO_VIDEOS)
    # D1 has 4500, D2 has 2800 → D2 is #2
    assert rankings["views_at_hour"]["rank"] == 2
    assert rankings["views_at_hour"]["total"] == 2

def test_rank_snapshot_skip_rate_lower_is_better():
    snap = {"hours_since_post": 6, "skipRate": 48.0, "views": 3000}
    rankings = rank_snapshot(snap, "V2", CACHE_TWO_VIDEOS)
    # D1 has 55%, D2 has 48% → D2 is #1 (lower is better)
    assert rankings["skipRate"]["rank"] == 1

def test_rank_snapshot_no_comparables_returns_empty():
    cache = {"V1": {"id": "V1", "snapshots": []}}
    snap = {"hours_since_post": 6, "views": 1000}
    rankings = rank_snapshot(snap, "V1", cache)
    assert rankings == {}

def test_rank_snapshot_uses_closest_snapshot_per_video():
    # D1 only has a snapshot at hour 24 — new logic uses closest available, not a strict window
    cache = {
        "V1": {"id": "V1", "snapshots": [{"hours_since_post": 24, "views": 9999}]},
    }
    snap = {"hours_since_post": 6, "views": 2000}
    rankings = rank_snapshot(snap, "V2", cache)
    # D1's hour-24 is closest available → included → D2's 2000 loses to 9999 → rank 2
    assert rankings["views"]["rank"] == 2
    assert rankings["views"]["total"] == 2

def test_rank_snapshot_excludes_null_hour_videos_when_timed():
    # When current snapshot has hours, videos with only null-hour snapshots are excluded
    cache = {
        "V1": {"id": "V1", "snapshots": [{"hours_since_post": None, "views": 9999}]},
    }
    snap = {"hours_since_post": 6, "views": 2000}
    rankings = rank_snapshot(snap, "V2", cache)
    assert "views" not in rankings

def test_rank_snapshot_uses_one_snapshot_per_video():
    # Video with multiple snapshots — only the closest one is used, not both
    cache = {
        "V1": {"id": "V1", "snapshots": [
            {"hours_since_post": 6, "views": 3000},
            {"hours_since_post": 24, "views": 8000},
        ]},
    }
    snap = {"hours_since_post": 6, "views": 5000}
    rankings = rank_snapshot(snap, "V2", cache)
    # D1's closest to hour 6 is their hour-6 snapshot (views=3000), not hour-24
    # Our 5000 > their 3000 → rank 1 of 2
    assert rankings["views"]["rank"] == 1
    assert rankings["views"]["total"] == 2

# ── format_report ──────────────────────────────────────────────────────────

def test_format_report_new_video():
    snap = {"hours_since_post": 6, "views_at_hour": 2324, "views": 2635}
    rankings = {"views_at_hour": {"rank": 2, "total": 5}}
    report = format_report("V7", "Meeting with KSI", snap, rankings, is_new=True)
    assert "Saved" in report
    assert "V7" in report
    assert "Hour 6" in report
    assert "#2 of 5" in report

def test_format_report_existing_video():
    snap = {"hours_since_post": 12, "views": 5000}
    rankings = {}
    report = format_report("V2", "Going after creators", snap, {}, is_new=False)
    assert "Updated" in report

def test_format_report_rank_1_shows_best_ever():
    snap = {"hours_since_post": 6, "skipRate": 40.0}
    rankings = {"skipRate": {"rank": 1, "total": 4}}
    report = format_report("V7", "Test", snap, rankings, is_new=True)
    assert "best ever" in report

def test_rank_snapshot_tie_gives_same_rank():
    # Both videos have same views_at_hour — both should be rank 1
    cache = {
        "V1": {"id": "V1", "snapshots": [{"hours_since_post": 6, "views_at_hour": 2324}]},
    }
    snap = {"hours_since_post": 6, "views_at_hour": 2324}
    rankings = rank_snapshot(snap, "V2", cache)
    assert rankings["views_at_hour"]["rank"] == 1

def test_format_report_hours_zero():
    snap = {"hours_since_post": 0, "views_at_hour": 500, "views": 500}
    rankings = {}
    report = format_report("V7", "Test", snap, {"views_at_hour": {"rank": 1, "total": 2}}, is_new=True)
    assert "Hour 0" in report

def test_format_report_total_one_skips_ranking():
    snap = {"hours_since_post": 6, "skipRate": 45.0}
    rankings = {"skipRate": {"rank": 1, "total": 1}}
    report = format_report("V7", "Test", snap, rankings, is_new=True)
    # When total == 1, ranking line should NOT appear
    assert "skip rate" not in report

# ── format_batch_report ────────────────────────────────────────────────────

def test_format_batch_report_single_snapshot():
    snap = {"hours_since_post": 6, "views_at_hour": 2324, "views": 2635}
    rankings = {"views_at_hour": {"rank": 2, "total": 5}}
    report = format_batch_report("V7", "Test Video", [(snap, rankings)], is_new=True)
    assert "1 snapshot" in report
    assert "Saved" in report
    assert "V7" in report
    # No section divider for a single snapshot
    assert "──" not in report


def test_format_batch_report_multiple_snapshots_has_dividers():
    snap1 = {"hours_since_post": 6, "views_at_hour": 2324, "views": 2635}
    snap2 = {"hours_since_post": 24, "views_at_hour": 11300, "views": 12000}
    rankings1 = {"views_at_hour": {"rank": 2, "total": 5}}
    rankings2 = {"views_at_hour": {"rank": 1, "total": 5}}
    report = format_batch_report("V7", "Test Video", [(snap1, rankings1), (snap2, rankings2)], is_new=True)
    assert "2 snapshots" in report
    assert "── Hour 6 ──" in report
    assert "── Hour 24 ──" in report


def test_format_batch_report_sorted_by_hour():
    # Pass hour 24 first, hour 6 second — output must have hour 6 before hour 24
    snap_h24 = {"hours_since_post": 24, "views_at_hour": 11300, "views": 12000}
    snap_h6 = {"hours_since_post": 6, "views_at_hour": 2324, "views": 2635}
    rankings = {}
    report = format_batch_report(
        "V7", "Test Video",
        [(snap_h24, rankings), (snap_h6, rankings)],
        is_new=True,
    )
    pos_h6 = report.index("── Hour 6 ──")
    pos_h24 = report.index("── Hour 24 ──")
    assert pos_h6 < pos_h24


def test_format_batch_report_none_hours_sort_last():
    snap_hours = {"hours_since_post": 6, "views_at_hour": 2324, "views": 2635}
    snap_none = {"hours_since_post": None, "views": 5000}
    rankings = {}
    report = format_batch_report(
        "V7", "Test Video",
        [(snap_none, rankings), (snap_hours, rankings)],
        is_new=True,
    )
    pos_hour6 = report.index("── Hour 6 ──")
    pos_snapshot = report.index("── snapshot ──")
    assert pos_hour6 < pos_snapshot


def test_format_batch_report_updated_label():
    snap = {"hours_since_post": 12, "views": 5000}
    rankings = {}
    report = format_batch_report("V2", "Old Video", [(snap, rankings)], is_new=False)
    assert "Updated" in report
    assert "Saved" not in report
