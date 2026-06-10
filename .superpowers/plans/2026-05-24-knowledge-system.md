# Knowledge Discovery & Management System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local system that watches YouTube channels, generates structured lesson summaries from transcripts, synthesizes them into a living knowledge base weekly, and serves it as a browsable local web app.

**Architecture:** Python pipeline (`watcher → fetcher → summarizer → synthesizer`) orchestrated by a Click CLI, with Claude API handling all AI tasks. FastAPI serves the `knowledge/` markdown directory. Claude Code cron triggers daily processing and weekly synthesis.

**Tech Stack:** Python 3.12+, uv, pytest, yt-dlp, youtube-transcript-api, anthropic SDK, click, fastapi, uvicorn, mistune, jinja2, pyyaml

---

## File Map

| File | Responsibility |
|---|---|
| `pyproject.toml` | Project metadata, dependencies, entry point |
| `config/channels.yaml` | Channel configs (one entry per channel) |
| `src/eternity/__init__.py` | Package root |
| `src/eternity/config.py` | Load/parse channels.yaml into dataclasses |
| `src/eternity/watcher.py` | Detect new unprocessed episodes per channel |
| `src/eternity/fetcher.py` | Download transcript via yt-dlp + fallback |
| `src/eternity/summarizer.py` | Claude API: transcript → summary.md |
| `src/eternity/synthesizer.py` | Claude API: weekly KB consolidation |
| `src/eternity/cli.py` | Click CLI entry points |
| `src/eternity/web/app.py` | FastAPI server |
| `src/eternity/web/templates/` | Jinja2 HTML templates |
| `tests/test_config.py` | Config loading tests |
| `tests/test_watcher.py` | Filter + filesystem check tests |
| `tests/test_fetcher.py` | VTT parsing tests |
| `tests/test_summarizer.py` | Summarizer tests (Claude mocked) |
| `tests/test_synthesizer.py` | Synthesizer tests (Claude mocked) |
| `.claude/settings.json` | Cron job definitions |

---

## Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/eternity/__init__.py`
- Create: `config/channels.yaml`
- Create: `knowledge/.gitkeep`, `knowledge/channels/.gitkeep`, `knowledge/topics/.gitkeep`, `knowledge/synthesis/.gitkeep`
- Create: `.gitignore`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "eternity"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "anthropic>=0.40.0",
    "click>=8.1.0",
    "fastapi>=0.115.0",
    "jinja2>=3.1.0",
    "mistune>=3.0.0",
    "pyyaml>=6.0.0",
    "uvicorn[standard]>=0.32.0",
    "yt-dlp>=2024.1.0",
    "youtube-transcript-api>=0.6.0",
]

[project.scripts]
eternity = "eternity.cli:cli"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/eternity"]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Create package and directory structure**

```bash
mkdir -p src/eternity/web/templates
mkdir -p tests/fixtures
mkdir -p knowledge/channels
mkdir -p knowledge/topics
mkdir -p knowledge/synthesis
touch src/eternity/__init__.py
touch src/eternity/web/__init__.py
touch tests/__init__.py
touch knowledge/.gitkeep
touch knowledge/topics/.gitkeep
touch knowledge/synthesis/.gitkeep
```

- [ ] **Step 3: Create config/channels.yaml**

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

- [ ] **Step 4: Create .gitignore**

```
__pycache__/
*.py[cod]
.venv/
.env
knowledge/channels/*/episodes/*/transcript.txt
```

- [ ] **Step 5: Install dependencies**

```bash
uv sync --dev
```

Expected: uv creates `.venv/` and installs all dependencies.

- [ ] **Step 6: Verify pytest runs**

```bash
uv run pytest
```

Expected: `no tests ran` (exit 0, or exit 5 for "no tests collected" — both are fine).

- [ ] **Step 7: Commit**

```bash
git init
git add pyproject.toml src/ config/ knowledge/ tests/ .gitignore
git commit -m "feat: project scaffolding with uv and pytest"
```

---

## Task 2: Config Loading

**Files:**
- Create: `src/eternity/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_config.py
from pathlib import Path
from eternity.config import load_channels, Channel, ChannelFilters

FULL_YAML = """\
channels:
  - id: tkk_podcast
    name: The Knowledge Project Podcast
    url: https://www.youtube.com/@tkppodcast/videos
    check_frequency: daily
    filters:
      min_duration_minutes: 20
      max_duration_minutes: 180
      exclude_title_keywords: ["trailer", "clip"]
      backfill_days: 90
      max_episodes_per_run: 5
      max_transcript_tokens: 50000
"""

MINIMAL_YAML = """\
channels:
  - id: test
    name: Test Channel
    url: https://youtube.com/@test
    check_frequency: daily
"""


def test_load_full_config(tmp_path):
    f = tmp_path / "channels.yaml"
    f.write_text(FULL_YAML)
    channels = load_channels(f)
    assert len(channels) == 1
    ch = channels[0]
    assert ch.id == "tkk_podcast"
    assert ch.name == "The Knowledge Project Podcast"
    assert ch.filters.min_duration_minutes == 20
    assert ch.filters.max_duration_minutes == 180
    assert ch.filters.exclude_title_keywords == ["trailer", "clip"]
    assert ch.filters.backfill_days == 90
    assert ch.filters.max_episodes_per_run == 5
    assert ch.filters.max_transcript_tokens == 50000


def test_load_minimal_config_uses_defaults(tmp_path):
    f = tmp_path / "channels.yaml"
    f.write_text(MINIMAL_YAML)
    channels = load_channels(f)
    ch = channels[0]
    assert ch.filters.min_duration_minutes == 0
    assert ch.filters.max_duration_minutes == 300
    assert ch.filters.exclude_title_keywords == []
    assert ch.filters.backfill_days == 30
    assert ch.filters.max_episodes_per_run == 5
    assert ch.filters.max_transcript_tokens == 50000
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_config.py -v
```

Expected: `ImportError: cannot import name 'load_channels' from 'eternity.config'`

- [ ] **Step 3: Implement config.py**

