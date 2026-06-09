from dataclasses import dataclass, field
from pathlib import Path
import yaml


@dataclass
class ChannelFilters:
    min_duration_minutes: int = 0
    max_duration_minutes: int = 300
    exclude_title_keywords: list[str] = field(default_factory=list)
    backfill_days: int = 30
    max_episodes_per_run: int = 10
    max_transcript_tokens: int = 50000


@dataclass
class Channel:
    id: str
    name: str
    url: str
    check_frequency: str
    filters: ChannelFilters


def load_channels(config_path: Path) -> list[Channel]:
    with open(config_path) as f:
        data = yaml.safe_load(f)
    channels = []
    for c in data["channels"]:
        try:
            filters = ChannelFilters(**c.get("filters", {}))
        except TypeError as e:
            raise ValueError(f"Invalid filter key in channel '{c.get('id', '?')}': {e}") from e
        try:
            channels.append(Channel(
                id=c["id"],
                name=c["name"],
                url=c["url"],
                check_frequency=c["check_frequency"],
                filters=filters,
            ))
        except KeyError as e:
            raise ValueError(f"Channel entry missing required field {e}") from e
    return channels
