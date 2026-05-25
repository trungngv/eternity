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


def episode_dir_name(entry: VideoEntry) -> str:
    date = entry.upload_date or datetime.now(tz=timezone.utc).strftime("%Y%m%d")
    y, m, d = date[:4], date[4:6], date[6:8]
    return f"{y}-{m}-{d}_{_slugify(entry.title)}"


def _is_processed(entry: VideoEntry, episodes_dir: Path) -> bool:
    return (episodes_dir / episode_dir_name(entry)).exists()


def _passes_filters(entry: VideoEntry, filters) -> bool:
    duration_minutes = entry.duration / 60
    if duration_minutes < filters.min_duration_minutes:
        return False
    if duration_minutes > filters.max_duration_minutes:
        return False
    title_lower = entry.title.lower()
    for keyword in filters.exclude_title_keywords:
        if keyword.lower() in title_lower:
            return False
    if entry.upload_date and len(entry.upload_date) == 8:
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
            upload_date=item.get("upload_date") or "",
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