```python
# src/eternity/config.py
from dataclasses import dataclass, field
from pathlib import Path
import yaml


@dataclass
class ChannelFilters:
    min_duration_minutes: int = 0
    max_duration_minutes: int = 300
    exclude_title_keywords: list[str] = field(default_factory=list)
    backfill_days: int = 30
    max_episodes_per_run: int = 5
    max_transcript_tokens: int = 50000


@dataclass
class Channel:
    id: str
    name: str
    url: str
    check_frequency: str
    filters: ChannelFilters


def load_channels(config_path: Path) -> list[Channel]:
    with open(config_path) as f:
        data = yaml.safe_load(f)
    channels = []
    for c in data["channels"]:
        filters = ChannelFilters(**c.get("filters", {}))
        channels.append(Channel(
            id=c["id"],
            name=c["name"],
            url=c["url"],
            check_frequency=c["check_frequency"],
            filters=filters,
        ))
    return channels
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_config.py -v
```

Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add src/eternity/config.py tests/test_config.py
git commit -m "feat: config loading with channel filters"
```

---

## Task 3: VTT Parsing

**Files:**
- Create: `src/eternity/fetcher.py` (parsing functions only — network calls added in Task 5)
- Create: `tests/test_fetcher.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_fetcher.py
from eternity.fetcher import parse_vtt, segments_to_text, _parse_timestamp, TranscriptSegment

SAMPLE_VTT = """\
WEBVTT
Kind: captions
Language: en

00:00:01.000 --> 00:00:05.000
Hello world

00:00:05.500 --> 00:00:10.000
<00:00:05.500><c>This</c><00:00:06.000><c> is</c> auto-generated

00:01:30.000 --> 00:01:35.000
New topic here
"""


def test_parse_vtt_segment_count():
    segments = parse_vtt(SAMPLE_VTT)
    assert len(segments) == 3


def test_parse_vtt_first_segment():
    segments = parse_vtt(SAMPLE_VTT)
    assert segments[0].text == "Hello world"
    assert segments[0].start_seconds == 1


def test_parse_vtt_strips_inline_tags():
    segments = parse_vtt(SAMPLE_VTT)
    assert "<c>" not in segments[1].text
    assert segments[1].text == "This is auto-generated"


def test_parse_vtt_timestamp_to_seconds():
    segments = parse_vtt(SAMPLE_VTT)
    assert segments[2].start_seconds == 90  # 1:30


def test_parse_timestamp_hours_minutes_seconds():
    assert _parse_timestamp("01:02:03.500") == 3723


def test_parse_timestamp_minutes_seconds():
    assert _parse_timestamp("02:30.000") == 150


def test_segments_to_text_groups_by_minute():
    segments = [
        TranscriptSegment(text="First.", start_seconds=5),
        TranscriptSegment(text="Second.", start_seconds=30),
        TranscriptSegment(text="New minute.", start_seconds=65),
    ]
    text = segments_to_text(segments)
    lines = text.splitlines()
    assert len(lines) == 2
    assert lines[0].startswith("[0:00]")
    assert "First." in lines[0]
    assert "Second." in lines[0]
    assert lines[1].startswith("[0:01]")
    assert "New minute." in lines[1]


def test_segments_to_text_empty():
    assert segments_to_text([]) == ""
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_fetcher.py -v
```

Expected: `ImportError: cannot import name 'parse_vtt' from 'eternity.fetcher'`

- [ ] **Step 3: Implement VTT parsing in fetcher.py**

```python
# src/eternity/fetcher.py
from dataclasses import dataclass
from pathlib import Path
import re


@dataclass
class TranscriptSegment:
    text: str
    start_seconds: int


class FetchError(Exception):
    pass


def _parse_timestamp(ts: str) -> int:
    parts = ts.strip().split(":")
    if len(parts) == 3:
        h, m, s = parts
    else:
        h, m, s = 0, parts[0], parts[1]
    return int(h) * 3600 + int(m) * 60 + int(float(s))


def _strip_vtt_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def parse_vtt(vtt_content: str) -> list[TranscriptSegment]:
    segments = []
    lines = vtt_content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if "-->" in line:
            start_ts = line.split("-->")[0].strip()
            start_seconds = _parse_timestamp(start_ts)
            text_lines = []
            i += 1
            while i < len(lines) and lines[i].strip():
                cleaned = _strip_vtt_tags(lines[i])
                if cleaned:
                    text_lines.append(cleaned)
                i += 1
            if text_lines:
                segments.append(TranscriptSegment(
                    text=" ".join(text_lines),
                    start_seconds=start_seconds,
                ))
        i += 1
    return segments


def segments_to_text(segments: list[TranscriptSegment]) -> str:
    if not segments:
        return ""
    lines = []
    current_minute = -1
    buffer: list[str] = []

    def flush(minute: int) -> None:
        h, m = divmod(minute, 60)
        ts = f"{h}:{m:02d}" if h else f"0:{m:02d}"
        lines.append(f"[{ts}] {' '.join(buffer)}")

    for seg in segments:
        minute = seg.start_seconds // 60
        if minute != current_minute:
            if buffer:
                flush(current_minute)
                buffer = []
            current_minute = minute
        buffer.append(seg.text)
    if buffer:
        flush(current_minute)
    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_fetcher.py -v
```

Expected: `8 passed`

- [ ] **Step 5: Commit**

```bash
git add src/eternity/fetcher.py tests/test_fetcher.py
git commit -m "feat: VTT transcript parsing"
```

---

## Task 4: Watcher — Filtering and Filesystem Check

**Files:**
- Create: `src/eternity/watcher.py`
- Create: `tests/test_watcher.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_watcher.py
from datetime import datetime, timedelta, timezone
from pathlib import Path
from eternity.watcher import (
    VideoEntry,
    _passes_filters,
    _is_processed,
    _episode_dir_name,
    _slugify,
)
from eternity.config import ChannelFilters


def _days_ago(n: int) -> str:
    return (datetime.now(tz=timezone.utc) - timedelta(days=n)).strftime("%Y%m%d")


