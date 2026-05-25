from dataclasses import dataclass
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
