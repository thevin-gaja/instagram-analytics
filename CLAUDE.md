# Instagram Reels Analytics — Project Context

## What This Is

A personal analytics system for tracking Instagram Reel performance over time. Three components:

1. **Telegram bot** — you share screenshots of your Instagram analytics from your phone; it extracts the data and gives you a comparison report. You can also ask natural-language questions about your full video database.
2. **GitHub-hosted data store** — `metrics_cache.json` holds all video data; every bot submission is a git commit.
3. **Live dashboard** — `reels_dashboard.html` served via GitHub Pages, fetches `metrics_cache.json` at runtime and renders 4 interactive tabs of charts.

---

## Architecture

```
Phone (Telegram app)
    -> Telegram Bot (Python, Railway, 24/7)
        -> Claude Vision API (extracts metrics from screenshot)
        -> GitHub Repo (commits updated metrics_cache.json)
            -> GitHub Pages (reels_dashboard.html auto-updates in ~30s)
    -> Bot replies with ranked comparison report in Telegram
    -> "Ask a question" button -> Claude Sonnet Q&A over analytics summary
```

**Services:**
- **Railway** (free tier) — hosts the bot
- **GitHub + GitHub Pages** — data store and live dashboard
- **Claude API** — vision extraction (claude-opus-4-6) + Q&A (claude-sonnet-4-6)
- **Telegram Bot API** — free

---

## File Structure

```
/
├── bot/
│   ├── main.py          — entry point; env vars, Application setup, slash commands
│   ├── handlers.py      — ConversationHandler; photo flow, batch buffering, Q&A handlers
│   ├── vision.py        — Claude Vision (claude-opus-4-6); extracts metrics from screenshot
│   ├── github_store.py  — PyGithub wrapper; read/write metrics_cache.json
│   ├── analysis.py      — ranking logic, snapshot builder, report formatter
│   ├── analytics.py     — pre-computes analytics summary for Q&A context
│   ├── qa.py            — Claude Sonnet Q&A over analytics summary
│   └── migrate.py       — one-time migration (already run)
├── tests/
│   ├── test_analysis.py
│   ├── test_analytics.py
│   ├── test_migrate.py
│   └── test_vision.py
├── metrics_cache.json   — all video data (source of truth)
├── reels_dashboard.html — 4-tab interactive dashboard (fetches JSON at runtime)
├── requirements.txt
├── railway.toml         — Railway deployment config
└── docs/superpowers/
    ├── specs/           — design documents
    └── plans/           — implementation plans
```

---

## Current Video Roster

| ID  | Name                            | Notes                                      |
|-----|---------------------------------|--------------------------------------------|
| V1  | Day 1                           | Legacy; manual day-1/2/3 view counts only  |
| V2  | Day 2                           | Legacy                                     |
| V3  | Day 3                           | Legacy                                     |
| V4  | Day 4                           | Legacy                                     |
| V5  | Day 5                           | Legacy                                     |
| V6  | Day 6                           | Legacy                                     |
| V7  | Speak When I Name - blueshirt   | First bot-tracked video; posted_at set     |
| V8  | Day 7                           | Bot-tracked, single final-state snapshot   |
| V9  | Day 8                           | Bot-tracked, single final-state snapshot   |
| V10 | Day 10                          | Bot-tracked; has day-1 snapshot            |
| V11 | Aesthetic Reel 1                | Bot-tracked; has day-1 snapshot            |

---

## Data Model

`metrics_cache.json` stores one entry per video keyed by ID. Each video has a `snapshots[]` array — every screenshot submission appends one entry.

```json
{
  "V7": {
    "id": "V7",
    "name": "Speak When I Name - blueshirt",
    "posted_at": "2026-06-06T23:19:57.926734+00:00",
    "snapshots": [
      {
        "captured_at": "2026-06-07T00:19:57.926705+00:00",
        "hours_since_post": 1,
        "views_at_hour": 1376,
        "views": 1654,
        "reached": 740,
        "watchTime": 14,
        "follows": 0,
        "likes": 55,
        "...": "all other metrics"
      }
    ]
  }
}
```

**Key fields per snapshot:**
- `hours_since_post` — extracted from the Instagram graph tooltip in the screenshot (null on legacy final-state snapshots)
- `views_at_hour` — the pinned value shown on the views-over-time graph (null on final-state snapshots without graph data)
- All other fields (`skipRate`, `likeRate`, `ret3s`, etc.) — current running totals at screenshot time

**Legacy data (V1–V6):**
- Have three manually-entered snapshots at `hours_since_post: 24 / 48 / 72` with only `views_at_hour` filled in
- Plus one final-state snapshot with `hours_since_post: null` containing all engagement metrics
- Work for absolute comparisons; the timed snapshots participate in day-1/day-3 growth calculations

