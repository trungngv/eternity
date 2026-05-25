# tests/test_summarizer.py
from pathlib import Path
from unittest.mock import patch, MagicMock
from eternity.summarizer import summarize_episode, _truncate_transcript

FIXTURE_TRANSCRIPT = Path(__file__).parent / "fixtures" / "sample_transcript.txt"

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
