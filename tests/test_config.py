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
      max_episodes_per_run: 10
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
    assert ch.filters.max_episodes_per_run == 10
    assert ch.filters.max_transcript_tokens == 50000


def test_unknown_filter_key_raises_value_error(tmp_path):
    yaml_text = """\
channels:
  - id: test
    name: Test
    url: https://youtube.com/@test
    check_frequency: daily
    filters:
      unknown_key: 42
"""
    f = tmp_path / "channels.yaml"
    f.write_text(yaml_text)
    import pytest
    with pytest.raises(ValueError, match="Invalid filter key"):
        load_channels(f)


def test_load_minimal_config_uses_defaults(tmp_path):
    f = tmp_path / "channels.yaml"
    f.write_text(MINIMAL_YAML)
    channels = load_channels(f)
    ch = channels[0]
    assert ch.filters.min_duration_minutes == 0
    assert ch.filters.max_duration_minutes == 300
    assert ch.filters.exclude_title_keywords == []
    assert ch.filters.backfill_days == 30
    assert ch.filters.max_episodes_per_run == 10
    assert ch.filters.max_transcript_tokens == 50000
