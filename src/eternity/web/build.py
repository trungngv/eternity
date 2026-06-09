"""Render the Eternity web app to static HTML in docs/."""
import shutil
from pathlib import Path

import mistune
from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = Path(__file__).parent / "templates"
md = mistune.create_markdown()


def _render_md(path: Path) -> str:
    return md(path.read_text()) if path.exists() else "<p><em>Not found.</em></p>"


def build(knowledge_dir: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)

    def write(rel_path: str, template_name: str, ctx: dict) -> None:
        dest = out_dir / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(env.get_template(template_name).render(**ctx))

    # index
    channels = []
    channels_dir = knowledge_dir / "channels"
    if channels_dir.exists():
        for ch_dir in sorted(channels_dir.iterdir()):
            if ch_dir.is_dir():
                ep_summaries = sorted(
                    (ch_dir / "episodes").glob("*/summary.md"), reverse=True
                )[:5]
                channels.append({
                    "id": ch_dir.name,
                    "episodes": [e.parent.name for e in ep_summaries],
                })
    synthesis_dir = knowledge_dir / "synthesis"
    recent_synthesis = []
    if synthesis_dir.exists():
        recent_synthesis = [f.stem for f in sorted(synthesis_dir.glob("*.md"), reverse=True)[:3]]
    write("index.html", "index.html", {"channels": channels, "recent_synthesis": recent_synthesis})

    # channels + episodes
    if channels_dir.exists():
        for ch_dir in sorted(channels_dir.iterdir()):
            if not ch_dir.is_dir():
                continue
            channel_id = ch_dir.name
            episodes_dir = ch_dir / "episodes"
            episodes = []
            if episodes_dir.exists():
                episodes = [
                    d.name for d in sorted(episodes_dir.iterdir(), reverse=True)
                    if d.is_dir() and (d / "summary.md").exists()
                ]
            write(f"channels/{channel_id}/index.html", "channel.html", {
                "channel_id": channel_id,
                "episodes": episodes,
            })
            for slug in episodes:
                path = ch_dir / "episodes" / slug / "summary.md"
                write(f"channels/{channel_id}/episodes/{slug}/index.html", "episode.html", {
                    "channel_id": channel_id,
                    "slug": slug,
                    "content": _render_md(path),
                })

    # lessons
    write("lessons/index.html", "lessons.html", {
        "content": _render_md(knowledge_dir / "master_lessons.md"),
    })

    # topics
    topics_dir = knowledge_dir / "topics"
    if topics_dir.exists():
        for topic_file in topics_dir.glob("*.md"):
            topic = topic_file.stem
            write(f"topics/{topic}/index.html", "topic.html", {
                "topic": topic,
                "content": _render_md(topic_file),
            })

    # synthesis list + individual weeks
    weeks = []
    if synthesis_dir.exists():
        weeks = [f.stem for f in sorted(synthesis_dir.glob("*.md"), reverse=True)]
    write("synthesis/index.html", "synthesis.html", {"weeks": weeks})
    for week in weeks:
        path = synthesis_dir / f"{week}.md"
        write(f"synthesis/{week}/index.html", "synthesis.html", {
            "weeks": [],
            "week": week,
            "content": _render_md(path),
        })
