# Napkin Runbook

## Curation Rules
- Re-prioritize on every read.
- Keep recurring, high-value notes only.
- Max 10 items per category.
- Each item includes date + "Do instead".

## Execution & Validation (Highest Priority)
1. **[2026-05-25] All python/pytest/eternity commands require `uv run`**
   Do instead: `uv run pytest -v`, `uv run eternity process`, `uv run python -c ...` — python is not in PATH, uv manages the venv.

2. **[2026-05-25] `.env` without `export` does not propagate to child processes**
   Do instead: `export $(grep -v '^#' .env | xargs) && uv run eternity ...` — `source .env` sets vars in shell only, not exported subprocesses.

3. **[2026-05-25] `yt-dlp extract_flat=True` returns `None` for `upload_date` on YouTube**
   Do instead: Use `item.get("upload_date") or ""` (not the default= form); treat empty upload_date as "include" in backfill filter rather than rejecting.

## Shell & Command Reliability
1. **[2026-05-25] FastAPI/Starlette TemplateResponse signature changed in Starlette 1.1.0**
   Do instead: `templates.TemplateResponse(request, "template.html", context_dict)` — `request` is first positional arg, NOT inside context dict.

2. **[2026-05-25] `grep` without `-F` and `--` treats query as regex and flag**
   Do instead: `["grep", "-rilF", "--", q, str(dir)]` — `-F` = fixed string, `--` = end of flags, prevents `q=--include=*` from being parsed as a grep option.

## Domain Behavior Guardrails
1. **[2026-05-25] Claude Code settings.json has no `crons` field**
   Do instead: Use `CronCreate(durable=True)` for persistent Claude-triggered crons, or add the shell commands to OS crontab/launchd directly.

2. **[2026-05-25] Anthropic Tier 1 rate limit: 30k tokens/min**
   Do instead: Process one episode at a time and wait 60s between batches; re-running `eternity process` is safe — transcripts are idempotent (skips if transcript.txt exists), summaries too (skips if summary.md exists).

3. **[2026-05-25] Path traversal via URL path params in FastAPI**
   Do instead: After building `path = KNOWLEDGE_DIR / user_input / ...`, call `_safe_path(path)` which asserts `resolved.is_relative_to(KNOWLEDGE_DIR.resolve())` before use.
