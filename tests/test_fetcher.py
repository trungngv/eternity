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
    from types import SimpleNamespace
    output_path = tmp_path / "transcript.txt"
    mock_entries = [
        SimpleNamespace(start=0.0, duration=5.0, text="Hello world"),
        SimpleNamespace(start=65.0, duration=5.0, text="New minute content"),
    ]

    with patch("eternity.fetcher._download_subtitles", return_value=None), \
         patch("eternity.fetcher.YouTubeTranscriptApi") as MockAPI:
        MockAPI.return_value.fetch.return_value = mock_entries
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
        MockAPI.return_value.fetch.side_effect = NoTranscriptFound("abc123", ["en"], None)

        with pytest.raises(FetchError):
            fetch_transcript("abc123", output_path)
