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