def make_video(
    duration_seconds: int = 3600,
    title: str = "Great Episode",
    days_ago: int = 5,
    video_id: str = "abc123",
) -> VideoEntry:
    return VideoEntry(
        id=video_id,
        title=title,
        upload_date=_days_ago(days_ago),
        duration=duration_seconds,
        webpage_url=f"https://youtube.com/watch?v={video_id}",
    )


def default_filters(**overrides) -> ChannelFilters:
    return ChannelFilters(
        min_duration_minutes=20,
        max_duration_minutes=180,
        exclude_title_keywords=["trailer", "clip"],
        backfill_days=90,
        max_episodes_per_run=5,
        max_transcript_tokens=50000,
        **overrides,
    )


def test_rejects_too_short():
    assert not _passes_filters(make_video(duration_seconds=600), default_filters())


def test_rejects_too_long():
    assert not _passes_filters(make_video(duration_seconds=12000), default_filters())


def test_rejects_keyword_in_title():
    assert not _passes_filters(make_video(title="Season 2 Trailer"), default_filters())


def test_rejects_keyword_case_insensitive():
    assert not _passes_filters(make_video(title="Best CLIPS of 2025"), default_filters())


def test_rejects_outside_backfill_window():
    assert not _passes_filters(make_video(days_ago=100), default_filters())


def test_accepts_valid_video():
    assert _passes_filters(make_video(), default_filters())


def test_is_processed_true(tmp_path):
    video = make_video()
    dir_name = _episode_dir_name(video)
    (tmp_path / dir_name).mkdir()
    assert _is_processed(video, tmp_path)


def test_is_processed_false(tmp_path):
    assert not _is_processed(make_video(), tmp_path)


def test_slugify_basic():
    assert _slugify("Hello World") == "hello-world"


def test_slugify_special_chars():
    assert _slugify("Shane Parrish: Mental Models & More!") == "shane-parrish-mental-models-more"


def test_slugify_truncates_at_60():
    long_title = "a" * 100
    assert len(_slugify(long_title)) <= 60


def test_episode_dir_name_format():
    video = make_video(title="Great Episode", days_ago=0)
    name = _episode_dir_name(video)
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    assert name.startswith(today)
    assert "great-episode" in name
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_watcher.py -v
```

Expected: `ImportError: cannot import name 'VideoEntry' from 'eternity.watcher'`

- [ ] **Step 3: Implement watcher.py (pure logic — no network calls)**

```python
# src/eternity/watcher.py
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re


@dataclass
class VideoEntry:
    id: str
    title: str
    upload_date: str  # YYYYMMDD
    duration: int     # seconds
    webpage_url: str


def _slugify(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug[:60].strip("-")


def _episode_dir_name(entry: VideoEntry) -> str:
    y, m, d = entry.upload_date[:4], entry.upload_date[4:6], entry.upload_date[6:8]
    return f"{y}-{m}-{d}_{_slugify(entry.title)}"


def _is_processed(entry: VideoEntry, episodes_dir: Path) -> bool:
    return (episodes_dir / _episode_dir_name(entry)).exists()


def _passes_filters(entry: VideoEntry, filters) -> bool:
    from .config import ChannelFilters
    duration_minutes = entry.duration / 60
    if duration_minutes < filters.min_duration_minutes:
        return False
    if duration_minutes > filters.max_duration_minutes:
        return False
    title_lower = entry.title.lower()
    for keyword in filters.exclude_title_keywords:
        if keyword.lower() in title_lower:
            return False
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=filters.backfill_days)
    upload_dt = datetime(
        int(entry.upload_date[:4]),
        int(entry.upload_date[4:6]),
        int(entry.upload_date[6:8]),
        tzinfo=timezone.utc,
    )
    if upload_dt < cutoff:
        return False
    return True


