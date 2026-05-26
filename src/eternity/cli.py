# src/eternity/cli.py
import json
from datetime import datetime, timezone
from pathlib import Path

import click

CONFIG_PATH = Path("config/channels.yaml")
KNOWLEDGE_PATH = Path("knowledge")


@click.group()
def cli():
    pass


@cli.command()
@click.option("--channel", default=None, help="Fetch transcripts from a specific channel ID only")
def fetch(channel):
    """Check for new episodes and download transcripts."""
    from .config import load_channels
    from .watcher import find_new_episodes, episode_dir_name
    from .fetcher import fetch_transcript

    channels = load_channels(CONFIG_PATH)
    if channel:
        channels = [c for c in channels if c.id == channel]
        if not channels:
            raise click.ClickException(f"Channel '{channel}' not found in config")

    for ch in channels:
        channel_dir = KNOWLEDGE_PATH / "channels" / ch.id
        channel_dir.mkdir(parents=True, exist_ok=True)

        channel_json = channel_dir / "channel.json"
        state: dict = {"last_checked": "", "errors": []}
        if channel_json.exists():
            state = json.loads(channel_json.read_text())
        if "errors" not in state:
            state["errors"] = []

        click.echo(f"Checking {ch.name}...")
        new_episodes = find_new_episodes(ch, channel_dir)
        click.echo(f"  {len(new_episodes)} new episode(s) found")

        for video in new_episodes:
            slug = episode_dir_name(video)
            episode_dir = channel_dir / "episodes" / slug
            episode_dir.mkdir(parents=True, exist_ok=True)

            transcript_path = episode_dir / "transcript.txt"
            metadata_path = episode_dir / "episode.json"

            click.echo(f"  -> {video.title}")
            try:
                if not transcript_path.exists():
                    fetch_transcript(video.id, transcript_path)
                
                # Store episode metadata for later use by summarize
                metadata = {
                    "video_id": video.id,
                    "title": video.title,
                    "url": video.webpage_url,
                    "upload_date": video.upload_date,
                }
                metadata_path.write_text(json.dumps(metadata, indent=2))
                click.echo("    Transcript saved")
            except Exception as e:
                click.echo(f"    Error: {e}", err=True)
                state["errors"].append({
                    "video_id": video.id,
                    "reason": str(e),
                    "attempted_at": datetime.now(tz=timezone.utc).isoformat(),
                })

        state["last_checked"] = datetime.now(tz=timezone.utc).isoformat()
        channel_json.write_text(json.dumps(state, indent=2))


@cli.command()
@click.option("--channel", default=None, help="Summarize a specific channel ID only")
def summarize_episodes(channel):
    """Summarize episodes that have transcripts but no summaries."""
    from .config import load_channels
    from .summarizer import summarize_episode

    channels = load_channels(CONFIG_PATH)
    if channel:
        channels = [c for c in channels if c.id == channel]
        if not channels:
            raise click.ClickException(f"Channel '{channel}' not found in config")

    for ch in channels:
        channel_dir = KNOWLEDGE_PATH / "channels" / ch.id
        if not channel_dir.exists():
            continue

        episodes_dir = channel_dir / "episodes"
        if not episodes_dir.exists():
            continue

        click.echo(f"Summarizing {ch.name}...")
        count = 0

        for episode_dir in sorted(episodes_dir.iterdir()):
            if not episode_dir.is_dir():
                continue

            transcript_path = episode_dir / "transcript.txt"
            summary_path = episode_dir / "summary.md"
            metadata_path = episode_dir / "episode.json"

            if not transcript_path.exists() or summary_path.exists():
                continue

            # Read episode metadata (saved during fetch)
            if not metadata_path.exists():
                click.echo(f"  -> {episode_dir.name} (skipped: no metadata)")
                continue

            metadata = json.loads(metadata_path.read_text())

            click.echo(f"  -> {metadata['title']}")

            try:
                summarize_episode(
                    video_id=metadata["video_id"],
                    video_title=metadata["title"],
                    video_url=metadata["url"],
                    upload_date=metadata["upload_date"],
                    transcript_path=transcript_path,
                    summary_path=summary_path,
                    max_tokens=ch.filters.max_transcript_tokens,
                )
                click.echo("    Done")
                count += 1
            except Exception as e:
                click.echo(f"    Error: {e}", err=True)

        click.echo(f"  Summarized {count} episode(s)")


@cli.command()
def synthesize():
    """Run weekly knowledge synthesis across all channels."""
    from .synthesizer import run_synthesis
    click.echo("Running synthesis...")
    run_synthesis(KNOWLEDGE_PATH)
    click.echo("Done.")


@cli.command()
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=8000, show_default=True)
def serve(host, port):
    """Start the local web app."""
    import uvicorn
    uvicorn.run("eternity.web.app:app", host=host, port=port, reload=True)
