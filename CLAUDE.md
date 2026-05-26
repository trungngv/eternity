# CLAUDE.md

## Project Overview

**Eternity** watches YouTube channels, downloads transcripts, generates structured lesson summaries via Claude, synthesizes them into a living knowledge base weekly, and serves it as a local web app.

**Pipeline:** `watcher → fetcher → summarizer → synthesizer`

**Stack:** Python 3.12+, uv, yt-dlp, youtube-transcript-api, click, fastapi, uvicorn, mistune, jinja2, pyyaml. No `anthropic` SDK — AI calls use the `claude` CLI directly.

---

## Key Commands

```bash
uv run pytest -v                               # run tests (always prefix with uv run)
uv run eternity fetch                          # check for new episodes & download transcripts
uv run eternity fetch --channel tkk_podcast    # single channel
uv run eternity summarize-episodes             # generate lesson summaries
uv run eternity summarize-episodes --channel tkk_podcast
uv run eternity synthesize                     # weekly KB consolidation
uv run eternity serve                          # web app at http://localhost:8000
```

---

## Architecture

| File | Role |
|---|---|
| `config/channels.yaml` | Channel configs (id, url, filters) |
| `src/eternity/config.py` | Loads channels.yaml → `Channel` dataclasses |
| `src/eternity/watcher.py` | Lists channel videos, filters by duration/title/backfill, skips processed |
| `src/eternity/fetcher.py` | Downloads transcript via yt-dlp (VTT), falls back to youtube-transcript-api |
| `src/eternity/summarizer.py` | Calls `claude` CLI → JSON lessons → writes `summary.md` |
| `src/eternity/synthesizer.py` | Calls `claude` CLI → updates `master_lessons.md`, topic files, synthesis log |
| `src/eternity/cli.py` | Click CLI: `process`, `synthesize`, `serve` |
| `src/eternity/web/app.py` | FastAPI: serves `knowledge/` as HTML |

---

## Data Layout

```
knowledge/
  channels/{channel_id}/
    channel.json              # centralized manifest: {last_checked, videos: [{video_id, title, url, fetched_date, summarized_date, error}]}
    episodes/{slug}/          # slug derived from title only (no date prefix)
      transcript.txt          # gitignored, idempotent (skip if exists)
      summary.md              # skip if exists
  topics/{slug}.md
  synthesis/{YYYY-WNN}.md
  master_lessons.md
config/channels.yaml
```

**Deduplication:** Videos tracked by `video_id` in `channel.json`. Already-fetched videos are skipped by comparing against `videos[].video_id`.

**Idempotency:** `transcript.txt` and `summary.md` never overwritten. Episodes without transcripts are skipped during summarization.

---

## AI Calls (claude CLI, not SDK)

Both `summarizer.py` and `synthesizer.py` use `_call_claude(system, user) -> str`:

```python
subprocess.run(
    ["claude", "-p", "--system-prompt", system, "--model", "claude-sonnet-4-6"],
    input=user, capture_output=True, text=True, timeout=300,
)
```

Uses the Pro account OAuth (keychain), not `ANTHROPIC_API_KEY`. Model is `claude-sonnet-4-6`.

Tests mock `eternity.summarizer._call_claude` / `eternity.synthesizer._call_claude` directly.

---

## Known Gotchas

- **All Python commands need `uv run`** — Python is not on PATH, uv manages the venv.
- **`yt-dlp` flat extract returns `None` for `upload_date`** — treat missing as "include" rather than reject in backfill filter; use `item.get("upload_date") or ""`.
- **FastAPI `TemplateResponse` signature**: `templates.TemplateResponse(request, "template.html", ctx)` — `request` is the first positional arg.
- **`grep` in web search**: use `-rilF --` flags — `-F` for fixed string, `--` to end flags (prevents query strings starting with `-` from being parsed as options).
- **Path traversal in web app**: `_safe_path()` in `web/app.py` validates all user-supplied path params are under `KNOWLEDGE_DIR`.
- **Rate limits**: Tier 1 is 30k tokens/min. Process one episode at a time; re-running is safe.

---

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.
