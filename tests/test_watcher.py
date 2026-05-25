from datetime import datetime, timedelta, timezone
from pathlib import Path
from eternity.watcher import (
    VideoEntry,
    _passes_filters,
    _is_processed,
    episode_dir_name,
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
    dir_name = episode_dir_name(video)
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
    name = episode_dir_name(video)
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    assert name.startswith(today)
    assert "great-episode" in name
