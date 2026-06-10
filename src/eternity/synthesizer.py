# src/eternity/synthesizer.py
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


SYSTEM_PROMPT = """You are a knowledge synthesizer. You maintain a living knowledge base of lessons from podcast episodes.

Given new episode summaries and the current knowledge base, update the knowledge base by:
1. Adding new lessons not already present
2. Merging or updating existing lessons when new episodes add nuance
3. Assigning lessons to topic categories

Respond with JSON only:
{
  "master_lessons_md": "full updated content of master_lessons.md",
  "topic_updates": {
    "topic-slug": "full content of topics/topic-slug.md"
  },
  "synthesis_summary": {
    "episodes_reviewed": N,
    "lessons_added": N,
    "lessons_updated": N,
    "changes": ["description of each change"]
  }
}"""


def _call_claude(system: str, user: str) -> str:
    result = subprocess.run(
        ["claude", "-p", "--system-prompt", system, "--model", "claude-haiku-4-5"],
        input=user,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude command failed: {result.stderr[:500]}")
    return result.stdout.strip()


def _get_last_synthesis_date(synthesis_dir: Path) -> datetime | None:
    if not synthesis_dir.exists():
        return None
    files = sorted(synthesis_dir.glob("*.md"), reverse=True)
    if not files:
        return None
    return datetime.fromtimestamp(files[0].stat().st_mtime, tz=timezone.utc)


def _collect_new_summaries(knowledge_dir: Path, since: datetime | None) -> list[Path]:
    summaries = []
    for summary in knowledge_dir.glob("channels/*/episodes/*/summary.md"):
        if since is None:
            summaries.append(summary)
        else:
            mtime = datetime.fromtimestamp(summary.stat().st_mtime, tz=timezone.utc)
            if mtime > since:
                summaries.append(summary)
    return summaries


def run_synthesis(knowledge_dir: Path) -> None:
    synthesis_dir = knowledge_dir / "synthesis"
    synthesis_dir.mkdir(exist_ok=True)

    last_synthesis = _get_last_synthesis_date(synthesis_dir)
    new_summaries = _collect_new_summaries(knowledge_dir, since=last_synthesis)

    if not new_summaries:
        return

    master_path = knowledge_dir / "master_lessons.md"
    current_kb = master_path.read_text() if master_path.exists() else "# Master Lessons\n"

    summaries_text = "\n\n---\n\n".join(p.read_text() for p in new_summaries)
    user_content = f"Current knowledge base:\n{current_kb}\n\n---\n\nNew episode summaries:\n{summaries_text}"

    raw_text = _call_claude(SYSTEM_PROMPT, user_content)
    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[-1]
        raw_text = raw_text.rsplit("```", 1)[0]

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Synthesis failed: Claude returned unparseable JSON: {e}\n{raw_text[:200]}") from e
    master_path.write_text(data["master_lessons_md"])

    topics_dir = knowledge_dir / "topics"
    topics_dir.mkdir(exist_ok=True)
    for slug, content in data.get("topic_updates", {}).items():
        (topics_dir / f"{slug}.md").write_text(content)

    summary = data["synthesis_summary"]
    week = datetime.now(tz=timezone.utc).strftime("%Y-W%W")
    lines = [
        f"# Week {week} Synthesis",
        f"episodes_reviewed: {summary['episodes_reviewed']}",
        f"lessons_added: {summary['lessons_added']}",
        f"lessons_updated: {summary['lessons_updated']}",
        "",
        "## Changes",
    ] + [f"- {c}" for c in summary["changes"]]
    (synthesis_dir / f"{week}.md").write_text("\n".join(lines))