**Video IDs** auto-increment: V1, V2, V3... New IDs are assigned by the bot when you register a new video.

---

## Bot Features

### 1. Screenshot Logging
Send a screenshot in Telegram:
1. Bot shows two inline buttons: **New video** / **Existing video**
2. **New:** bot asks for a name (one text reply) -> extracts metrics -> saves -> sends report
3. **Existing:** bot shows button list of all videos -> you tap one -> extracts metrics -> saves -> sends report

### 2. Batch Uploads
Send multiple screenshots as a Telegram album — the bot buffers them (1-second debounce), processes all in sequence, and sends a single report with `-- Hour N --` section dividers.

### 3. Conversational Q&A
After any report, tap **"Ask a question"** -> ask natural-language questions about your full video database (e.g. "which video has the best skip rate?", "what's my day-1 multiplier trend?"). Powered by Claude Sonnet with a pre-computed analytics summary as context.

### 4. Ranking
Each snapshot is ranked against other videos' closest available snapshot at a similar hour (not final totals). Rankings are computed before the new snapshot is appended, so batch submissions don't compete against each other.

---

## Comparison Report Format

```
Saved — V7 · Hour 6

2,324 views at hour 6
#2 of 7 videos at this stage
skip rate 48.3% -> your best ever
like rate 5.4% -> #3 of 7
```

- For each metric, finds each other video's snapshot closest in time to the current hour
- Only videos with timed snapshots (`hours_since_post != null`) participate in time-based rankings
- Legacy null-hour snapshots excluded from timed comparisons

---

## Analytics Q&A

`bot/analytics.py` pre-computes a structured summary from the cache (per-video table, averages, chronological trend, rankings) before sending to Claude Sonnet. This gives reliable answers to questions like:
- Skip rate trend over time
- Day-1 multiplier per video
- Best/worst performers
- Follows per 1K views
- Weak spots in engagement

Pre-computation approach is deliberate: Python does the math; Claude interprets the results (avoids unreliable LLM arithmetic on raw JSON).

---

## Dashboard

`reels_dashboard.html` — fully client-side, 4-tab interactive dashboard built with Chart.js v4.5.0.

| Tab | Contents |
|-----|----------|
| **Overview** | 4 summary cards (video count, avg skip rate, avg day-1 views, avg 3s retention) + 4 horizontal bar charts (views, skip rate, 3s retention, like rate) |
| **Trends** | 3 line charts over V1->V11: skip rate / watch time / 3s retention, each with average dashed line |
| **Growth** | Grouped bar chart (day-1 / day-3 / current views) + multiplier table sorted by growth |
| **Video Detail** | Dropdown to pick any video; 6 metric cards with above/below-avg comparison; snapshot history line chart; full latest-snapshot metrics table |

Dashboard design: dark mode, accent colours `#E1306C` (pink) and `#833AB4` (purple), responsive grid layout.

---

## Environment Variables (Railway)

```
TELEGRAM_BOT_TOKEN    bot token from @BotFather
ANTHROPIC_API_KEY     Anthropic API key
GITHUB_TOKEN          GitHub PAT with repo read/write scope
GITHUB_REPO           thevin-gaja/instagram-analytics
```

---

## Running Locally

```bash
pip install -r requirements.txt

# Run tests
pytest -v

# Run bot (requires env vars exported)
export TELEGRAM_BOT_TOKEN=...
export ANTHROPIC_API_KEY=...
export GITHUB_TOKEN=...
export GITHUB_REPO=thevin-gaja/instagram-analytics
python -m bot.main

# Preview dashboard (fetch() requires a local server)
python3 -m http.server 8080
# open http://localhost:8080/reels_dashboard.html
```

---

## Design Decisions

- **GitHub as database** — avoids a separate DB; every update is a versioned commit with full history
- **Dashboard fetches JSON at runtime** — the bot never regenerates the HTML; GitHub Pages serves static files, JS does the work
- **Pre-computed analytics summary** — Python does the math before sending to Claude (reliable vs asking Claude to compute from raw JSON)
- **Closest-snapshot ranking** — compares against each video's nearest available timed snapshot, not a fixed time window
- **Rank-before-append** — each snapshot ranked against existing data before being added, so batch submissions don't compete against each other
- **Single screenshot per submission** — the Overview tab screenshot contains the graph tooltip with `hours_since_post`; other tabs (Engagement/Audience) can be submitted separately
- **Conversation state in memory** — `python-telegram-bot` ConversationHandler holds state in RAM on Railway; if Railway restarts mid-conversation, re-send the screenshot to restart the flow
