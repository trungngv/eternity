import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from eternity.build import build


@pytest.fixture
def knowledge_dir(tmp_path):
    ch_dir = tmp_path / "channels" / "test_ch"
    ep_dir = ch_dir / "episodes" / "episode-one-title"
    ep_dir.mkdir(parents=True)
    (ep_dir / "summary.md").write_text("## Lessons\n\n### Key insight\nThis is the lesson.")
    (ch_dir / "channel.json").write_text(json.dumps({
        "last_checked": "2026-06-10T00:00:00+00:00",
        "videos": [{
            "video_id": "abc123",
            "title": "Episode One Title",
            "url": "https://youtube.com/watch?v=abc123",
            "fetched_date": "2026-06-10T00:00:00+00:00",
            "summarized_date": "2026-06-10T00:00:00+00:00",
            "error": None,
        }],
    }))
    return tmp_path


def _mock_channels(channel_id="test_ch", channel_name="Test Channel"):
    ch = MagicMock()
    ch.id = channel_id
    ch.name = channel_name
    return [ch]


def test_build_creates_index(knowledge_dir, tmp_path):
    out_dir = tmp_path / "out"
    with patch("eternity.build.load_channels", return_value=_mock_channels()):
        build(knowledge_dir, out_dir, Path("config/channels.yaml"))
    index = (out_dir / "index.html").read_text()
    assert "2026-06-10" in index
    assert 'href="2026-06-10/"' in index
    assert "1 episode" in index


def test_build_creates_date_page(knowledge_dir, tmp_path):
    out_dir = tmp_path / "out"
    with patch("eternity.build.load_channels", return_value=_mock_channels()):
        build(knowledge_dir, out_dir, Path("config/channels.yaml"))
    date_page = (out_dir / "2026-06-10" / "index.html").read_text()
    assert "Test Channel" in date_page
    assert "Episode One Title" in date_page
    assert "Key insight" in date_page


def test_build_skips_unsummarized(knowledge_dir, tmp_path):
    ch_dir = knowledge_dir / "channels" / "test_ch"
    state = json.loads((ch_dir / "channel.json").read_text())
    state["videos"].append({
        "video_id": "xyz789",
        "title": "Unsummarized Episode",
        "url": "https://youtube.com/watch?v=xyz789",
        "fetched_date": "2026-06-10T00:00:00+00:00",
        "summarized_date": None,
        "error": None,
    })
    (ch_dir / "channel.json").write_text(json.dumps(state))
    out_dir = tmp_path / "out"
    with patch("eternity.build.load_channels", return_value=_mock_channels()):
        build(knowledge_dir, out_dir, Path("config/channels.yaml"))
    index = (out_dir / "index.html").read_text()
    assert "1 episode" in index
    assert "Unsummarized" not in index


def test_build_multiple_dates(tmp_path):
    ch_dir = tmp_path / "channels" / "test_ch"
    (ch_dir / "episodes" / "episode-day-one").mkdir(parents=True)
    (ch_dir / "episodes" / "episode-day-two").mkdir(parents=True)
    (ch_dir / "episodes" / "episode-day-one" / "summary.md").write_text("# Ep 1")
    (ch_dir / "episodes" / "episode-day-two" / "summary.md").write_text("# Ep 2")
    (ch_dir / "channel.json").write_text(json.dumps({
        "last_checked": "2026-06-10T00:00:00+00:00",
        "videos": [
            {
                "video_id": "a1",
                "title": "Episode Day One",
                "url": "https://youtube.com/watch?v=a1",
                "fetched_date": "2026-06-09T00:00:00+00:00",
                "summarized_date": "2026-06-09T00:00:00+00:00",
                "error": None,
            },
            {
                "video_id": "a2",
                "title": "Episode Day Two",
                "url": "https://youtube.com/watch?v=a2",
                "fetched_date": "2026-06-10T00:00:00+00:00",
                "summarized_date": "2026-06-10T00:00:00+00:00",
                "error": None,
            },
        ],
    }))
    out_dir = tmp_path / "out"
    with patch("eternity.build.load_channels", return_value=_mock_channels()):
        build(tmp_path, out_dir, Path("config/channels.yaml"))
    index = (out_dir / "index.html").read_text()
    assert "2026-06-10" in index
    assert "2026-06-09" in index
    assert index.index("2026-06-10") < index.index("2026-06-09")


def test_build_creates_nojekyll(knowledge_dir, tmp_path):
    out_dir = tmp_path / "out"
    with patch("eternity.build.load_channels", return_value=_mock_channels()):
        build(knowledge_dir, out_dir, Path("config/channels.yaml"))
    assert (out_dir / ".nojekyll").exists()
