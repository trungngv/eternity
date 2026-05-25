# src/eternity/summarizer.py
import json
import subprocess
from pathlib import Path


SYSTEM_PROMPT = """You are a knowledge curator. Given a podcast transcript, extract 5-10 key lessons.

For each lesson:
1. A concise title (5-10 words)
2. 1-2 sentences explaining the lesson and why it matters
3. One direct quote from the transcript that illustrates it
4. The timestamp in seconds of that quote (use the [H:MM] markers — convert to total seconds)

Respond with JSON only, no other text:
{
  "lessons": [
    {
      "title": "...",
      "summary": "...",
      "quote": "...",
      "timestamp_seconds": 123
    }
  ]
}"""


def _truncate_transcript(transcript: str, max_tokens: int) -> str:
    words = transcript.split()
    estimated_tokens = len(words) * 1.3
    if estimated_tokens <= max_tokens:
        return transcript.strip()
    max_words = int(max_tokens / 1.3)
    keep = max_words // 2
    return " ".join(words[:keep]) + " [...transcript truncated...] " + " ".join(words[-keep:])


def _call_claude(system: str, user: str) -> str:
    result = subprocess.run(
        ["claude", "-p", "--system-prompt", system, "--model", "claude-sonnet-4-6"],
        input=user,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude command failed: {result.stderr[:500]}")
    return result.stdout.strip()


def summarize_episode(
    video_id: str,
    video_title: str,
    video_url: str,
    upload_date: str,
    transcript_path: Path,
    summary_path: Path,
    max_tokens: int = 50000,
) -> None:
    if summary_path.exists():
        return

    transcript = transcript_path.read_text()
    transcript = _truncate_transcript(transcript, max_tokens)

    raw_text = _call_claude(SYSTEM_PROMPT, f"Title: {video_title}\n\nTranscript:\n{transcript}")
    # Strip markdown code fences if present
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[-1]  # remove opening fence line
        raw_text = raw_text.rsplit("```", 1)[0]  # remove closing fence

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Claude returned invalid JSON for {video_id}: {e}\nRaw: {raw_text[:200]}") from e

    if "lessons" not in data:
        raise ValueError(f"Claude response missing 'lessons' key for {video_id}")

    date_str = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"

    lines = [
        f"# {video_title}",
        f"**Source:** [Watch on YouTube]({video_url})",
        f"**Date:** {date_str}",
        "",
        "## Lessons",
        "",
    ]
    for lesson in data["lessons"]:
        ts = lesson["timestamp_seconds"]
        lines += [
            f"### {lesson['title']}",
            f"> \"{lesson['quote']}\"",
            f"[Watch this moment →]({video_url}{'&' if '?' in video_url else '?'}t={ts}s)",
            "",
            lesson["summary"],
            "",
        ]

    summary_path.write_text("\n".join(lines))
