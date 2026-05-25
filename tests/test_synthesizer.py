# tests/test_synthesizer.py
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock
from eternity.synthesizer import run_synthesis, _get_last_synthesis_date, _collect_new_summaries

FIXTURE_SUMMARY = Path(__file__).parent / "fixtures" / "sample_summary.md"

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
