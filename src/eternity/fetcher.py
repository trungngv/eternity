from dataclasses import dataclass
import re
import shutil
import tempfile
from pathlib import Path
from youtube_transcript_api import YouTubeTranscriptApi


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
        "nocheckcertificate": True,
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
        entries = YouTubeTranscriptApi().fetch(
            video_id, languages=["en", "en-US", "en-GB"]
        )
        lines = []
        for entry in entries:
            start = int(entry.start)
            h, m = divmod(start // 60, 60)
            ts = f"{h}:{m:02d}" if h else f"0:{m:02d}"
            lines.append(f"[{ts}] {entry.text}")
        output_path.write_text("\n".join(lines))
    except (NoTranscriptFound, TranscriptsDisabled) as e:
        raise FetchError(f"No transcript available for {video_id}: {e}") from e
