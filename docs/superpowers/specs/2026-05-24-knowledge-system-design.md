# Knowledge Discovery & Management System
**Date:** 2026-05-24
**Status:** Approved

## Overview

A local system that curates knowledge from YouTube channels. For each new episode it generates a structured summary of lessons with quotes and timestamps. A weekly synthesis agent consolidates lessons across episodes into a living knowledge base. A FastAPI web app lets you browse the wiki and jump to specific video moments.

---

## Directory Structure

```
eternity/
  knowledge/
    channels/
      tkk_podcast/
        episodes/
          2026-05-10_ep-title/
            transcript.txt
            summary.md
        channel.json
    master_lessons.md
    topics/
      decision-making.md
      leadership.md
      ...
    synthesis/
      2026-W21.md
  src/
    eternity/
      watcher.py
      fetcher.py
      summarizer.py
      synthesizer.py
      cli.py
      web/
        app.py
        templates/
  config/
    channels.yaml
  tests/
    fixtures/
    test_watcher.py
    test_fetcher.py
    test_summarizer.py
  pyproject.toml
  docs/
    superpowers/specs/
```

---

## Configuration

`config/channels.yaml` — one entry per channel. Adding a new channel requires only a new entry here.

```yaml
channels:
  - id: tkk_podcast
    name: The Knowledge Project Podcast
    url: https://www.youtube.com/@tkppodcast/videos
    check_frequency: daily
    filters:
      min_duration_minutes: 20
      max_duration_minutes: 180
      exclude_title_keywords: ["trailer", "clip", "highlight", "short"]
      backfill_days: 90
      max_episodes_per_run: 5
      max_transcript_tokens: 50000
```

---

## Data Formats

### `channel.json` — per-channel state
```json
{
  "last_checked": "2026-05-24T00:00:00Z",
  "errors": [
    {"video_id": "xyz789", "reason": "no transcript available", "attempted_at": "2026-05-24T10:00:00Z"}
  ]
}
```

### `episodes/<date>_<slug>/summary.md`
```markdown
# Episode Title
**Source:** [Watch on YouTube](https://youtube.com/watch?v=ID)
**Date:** 2026-05-10

## Lessons

### Lesson 1: Clear mental models reduce decision fatigue
> "When you have a framework, you stop relitigating the same decisions."
[Watch this moment →](https://youtube.com/watch?v=ID&t=312s)

Brief 1-2 sentence elaboration on why this lesson matters.

### Lesson 2: ...
```

### `master_lessons.md` — the living knowledge base
```markdown
# Master Lessons

_Last updated: 2026-W21 · 24 lessons across 3 channels_

## Decision Making
- **Clear mental models reduce decision fatigue** — when you have a framework, you stop relitigating the same decisions. ([TKP Ep. 142](channels/tkk_podcast/episodes/2026-05-10_ep-title/summary.md), [TKP Ep. 98](channels/tkk_podcast/episodes/2025-11-03_ep-title/summary.md))

## Learning
...
```

### `synthesis/YYYY-WXX.md` — weekly changelog
```markdown
# Week 21 Synthesis
Episodes reviewed: 3
New lessons added: 2
Lessons updated: 1

## Changes
- Added "decision fatigue" to topics/decision-making.md
- Merged two lessons on mental models in master_lessons.md
```

---

## Components

### `watcher.py`
Detects new episodes for a channel.

- Calls `yt-dlp --flat-playlist` to list recent videos with ID, title, duration, upload date
- Filters by `min_duration_minutes`, `max_duration_minutes`, `exclude_title_keywords`, `backfill_days`
- Checks filesystem: if `episodes/<date>_<slug>/` already exists, the episode is already processed — no ID list needed
- Respects `max_episodes_per_run` — returns at most N unprocessed videos per call
- Updates `last_checked` in `channel.json` after returning results

### `fetcher.py`
Downloads and normalises a transcript for a video ID.

- Primary: `yt-dlp --write-auto-sub --skip-download` → parses VTT into list of `{text, start_seconds}` segments
- Fallback: `youtube_transcript_api` if yt-dlp yields no subtitles
- Concatenates segments into plain text, preserving timestamp markers
- Saves to `episodes/<date>_<slug>/transcript.txt`
- If both sources fail, logs to `channel.json` errors list and raises so the caller can skip

### `summarizer.py`
Calls Claude API to generate a structured summary from a transcript.

- Checks for existing `summary.md` first — skips if already present (idempotent)
- Truncates transcript to `max_transcript_tokens` if needed (drops middle, keeps start and end)
- Uses prompt caching: system prompt is a cached prefix, transcript is the user turn
- Instructs Claude to extract 3-5 lessons, each with: title, 1-2 sentence summary, one direct quote, timestamp in seconds
- Parses response and writes `summary.md` with YouTube deep links (`&t=Xs`)

### `synthesizer.py`
Weekly consolidation of new summaries into the knowledge base.

- Determines last synthesis date from the most recent file in `synthesis/` (or epoch if none exist)
- Reads all `summary.md` files whose parent episode dir was created since last synthesis date
- Calls Claude API (with prompt caching) with: all new summaries + current `master_lessons.md`
- Claude identifies new lessons to add, existing lessons to update/merge, and topic assignments
- Updates `master_lessons.md` and relevant `topics/*.md` files in place
- Writes `synthesis/YYYY-WXX.md` as a changelog

### `cli.py`
Manual entry points. All also triggered by cron.

```bash
uv run python -m eternity process                        # all channels
uv run python -m eternity process --channel tkk_podcast  # one channel
uv run python -m eternity synthesize                     # run synthesis now
uv run python -m eternity serve                          # start web app
uv run python -m eternity serve --port 8080              # custom port
```

### `web/app.py`
FastAPI server. Reads directly from `knowledge/` — no database.

| Route | Description |
|---|---|
| `GET /` | Dashboard: recent episodes, latest synthesis |
| `GET /channels/{id}` | Episode list, sorted by date |
| `GET /channels/{id}/episodes/{slug}` | Rendered summary with timestamp links |
| `GET /lessons` | Rendered `master_lessons.md` |
| `GET /topics/{topic}` | Rendered topic file |
| `GET /synthesis` | List of weekly synthesis logs |
| `GET /search?q=...` | Grep-based full-text search across all markdown |

Markdown rendered server-side via `mistune`. Timestamp links open YouTube in a new tab. Runs on `localhost:8000` by default.

---

## Scheduling

Claude Code cron jobs in `.claude/settings.json`:

- **Daily** — runs `eternity process` for all channels
- **Weekly (Monday)** — runs `eternity synthesize`

Failed episodes (transcript fetch error, API error) are logged to the channel's errors list in `channel.json` and retried on the next run.

---

## Tooling

- **Runtime:** Python 3.12+, managed with `uv` + `pyproject.toml`
- **Key dependencies:** `yt-dlp`, `youtube-transcript-api`, `anthropic`, `fastapi`, `uvicorn`, `mistune`, `pyyaml`
- **Tests:** `pytest` with fixtures in `tests/fixtures/`

### Test coverage
- `test_watcher.py` — filter logic (duration, keywords, backfill, max_episodes_per_run)
- `test_fetcher.py` — VTT parsing, timestamp extraction, fallback logic
- `test_summarizer.py` — transcript truncation, summary.md generation (Claude mocked), idempotency check

Web app is a thin read-only layer — verified manually.

---

## Adding a New Channel

1. Add an entry to `config/channels.yaml`
2. Run `uv run python -m eternity process --channel <new_id>`
3. Done — the watcher creates `knowledge/channels/<new_id>/` automatically
