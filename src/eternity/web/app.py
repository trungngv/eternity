import subprocess
from pathlib import Path

import mistune
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

KNOWLEDGE_DIR = Path("knowledge")
TEMPLATES_DIR = Path(__file__).parent / "templates"

app = FastAPI(title="Eternity")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
md = mistune.create_markdown()


def render_md(path: Path) -> str:
    return md(path.read_text()) if path.exists() else "<p><em>Not found.</em></p>"


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    channels = []
    channels_dir = KNOWLEDGE_DIR / "channels"
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
    synthesis_dir = KNOWLEDGE_DIR / "synthesis"
    recent_synthesis = []
    if synthesis_dir.exists():
        recent_synthesis = [f.stem for f in sorted(synthesis_dir.glob("*.md"), reverse=True)[:3]]
    return templates.TemplateResponse(request, "index.html", {
        "channels": channels,
        "recent_synthesis": recent_synthesis,
    })


@app.get("/channels/{channel_id}", response_class=HTMLResponse)
async def channel(request: Request, channel_id: str):
    episodes_dir = KNOWLEDGE_DIR / "channels" / channel_id / "episodes"
    episodes = []
    if episodes_dir.exists():
        episodes = [d.name for d in sorted(episodes_dir.iterdir(), reverse=True) if d.is_dir()]
    return templates.TemplateResponse(request, "channel.html", {
        "channel_id": channel_id,
        "episodes": episodes,
    })


@app.get("/channels/{channel_id}/episodes/{slug}", response_class=HTMLResponse)
async def episode(request: Request, channel_id: str, slug: str):
    path = KNOWLEDGE_DIR / "channels" / channel_id / "episodes" / slug / "summary.md"
    return templates.TemplateResponse(request, "episode.html", {
        "channel_id": channel_id,
        "slug": slug,
        "content": render_md(path),
    })


@app.get("/lessons", response_class=HTMLResponse)
async def lessons(request: Request):
    return templates.TemplateResponse(request, "lessons.html", {
        "content": render_md(KNOWLEDGE_DIR / "master_lessons.md"),
    })


@app.get("/topics/{topic}", response_class=HTMLResponse)
async def topic(request: Request, topic: str):
    path = KNOWLEDGE_DIR / "topics" / f"{topic}.md"
    return templates.TemplateResponse(request, "topic.html", {
        "topic": topic,
        "content": render_md(path),
    })


@app.get("/synthesis", response_class=HTMLResponse)
async def synthesis_list(request: Request):
    synthesis_dir = KNOWLEDGE_DIR / "synthesis"
    files = sorted(synthesis_dir.glob("*.md"), reverse=True) if synthesis_dir.exists() else []
    return templates.TemplateResponse(request, "synthesis.html", {
        "weeks": [f.stem for f in files],
    })


@app.get("/synthesis/{week}", response_class=HTMLResponse)
async def synthesis_week(request: Request, week: str):
    path = KNOWLEDGE_DIR / "synthesis" / f"{week}.md"
    return templates.TemplateResponse(request, "synthesis.html", {
        "weeks": [],
        "week": week,
        "content": render_md(path),
    })


@app.get("/search", response_class=HTMLResponse)
async def search(request: Request, q: str = ""):
    results = []
    if q and KNOWLEDGE_DIR.exists():
        proc = subprocess.run(
            ["grep", "-ril", q, str(KNOWLEDGE_DIR)],
            capture_output=True, text=True, timeout=10,
        )
        for line in proc.stdout.strip().splitlines():
            try:
                results.append(Path(line).relative_to(KNOWLEDGE_DIR))
            except ValueError:
                pass
    return templates.TemplateResponse(request, "search.html", {
        "query": q,
        "results": results,
    })
