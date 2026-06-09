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
        state: dict = {"last_checked": "", "videos": []}
        if channel_json.exists():
            state = json.loads(channel_json.read_text())

        click.echo(f"Checking {ch.name}...")
        new_episodes = find_new_episodes(ch, channel_dir)
        click.echo(f"  {len(new_episodes)} new episode(s) found")

        for video in new_episodes:
            slug = episode_dir_name(video)
            episode_dir = channel_dir / "episodes" / slug
            episode_dir.mkdir(parents=True, exist_ok=True)

            transcript_path = episode_dir / "transcript.txt"

            click.echo(f"  -> {video.title}")
            try:
                if not transcript_path.exists():
                    fetch_transcript(video.id, transcript_path)
                
                # Add video entry to channel.json
                now = datetime.now(tz=timezone.utc).isoformat()
                video_entry = {
                    "video_id": video.id,
                    "title": video.title,
                    "url": video.webpage_url,
                    "fetched_date": now,
                    "summarized_date": None,
                    "error": None,
                }
                # Update or add entry
                existing = [v for v in state["videos"] if v["video_id"] == video.id]
                if existing:
                    existing[0].update(video_entry)
                else:
                    state["videos"].append(video_entry)
                
                click.echo("    Transcript saved")
            except Exception as e:
                click.echo(f"    Error: {e}", err=True)
                video_entry = {
                    "video_id": video.id,
                    "title": video.title,
                    "url": video.webpage_url,
                    "fetched_date": None,
                    "summarized_date": None,
                    "error": str(e),
                }
                # Add error entry
                existing = [v for v in state["videos"] if v["video_id"] == video.id]
                if not existing:
                    state["videos"].append(video_entry)

        state["last_checked"] = datetime.now(tz=timezone.utc).isoformat()
        channel_json.write_text(json.dumps(state, indent=2))


@cli.command()
@click.option("--channel", default=None, help="Summarize a specific channel ID only")
def summarize_episodes(channel):
    """Summarize episodes that have transcripts but no summaries."""
    from .config import load_channels
    from .watcher import episode_dir_name, VideoEntry
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

        channel_json = channel_dir / "channel.json"
        if not channel_json.exists():
            continue

        state = json.loads(channel_json.read_text())
        videos = state.get("videos", [])

        click.echo(f"Summarizing {ch.name}...")
        count = 0
        updated = 0

        for video_entry in sorted(videos, key=lambda v: v.get("fetched_date") or ""):
            # Skip if has an error
            if video_entry.get("error"):
                continue

            # Skip if not successfully fetched
            if not video_entry.get("fetched_date"):
                continue

            # Build episode directory and check for transcript/summary
            temp_entry = VideoEntry(
                id=video_entry["video_id"],
                title=video_entry["title"],
                upload_date="",
                duration=0,
                webpage_url=video_entry["url"],
            )
            slug = episode_dir_name(temp_entry)
            episode_dir = channel_dir / "episodes" / slug
            transcript_path = episode_dir / "transcript.txt"
            summary_path = episode_dir / "summary.md"

            if not transcript_path.exists():
                continue

            # If summary exists but summarized_date is not set, update it
            if summary_path.exists() and not video_entry.get("summarized_date"):
                video_entry["summarized_date"] = datetime.now(tz=timezone.utc).isoformat()
                updated += 1
                continue

            # Skip if already summarized
            if video_entry.get("summarized_date"):
                continue

            # Generate new summary
            click.echo(f"  -> {video_entry['title']}")

            try:
                summarize_episode(
                    video_id=video_entry["video_id"],
                    video_title=video_entry["title"],
                    video_url=video_entry["url"],
                    upload_date=video_entry.get("upload_date", ""),
                    transcript_path=transcript_path,
                    summary_path=summary_path,
                    max_tokens=ch.filters.max_transcript_tokens,
                )
                # Update summarized_date in channel.json
                video_entry["summarized_date"] = datetime.now(tz=timezone.utc).isoformat()
                click.echo("    Done")
                count += 1
                if count >= ch.filters.max_episodes_per_run:
                    break
            except Exception as e:
                click.echo(f"    Error: {e}", err=True)
                video_entry["error"] = str(e)

        # Save updated state
        channel_json.write_text(json.dumps(state, indent=2))
        click.echo(f"  Summarized {count} episode(s), updated {updated} existing")


@cli.command()
def synthesize():
    """Run weekly knowledge synthesis across all channels."""
    from .synthesizer import run_synthesis
    click.echo("Running synthesis...")
    run_synthesis(KNOWLEDGE_PATH)
    click.echo("Done.")


@cli.command()
@click.option("--out", default="docs", show_default=True, help="Output directory for static HTML")
def build(out):
    """Render the knowledge base to static HTML."""
    from .web.build import build as _build
    out_dir = Path(out)
    click.echo(f"Building static site → {out_dir}/")
    _build(KNOWLEDGE_PATH, out_dir)
    click.echo("Done.")


@cli.command()
@click.option("--message", default=None, help="Git commit message (default: auto)")
def publish(message):
    """Build static site and push docs/ to GitHub Pages."""
    import subprocess as sp
    from .web.build import build as _build
    from datetime import datetime, timezone

    out_dir = Path("docs")
    click.echo("Building static site...")
    _build(KNOWLEDGE_PATH, out_dir)

    commit_msg = message or f"Update site {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC"
    click.echo(f"Committing: {commit_msg}")
    sp.run(["git", "add", "docs/"], check=True)
    result = sp.run(["git", "diff", "--cached", "--quiet"])
    if result.returncode == 0:
        click.echo("Nothing to commit.")
        return
    sp.run(["git", "commit", "-m", commit_msg], check=True)
    sp.run(["git", "push"], check=True)
    click.echo("Pushed to GitHub.")


@cli.command()
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=8000, show_default=True)
def serve(host, port):
    """Start the local web app."""
    import uvicorn
    uvicorn.run("eternity.web.app:app", host=host, port=port, reload=True)