def list_channel_videos(channel_url: str) -> list[VideoEntry]:
    import yt_dlp
    ydl_opts = {"extract_flat": True, "quiet": True, "no_warnings": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(channel_url, download=False)
    entries = []
    for item in info.get("entries", []):
        if not item:
            continue
        entries.append(VideoEntry(
            id=item["id"],
            title=item.get("title", ""),
            upload_date=item.get("upload_date", "19700101"),
            duration=item.get("duration", 0) or 0,
            webpage_url=item.get("webpage_url", f"https://youtube.com/watch?v={item['id']}"),
        ))
    return entries


def find_new_episodes(channel, channel_dir: Path) -> list[VideoEntry]:
    episodes_dir = channel_dir / "episodes"
    episodes_dir.mkdir(parents=True, exist_ok=True)
    all_videos = list_channel_videos(channel.url)
    filtered = [v for v in all_videos if _passes_filters(v, channel.filters)]
    unprocessed = [v for v in filtered if not _is_processed(v, episodes_dir)]
    return unprocessed[: channel.filters.max_episodes_per_run]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_watcher.py -v
```

Expected: `12 passed`

- [ ] **Step 5: Commit**

```bash
git add src/eternity/watcher.py tests/test_watcher.py
git commit -m "feat: episode watcher with filtering and filesystem check"
```

---

## Task 5: Transcript Fetching (Network Layer)

**Files:**
- Modify: `src/eternity/fetcher.py` (add `fetch_transcript` and `_fetch_via_api`)
- Modify: `tests/test_fetcher.py` (add network-layer tests with mocks)

- [ ] **Step 1: Write failing tests for fetch_transcript**

Add to `tests/test_fetcher.py`:

```python
from unittest.mock import patch
from eternity.fetcher import fetch_transcript, FetchError


def test_fetch_uses_yt_dlp_when_vtt_available(tmp_path):
    output_path = tmp_path / "transcript.txt"
    vtt_file = tmp_path / "abc123.en.vtt"
    vtt_file.write_text("WEBVTT\n\n00:00:01.000 --> 00:00:05.000\nHello world\n")

    with patch("eternity.fetcher._download_subtitles", return_value=vtt_file):
        fetch_transcript("abc123", output_path)

    assert output_path.exists()
    assert "Hello world" in output_path.read_text()


def test_fetch_falls_back_to_api_when_no_vtt(tmp_path):
    output_path = tmp_path / "transcript.txt"
    mock_entries = [
        {"start": 0.0, "duration": 5.0, "text": "Hello world"},
        {"start": 65.0, "duration": 5.0, "text": "New minute content"},
    ]

    with patch("eternity.fetcher._download_subtitles", return_value=None), \
         patch("eternity.fetcher.YouTubeTranscriptApi") as MockAPI:
        MockAPI.get_transcript.return_value = mock_entries
        fetch_transcript("abc123", output_path)

    content = output_path.read_text()
    assert "Hello world" in content
    assert "New minute content" in content


def test_fetch_raises_when_both_fail(tmp_path):
    import pytest
    from youtube_transcript_api import NoTranscriptFound
    output_path = tmp_path / "transcript.txt"

    with patch("eternity.fetcher._download_subtitles", return_value=None), \
         patch("eternity.fetcher.YouTubeTranscriptApi") as MockAPI:
        MockAPI.get_transcript.side_effect = NoTranscriptFound("abc123", ["en"], None)

        with pytest.raises(FetchError):
            fetch_transcript("abc123", output_path)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_fetcher.py::test_fetch_uses_yt_dlp_when_vtt_available tests/test_fetcher.py::test_fetch_falls_back_to_api_when_no_vtt tests/test_fetcher.py::test_fetch_raises_when_both_fail -v
```

Expected: `ImportError` — `fetch_transcript` not defined.

- [ ] **Step 3: Add fetch_transcript to fetcher.py**

Add to `src/eternity/fetcher.py`:

```python
import shutil
import tempfile
from youtube_transcript_api import YouTubeTranscriptApi


def _download_subtitles(video_id: str, output_dir: Path) -> Path | None:
    import yt_dlp
    ydl_opts = {
        "writeautomaticsub": True,
        "writesubtitles": True,
        "subtitlesformat": "vtt",
        "subtitleslangs": ["en", "en-US", "en-GB"],
        "skip_download": True,
        "outtmpl": str(output_dir / "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([f"https://youtube.com/watch?v={video_id}"])
    vtt_files = list(output_dir.glob("*.vtt"))
    return vtt_files[0] if vtt_files else None


def fetch_transcript(video_id: str, output_path: Path) -> None:
    tmp = Path(tempfile.mkdtemp())
    try:
        vtt_path = _download_subtitles(video_id, tmp)
        if vtt_path:
            segments = parse_vtt(vtt_path.read_text(encoding="utf-8", errors="replace"))
            if segments:
                output_path.write_text(segments_to_text(segments))
                return
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    _fetch_via_api(video_id, output_path)


def _fetch_via_api(video_id: str, output_path: Path) -> None:
    from youtube_transcript_api import NoTranscriptFound, TranscriptsDisabled

    try:
        entries = YouTubeTranscriptApi.get_transcript(
            video_id, languages=["en", "en-US", "en-GB"]
        )
        lines = []
        for entry in entries:
            start = int(entry["start"])
            m, s = divmod(start, 60)
            h, m = divmod(m, 60)
            ts = f"{h}:{m:02d}" if h else f"0:{m:02d}"
            lines.append(f"[{ts}] {entry['text']}")
        output_path.write_text("\n".join(lines))
    except (NoTranscriptFound, TranscriptsDisabled) as e:
        raise FetchError(f"No transcript available for {video_id}: {e}") from e
```

- [ ] **Step 4: Run all fetcher tests**

```bash
uv run pytest tests/test_fetcher.py -v
```

Expected: `11 passed`

- [ ] **Step 5: Commit**

```bash
git add src/eternity/fetcher.py tests/test_fetcher.py
git commit -m "feat: transcript fetching via yt-dlp with youtube_transcript_api fallback"
```

---

## Task 6: Episode Summarizer

**Files:**
- Create: `src/eternity/summarizer.py`
- Create: `tests/test_summarizer.py`
- Create: `tests/fixtures/sample_transcript.txt`

- [ ] **Step 1: Create transcript fixture**

```
# tests/fixtures/sample_transcript.txt
[0:00] Welcome to the show today we have a very special guest.
[0:01] We're going to talk about decision making and mental models.
[1:00] The key insight is that when you have a framework you stop relitigating the same decisions.
[1:01] This saves enormous cognitive energy over time.
[2:00] Another important point is that most decisions are reversible.
[2:01] We treat them as if they're permanent but they're not.
[3:00] The guest shares a story about how he uses a simple checklist.
[3:01] The checklist prevents him from making the same mistake twice.
[4:00] Thank you so much for being on the show today.
```

- [ ] **Step 2: Write failing tests**

```python
# tests/test_summarizer.py
from pathlib import Path
from unittest.mock import patch, MagicMock
from eternity.summarizer import summarize_episode, _truncate_transcript

FIXTURE_TRANSCRIPT = Path("tests/fixtures/sample_transcript.txt")

MOCK_CLAUDE_RESPONSE = """{
  "lessons": [
    {
      "title": "Frameworks eliminate repeated decisions",
      "summary": "Having a clear framework prevents relitigating the same choices. This conserves cognitive energy.",
      "quote": "when you have a framework you stop relitigating the same decisions",
      "timestamp_seconds": 60
    },
    {
      "title": "Most decisions are reversible",
      "summary": "We treat decisions as permanent when they usually are not. Recognizing this reduces anxiety.",
      "quote": "most decisions are reversible",
      "timestamp_seconds": 120
    }
  ]
}"""


def _make_mock_client(response_text: str):
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=response_text)]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response
    return mock_client


def test_truncate_no_op_when_short():
    short = "word " * 100
    assert _truncate_transcript(short, max_tokens=10000) == short.strip()


def test_truncate_keeps_start_and_end():
    words = [f"word{i}" for i in range(10000)]
    transcript = " ".join(words)
    result = _truncate_transcript(transcript, max_tokens=500)
    assert "word0" in result
    assert "word9999" in result
    assert "[...transcript truncated...]" in result


def test_summarize_skips_if_summary_exists(tmp_path):
    summary_path = tmp_path / "summary.md"
    summary_path.write_text("# existing")
    transcript_path = tmp_path / "transcript.txt"
    transcript_path.write_text("text")

    with patch("eternity.summarizer.anthropic.Anthropic") as MockClient:
        summarize_episode(
            video_id="abc",
            video_title="Test",
            video_url="https://youtube.com/watch?v=abc",
            upload_date="20260524",
            transcript_path=transcript_path,
            summary_path=summary_path,
        )
        MockClient.assert_not_called()


def test_summarize_writes_summary_md(tmp_path):
    summary_path = tmp_path / "summary.md"
    transcript_path = FIXTURE_TRANSCRIPT

    with patch("eternity.summarizer.anthropic.Anthropic") as MockClient:
        MockClient.return_value = _make_mock_client(MOCK_CLAUDE_RESPONSE)
        summarize_episode(
            video_id="abc123",
            video_title="Mental Models with Shane Parrish",
            video_url="https://youtube.com/watch?v=abc123",
            upload_date="20260524",
            transcript_path=transcript_path,
            summary_path=summary_path,
        )

    content = summary_path.read_text()
    assert "# Mental Models with Shane Parrish" in content
    assert "**Date:** 2026-05-24" in content
    assert "Frameworks eliminate repeated decisions" in content
    assert "when you have a framework you stop relitigating" in content
    assert "watch?v=abc123&t=60s" in content


def test_summarize_uses_prompt_caching(tmp_path):
    summary_path = tmp_path / "summary.md"
    transcript_path = FIXTURE_TRANSCRIPT

    with patch("eternity.summarizer.anthropic.Anthropic") as MockClient:
        MockClient.return_value = _make_mock_client(MOCK_CLAUDE_RESPONSE)
        summarize_episode(
            video_id="abc123",
            video_title="Test",
            video_url="https://youtube.com/watch?v=abc123",
            upload_date="20260524",
            transcript_path=transcript_path,
            summary_path=summary_path,
        )
        call_kwargs = MockClient.return_value.messages.create.call_args
        system = call_kwargs.kwargs["system"]
        assert isinstance(system, list)
        assert system[0].get("cache_control") == {"type": "ephemeral"}
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
uv run pytest tests/test_summarizer.py -v
```

Expected: `ImportError: cannot import name 'summarize_episode'`

- [ ] **Step 4: Implement summarizer.py**

```python
# src/eternity/summarizer.py
import json
from pathlib import Path
import anthropic


SYSTEM_PROMPT = """You are a knowledge curator. Given a podcast transcript, extract 3-5 key lessons.

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

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": f"Title: {video_title}\n\nTranscript:\n{transcript}"}],
    )

    data = json.loads(response.content[0].text)
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
            f"[Watch this moment →]({video_url}&t={ts}s)",
            "",
            lesson["summary"],
            "",
        ]

    summary_path.write_text("\n".join(lines))
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/test_summarizer.py -v
```

Expected: `5 passed`

- [ ] **Step 6: Commit**

```bash
git add src/eternity/summarizer.py tests/test_summarizer.py tests/fixtures/sample_transcript.txt
git commit -m "feat: episode summarizer with Claude API and prompt caching"
```

---

## Task 7: Weekly Synthesizer

**Files:**
- Create: `src/eternity/synthesizer.py`
- Create: `tests/test_synthesizer.py`
- Create: `tests/fixtures/sample_summary.md`

- [ ] **Step 1: Create summary fixture**

```markdown
# Mental Models with Shane Parrish
**Source:** [Watch on YouTube](https://youtube.com/watch?v=abc123)
**Date:** 2026-05-17

## Lessons

### Frameworks eliminate repeated decisions
> "when you have a framework you stop relitigating the same decisions"
[Watch this moment →](https://youtube.com/watch?v=abc123&t=60s)

Having a clear framework prevents relitigating the same choices. This conserves cognitive energy.

### Most decisions are reversible
> "most decisions are reversible"
[Watch this moment →](https://youtube.com/watch?v=abc123&t=120s)

We treat decisions as permanent when they usually are not.
```

Save to `tests/fixtures/sample_summary.md`.

- [ ] **Step 2: Write failing tests**

```python
# tests/test_synthesizer.py
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock
from eternity.synthesizer import run_synthesis, _get_last_synthesis_date, _collect_new_summaries

FIXTURE_SUMMARY = Path("tests/fixtures/sample_summary.md")

MOCK_SYNTHESIS_RESPONSE = """{
  "master_lessons_md": "# Master Lessons\\n\\n_Last updated: 2026-W21_\\n\\n## Decision Making\\n- **Frameworks eliminate repeated decisions** — having a clear framework prevents relitigating the same choices. ([TKP](channels/tkk_podcast/episodes/2026-05-17_mental-models/summary.md))\\n",
  "topic_updates": {
    "decision-making": "# Decision Making\\n\\n- **Frameworks eliminate repeated decisions** — see master_lessons.md\\n"
  },
  "synthesis_summary": {
    "episodes_reviewed": 1,
    "lessons_added": 1,
    "lessons_updated": 0,
    "changes": ["Added lesson: Frameworks eliminate repeated decisions"]
  }
}"""


def _make_mock_client(response_text: str):
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=response_text)]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response
    return mock_client


def test_get_last_synthesis_date_none_when_empty(tmp_path):
    synthesis_dir = tmp_path / "synthesis"
    synthesis_dir.mkdir()
    assert _get_last_synthesis_date(synthesis_dir) is None


def test_get_last_synthesis_date_returns_mtime(tmp_path):
    synthesis_dir = tmp_path / "synthesis"
    synthesis_dir.mkdir()
    f = synthesis_dir / "2026-W20.md"
    f.write_text("content")
    result = _get_last_synthesis_date(synthesis_dir)
    assert result is not None
    assert isinstance(result, datetime)


def test_collect_new_summaries_finds_recent(tmp_path):
    ep_dir = tmp_path / "channels" / "tkk" / "episodes" / "2026-05-17_test"
    ep_dir.mkdir(parents=True)
    summary = ep_dir / "summary.md"
    summary.write_text("# Test")
    results = _collect_new_summaries(tmp_path, since=None)
    assert summary in results


def test_collect_new_summaries_skips_old(tmp_path):
    ep_dir = tmp_path / "channels" / "tkk" / "episodes" / "2026-05-17_test"
    ep_dir.mkdir(parents=True)
    summary = ep_dir / "summary.md"
    summary.write_text("# Test")
    future = datetime(2030, 1, 1, tzinfo=timezone.utc)
    results = _collect_new_summaries(tmp_path, since=future)
    assert summary not in results


def test_run_synthesis_skips_when_no_new(tmp_path):
    (tmp_path / "channels").mkdir()
    (tmp_path / "synthesis").mkdir()

    with patch("eternity.synthesizer.anthropic.Anthropic") as MockClient:
        run_synthesis(tmp_path)
        MockClient.assert_not_called()


def test_run_synthesis_writes_output(tmp_path):
    ep_dir = tmp_path / "channels" / "tkk" / "episodes" / "2026-05-17_test"
    ep_dir.mkdir(parents=True)
    import shutil
    shutil.copy(FIXTURE_SUMMARY, ep_dir / "summary.md")
    (tmp_path / "synthesis").mkdir()
    (tmp_path / "topics").mkdir()
    master = tmp_path / "master_lessons.md"
    master.write_text("# Master Lessons\n")

    with patch("eternity.synthesizer.anthropic.Anthropic") as MockClient:
        MockClient.return_value = _make_mock_client(MOCK_SYNTHESIS_RESPONSE)
        run_synthesis(tmp_path)

    assert master.read_text().startswith("# Master Lessons")
    topic_file = tmp_path / "topics" / "decision-making.md"
    assert topic_file.exists()
    synthesis_files = list((tmp_path / "synthesis").glob("*.md"))
    assert len(synthesis_files) == 1
    assert "episodes_reviewed: 1" in synthesis_files[0].read_text()
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
uv run pytest tests/test_synthesizer.py -v
```

Expected: `ImportError: cannot import name 'run_synthesis'`

- [ ] **Step 4: Implement synthesizer.py**

```python
# src/eternity/synthesizer.py
import json
from datetime import datetime, timezone
from pathlib import Path
import anthropic


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

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_content}],
    )

    data = json.loads(response.content[0].text)
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
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/test_synthesizer.py -v
```

Expected: `7 passed`

- [ ] **Step 6: Commit**

```bash
git add src/eternity/synthesizer.py tests/test_synthesizer.py tests/fixtures/sample_summary.md
git commit -m "feat: weekly knowledge synthesizer"
```

---

## Task 8: CLI

**Files:**
- Create: `src/eternity/cli.py`

No unit tests — verify manually after Task 9 (needs the web app to be useful). The CLI wires together already-tested components.

- [ ] **Step 1: Implement cli.py**

```python
# src/eternity/cli.py
import json
from datetime import datetime, timezone
from pathlib import Path

import click

CONFIG_PATH = Path("config/channels.yaml")
KNOWLEDGE_PATH = Path("knowledge")


@click.group()
def cli():
    pass


@cli.command()
@click.option("--channel", default=None, help="Process a specific channel ID only")
def process(channel):
    """Fetch and summarize new episodes from all channels (or one)."""
    from .config import load_channels
    from .watcher import find_new_episodes, _episode_dir_name
    from .fetcher import fetch_transcript, FetchError
    from .summarizer import summarize_episode

    channels = load_channels(CONFIG_PATH)
    if channel:
        channels = [c for c in channels if c.id == channel]
        if not channels:
            raise click.ClickException(f"Channel '{channel}' not found in config")

    for ch in channels:
        channel_dir = KNOWLEDGE_PATH / "channels" / ch.id
        channel_dir.mkdir(parents=True, exist_ok=True)

        channel_json = channel_dir / "channel.json"
        state: dict = {"last_checked": "", "errors": []}
        if channel_json.exists():
            state = json.loads(channel_json.read_text())
        if "errors" not in state:
            state["errors"] = []

        click.echo(f"Checking {ch.name}...")
        new_episodes = find_new_episodes(ch, channel_dir)
        click.echo(f"  {len(new_episodes)} new episode(s) to process")

        for video in new_episodes:
            slug = _episode_dir_name(video)
            episode_dir = channel_dir / "episodes" / slug
            episode_dir.mkdir(parents=True, exist_ok=True)

            transcript_path = episode_dir / "transcript.txt"
            summary_path = episode_dir / "summary.md"

            click.echo(f"  → {video.title}")
            try:
                if not transcript_path.exists():
                    fetch_transcript(video.id, transcript_path)
                summarize_episode(
                    video_id=video.id,
                    video_title=video.title,
                    video_url=video.webpage_url,
                    upload_date=video.upload_date,
                    transcript_path=transcript_path,
                    summary_path=summary_path,
                    max_tokens=ch.filters.max_transcript_tokens,
                )
                click.echo("    ✓ Done")
            except Exception as e:
                click.echo(f"    ✗ Error: {e}", err=True)
                state["errors"].append({
                    "video_id": video.id,
                    "reason": str(e),
                    "attempted_at": datetime.now(tz=timezone.utc).isoformat(),
                })

        state["last_checked"] = datetime.now(tz=timezone.utc).isoformat()
        channel_json.write_text(json.dumps(state, indent=2))


@cli.command()
def synthesize():
    """Run weekly knowledge synthesis across all channels."""
    from .synthesizer import run_synthesis
    click.echo("Running synthesis...")
    run_synthesis(KNOWLEDGE_PATH)
    click.echo("Done.")


@cli.command()
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=8000, show_default=True)
def serve(host, port):
    """Start the local web app."""
    import uvicorn
    uvicorn.run("eternity.web.app:app", host=host, port=port, reload=True)
```

- [ ] **Step 2: Verify CLI help works**

```bash
uv run eternity --help
```

Expected:
```
Usage: eternity [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  process    Fetch and summarize new episodes from all channels (or one).
  serve      Start the local web app.
  synthesize Run weekly knowledge synthesis across all channels.
```

- [ ] **Step 3: Commit**

```bash
git add src/eternity/cli.py
git commit -m "feat: CLI with process, synthesize, and serve commands"
```

---

## Task 9: Web App

**Files:**
- Create: `src/eternity/web/app.py`
- Create: `src/eternity/web/templates/base.html`
- Create: `src/eternity/web/templates/index.html`
- Create: `src/eternity/web/templates/channel.html`
- Create: `src/eternity/web/templates/episode.html`
- Create: `src/eternity/web/templates/lessons.html`
- Create: `src/eternity/web/templates/topic.html`
- Create: `src/eternity/web/templates/synthesis.html`
- Create: `src/eternity/web/templates/search.html`

- [ ] **Step 1: Implement app.py**

```python
# src/eternity/web/app.py
import subprocess
from pathlib import Path

import mistune
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

KNOWLEDGE_DIR = Path("knowledge")
TEMPLATES_DIR = Path(__file__).parent / "templates"

app = FastAPI(title="Eternity")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
md = mistune.create_markdown()


def render_md(path: Path) -> str:
    return md(path.read_text()) if path.exists() else "<p><em>Not found.</em></p>"


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    channels = []
    channels_dir = KNOWLEDGE_DIR / "channels"
    if channels_dir.exists():
        for ch_dir in sorted(channels_dir.iterdir()):
            if ch_dir.is_dir():
                ep_summaries = sorted(
                    (ch_dir / "episodes").glob("*/summary.md"), reverse=True
                )[:5]
                channels.append({
                    "id": ch_dir.name,
                    "episodes": [e.parent.name for e in ep_summaries],
                })
    synthesis_dir = KNOWLEDGE_DIR / "synthesis"
    recent_synthesis = []
    if synthesis_dir.exists():
        recent_synthesis = [f.stem for f in sorted(synthesis_dir.glob("*.md"), reverse=True)[:3]]
    return templates.TemplateResponse("index.html", {
        "request": request,
        "channels": channels,
        "recent_synthesis": recent_synthesis,
    })


@app.get("/channels/{channel_id}", response_class=HTMLResponse)
async def channel(request: Request, channel_id: str):
    episodes_dir = KNOWLEDGE_DIR / "channels" / channel_id / "episodes"
    episodes = []
    if episodes_dir.exists():
        episodes = [d.name for d in sorted(episodes_dir.iterdir(), reverse=True) if d.is_dir()]
    return templates.TemplateResponse("channel.html", {
        "request": request,
        "channel_id": channel_id,
        "episodes": episodes,
    })


@app.get("/channels/{channel_id}/episodes/{slug}", response_class=HTMLResponse)
async def episode(request: Request, channel_id: str, slug: str):
    path = KNOWLEDGE_DIR / "channels" / channel_id / "episodes" / slug / "summary.md"
    return templates.TemplateResponse("episode.html", {
        "request": request,
        "channel_id": channel_id,
        "slug": slug,
        "content": render_md(path),
    })


@app.get("/lessons", response_class=HTMLResponse)
async def lessons(request: Request):
    return templates.TemplateResponse("lessons.html", {
        "request": request,
        "content": render_md(KNOWLEDGE_DIR / "master_lessons.md"),
    })


@app.get("/topics/{topic}", response_class=HTMLResponse)
async def topic(request: Request, topic: str):
    path = KNOWLEDGE_DIR / "topics" / f"{topic}.md"
    return templates.TemplateResponse("topic.html", {
        "request": request,
        "topic": topic,
        "content": render_md(path),
    })


@app.get("/synthesis", response_class=HTMLResponse)
async def synthesis_list(request: Request):
    synthesis_dir = KNOWLEDGE_DIR / "synthesis"
    files = sorted(synthesis_dir.glob("*.md"), reverse=True) if synthesis_dir.exists() else []
    return templates.TemplateResponse("synthesis.html", {
        "request": request,
        "weeks": [f.stem for f in files],
    })


@app.get("/synthesis/{week}", response_class=HTMLResponse)
async def synthesis_week(request: Request, week: str):
    path = KNOWLEDGE_DIR / "synthesis" / f"{week}.md"
    return templates.TemplateResponse("synthesis.html", {
        "request": request,
        "weeks": [],
        "week": week,
        "content": render_md(path),
    })


@app.get("/search", response_class=HTMLResponse)
async def search(request: Request, q: str = ""):
    results = []
    if q and KNOWLEDGE_DIR.exists():
        proc = subprocess.run(
            ["grep", "-ril", q, str(KNOWLEDGE_DIR)],
            capture_output=True, text=True, timeout=10,
        )
        for line in proc.stdout.strip().splitlines():
            try:
                results.append(Path(line).relative_to(KNOWLEDGE_DIR))
            except ValueError:
                pass
    return templates.TemplateResponse("search.html", {
        "request": request,
        "query": q,
        "results": results,
    })
```

- [ ] **Step 2: Create base.html**

```html
<!-- src/eternity/web/templates/base.html -->
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}Eternity{% endblock %}</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 860px; margin: 2rem auto; padding: 0 1rem; color: #222; }
    nav { margin-bottom: 2rem; padding-bottom: 0.5rem; border-bottom: 1px solid #ddd; }
    nav a { margin-right: 1.5rem; text-decoration: none; color: #555; }
    nav a:hover { color: #000; }
    h1 { margin-top: 0; }
    blockquote { border-left: 3px solid #aaa; margin: 1rem 0; padding: 0.25rem 1rem; color: #555; font-style: italic; }
    ul.episodes { list-style: none; padding: 0; }
    ul.episodes li { padding: 0.4rem 0; border-bottom: 1px solid #eee; }
    ul.episodes li a { text-decoration: none; color: #1a6bb5; }
    .meta { color: #777; font-size: 0.9rem; margin-bottom: 1.5rem; }
  </style>
</head>
<body>
  <nav>
    <a href="/">Home</a>
    <a href="/lessons">Master Lessons</a>
    <a href="/synthesis">Synthesis</a>
    <a href="/search">Search</a>
  </nav>
  {% block content %}{% endblock %}
</body>
</html>
```

- [ ] **Step 3: Create index.html**

```html
<!-- src/eternity/web/templates/index.html -->
{% extends "base.html" %}
{% block title %}Eternity — Knowledge Base{% endblock %}
{% block content %}
<h1>Knowledge Base</h1>

{% for channel in channels %}
<h2><a href="/channels/{{ channel.id }}">{{ channel.id | replace("_", " ") | title }}</a></h2>
<ul class="episodes">
  {% for ep in channel.episodes %}
  <li><a href="/channels/{{ channel.id }}/episodes/{{ ep }}">{{ ep }}</a></li>
  {% endfor %}
</ul>
{% else %}
<p>No episodes yet. Run <code>eternity process</code> to get started.</p>
{% endfor %}

{% if recent_synthesis %}
<h2>Recent Synthesis</h2>
<ul>
  {% for week in recent_synthesis %}
  <li><a href="/synthesis/{{ week }}">{{ week }}</a></li>
  {% endfor %}
</ul>
{% endif %}
{% endblock %}
```

- [ ] **Step 4: Create channel.html**

```html
<!-- src/eternity/web/templates/channel.html -->
{% extends "base.html" %}
{% block title %}{{ channel_id }} — Eternity{% endblock %}
{% block content %}
<h1>{{ channel_id | replace("_", " ") | title }}</h1>
<p class="meta"><a href="/">← Home</a></p>
{% if episodes %}
<ul class="episodes">
  {% for ep in episodes %}
  <li><a href="/channels/{{ channel_id }}/episodes/{{ ep }}">{{ ep }}</a></li>
  {% endfor %}
</ul>
{% else %}
<p>No episodes processed yet.</p>
{% endif %}
{% endblock %}
```

- [ ] **Step 5: Create episode.html**

```html
<!-- src/eternity/web/templates/episode.html -->
{% extends "base.html" %}
{% block title %}{{ slug }} — Eternity{% endblock %}
{% block content %}
<p class="meta"><a href="/channels/{{ channel_id }}">← {{ channel_id | replace("_", " ") | title }}</a></p>
{{ content | safe }}
{% endblock %}
```

- [ ] **Step 6: Create lessons.html**

```html
<!-- src/eternity/web/templates/lessons.html -->
{% extends "base.html" %}
{% block title %}Master Lessons — Eternity{% endblock %}
{% block content %}
{{ content | safe }}
{% endblock %}
```

- [ ] **Step 7: Create topic.html**

```html
<!-- src/eternity/web/templates/topic.html -->
{% extends "base.html" %}
{% block title %}{{ topic | title }} — Eternity{% endblock %}
{% block content %}
<p class="meta"><a href="/lessons">← Master Lessons</a></p>
{{ content | safe }}
{% endblock %}
```

- [ ] **Step 8: Create synthesis.html**

```html
<!-- src/eternity/web/templates/synthesis.html -->
{% extends "base.html" %}
{% block title %}Synthesis — Eternity{% endblock %}
{% block content %}
{% if weeks %}
<h1>Weekly Synthesis</h1>
<ul>
  {% for week in weeks %}
  <li><a href="/synthesis/{{ week }}">{{ week }}</a></li>
  {% endfor %}
</ul>
{% else %}
<p class="meta"><a href="/synthesis">← All weeks</a></p>
{{ content | safe }}
{% endif %}
{% endblock %}
```

- [ ] **Step 9: Create search.html**

```html
<!-- src/eternity/web/templates/search.html -->
{% extends "base.html" %}
{% block title %}Search — Eternity{% endblock %}
{% block content %}
<h1>Search</h1>
<form method="get" action="/search">
  <input type="text" name="q" value="{{ query }}" placeholder="Search lessons..." style="width:60%;padding:0.4rem;">
  <button type="submit">Search</button>
</form>
{% if query %}
<p class="meta">Results for "{{ query }}":</p>
{% if results %}
<ul>
  {% for path in results %}
  <li>{{ path }}</li>
  {% endfor %}
</ul>
{% else %}
<p>No results found.</p>
{% endif %}
{% endif %}
{% endblock %}
```

- [ ] **Step 10: Run all tests to make sure nothing broke**

```bash
uv run pytest -v
```

Expected: all tests passing.

- [ ] **Step 11: Start the server and verify it loads**

```bash
uv run eternity serve
```

Open `http://localhost:8000` — should show the home page with "No episodes yet" message.

- [ ] **Step 12: Commit**

```bash
git add src/eternity/web/ 
git commit -m "feat: FastAPI web app for browsing the knowledge base"
```

---

## Task 10: Claude Code Cron Scheduling

**Files:**
- Create: `.claude/settings.json`

- [ ] **Step 1: Create .claude/settings.json with cron jobs**

```json
{
  "crons": [
    {
      "name": "daily-episode-processing",
      "schedule": "0 7 * * *",
      "command": "uv run eternity process",
      "description": "Fetch and summarize new episodes from all channels daily at 7am"
    },
    {
      "name": "weekly-synthesis",
      "schedule": "0 8 * * 1",
      "command": "uv run eternity synthesize",
      "description": "Run weekly knowledge synthesis every Monday at 8am"
    }
  ]
}
```

- [ ] **Step 2: Verify cron config is valid JSON**

```bash
python3 -c "import json; json.load(open('.claude/settings.json')); print('valid')"
```

Expected: `valid`

- [ ] **Step 3: Run a full test suite one final time**

```bash
uv run pytest -v
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add .claude/settings.json
git commit -m "feat: Claude Code cron for daily processing and weekly synthesis"
```

---

## End-to-End Verification

After all tasks are complete, do a quick manual smoke test:

```bash
# 1. Process a single episode manually (requires ANTHROPIC_API_KEY)
uv run eternity process --channel tkk_podcast

# 2. Run synthesis
uv run eternity synthesize

# 3. Start the web app and browse
uv run eternity serve
# Open http://localhost:8000
```

Check:
- Episode appears under the channel in the web UI
- `summary.md` has lessons with YouTube timestamp links
- `knowledge/master_lessons.md` was updated
- `knowledge/synthesis/` has a new weekly file
