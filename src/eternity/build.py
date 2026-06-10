import json
import re
from collections import defaultdict
from pathlib import Path

import mistune

from .config import load_channels

_md = mistune.create_markdown()

_CSS = """\
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:860px;margin:2rem auto;padding:0 1rem;color:#222;line-height:1.6}
a{color:#0066cc}
h1,h2{margin-top:1.5rem}
details{border:1px solid #ddd;border-radius:4px;margin:.5rem 0}
summary{padding:.75rem 1rem;cursor:pointer;font-weight:500;list-style:none}
summary::-webkit-details-marker{display:none}
summary::before{content:'\\25b8  ';color:#999}
details[open] summary::before{content:'\\25be  '}
summary:hover{background:#f5f5f5}
.ep{padding:1rem 1.25rem;border-top:1px solid #ddd}
.back{text-decoration:none;color:#666;font-size:.9rem}
ul{list-style:none;padding:0}
li{margin:.5rem 0}"""


def _slugify(title: str) -> str:
    # Must stay in sync with watcher._slugify
    slug = title.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug[:60].strip("-")


def _render_md(path: Path) -> str:
    return _md(path.read_text()) if path.exists() else ""


def _page(title: str, body: str) -> str:
    return (
        f'<!DOCTYPE html>\n<html lang="en">\n<head>\n'
        f'  <meta charset="utf-8">\n'
        f'  <meta name="viewport" content="width=device-width,initial-scale=1">\n'
        f'  <title>{title}</title>\n'
        f'  <style>{_CSS}</style>\n'
        f'</head>\n<body>\n{body}\n</body>\n</html>'
    )


def build(knowledge_dir: Path, out_dir: Path, config_path: Path) -> None:
    channel_names = {c.id: c.name for c in load_channels(config_path)}

    by_date: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    channels_dir = knowledge_dir / "channels"
    if not channels_dir.exists():
        return

    for ch_dir in sorted(channels_dir.iterdir()):
        if not ch_dir.is_dir():
            continue
        channel_json = ch_dir / "channel.json"
        if not channel_json.exists():
            continue
        state = json.loads(channel_json.read_text())
        for v in state.get("videos", []):
            if not v.get("summarized_date"):
                continue
            slug = _slugify(v["title"])
            summary_path = ch_dir / "episodes" / slug / "summary.md"
            if not summary_path.exists():
                continue
            date = v["summarized_date"][:10]
            by_date[date][ch_dir.name].append({
                "title": v["title"],
                "content": _render_md(summary_path),
            })

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / ".nojekyll").touch()
    sorted_dates = sorted(by_date.keys(), reverse=True)

    items = []
    for date in sorted_dates:
        count = sum(len(eps) for eps in by_date[date].values())
        s = "s" if count != 1 else ""
        items.append(
            f'  <li><a href="{date}/">{date}</a>'
            f' <span style="color:#666;font-size:.9rem">({count} episode{s})</span></li>'
        )
    body = "<h1>Knowledge Base</h1>\n<ul>\n" + "\n".join(items) + "\n</ul>"
    (out_dir / "index.html").write_text(_page("Knowledge Base", body))

    for date in sorted_dates:
        date_dir = out_dir / date
        date_dir.mkdir(exist_ok=True)
        sections = []
        for channel_id, episodes in sorted(by_date[date].items()):
            name = channel_names.get(channel_id, channel_id)
            details = "\n".join(
                f'<details>\n  <summary>{ep["title"]}</summary>\n'
                f'  <div class="ep">{ep["content"]}</div>\n</details>'
                for ep in episodes
            )
            sections.append(f"<h2>{name}</h2>\n{details}")
        body = (
            '<a class="back" href="../">← All dates</a>\n'
            f"<h1>{date}</h1>\n"
            + "\n".join(sections)
        )
        (date_dir / "index.html").write_text(_page(date, body))
