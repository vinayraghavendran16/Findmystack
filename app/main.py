from __future__ import annotations

import csv
import io
from pathlib import Path

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from . import models
from .db import get_session, init_db
from .providers import all_providers
from .runner import run_search


BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(title="Findmystack")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_session)):
    provider_status = [(p.name, p.source_type, p.is_configured()) for p in all_providers()]
    recent = db.execute(
        select(models.Search).order_by(models.Search.created_at.desc()).limit(10)
    ).scalars().all()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "provider_status": provider_status,
        "recent": recent,
    })


@app.post("/search")
async def do_search(
    tool_name: str = Form(...),
    vendor_url: str = Form(""),
    db: Session = Depends(get_session),
):
    search = await run_search(db, tool_name.strip(), vendor_url.strip() or None)
    return RedirectResponse(url=f"/search/{search.id}", status_code=303)


@app.get("/search/{search_id}", response_class=HTMLResponse)
def show_search(search_id: int, request: Request, db: Session = Depends(get_session)):
    search = db.get(models.Search, search_id)
    if search is None:
        return HTMLResponse("Not found", status_code=404)
    confirmations = db.execute(
        select(models.Confirmation)
        .join(models.Hit, models.Hit.id == models.Confirmation.hit_id)
        .where(models.Hit.search_id == search_id)
        .order_by(models.Confirmation.confidence.desc())
    ).scalars().all()
    hit_count = db.execute(
        select(func.count()).select_from(models.Hit).where(models.Hit.search_id == search_id)
    ).scalar_one()
    return templates.TemplateResponse("results.html", {
        "request": request,
        "search": search,
        "confirmations": confirmations,
        "hit_count": hit_count,
    })


@app.get("/search/{search_id}/export.csv")
def export_csv(search_id: int, db: Session = Depends(get_session)):
    rows = db.execute(
        select(models.Confirmation)
        .join(models.Hit, models.Hit.id == models.Confirmation.hit_id)
        .where(models.Hit.search_id == search_id)
        .order_by(models.Confirmation.confidence.desc())
    ).scalars().all()

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["tool", "company", "confidence", "source_type", "source_url", "evidence"])
    for r in rows:
        w.writerow([r.tool_name, r.company, f"{r.confidence:.2f}", r.source_type, r.source_url, r.evidence_snippet])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="findmystack-{search_id}.csv"'},
    )


@app.get("/history", response_class=HTMLResponse)
def history(request: Request, db: Session = Depends(get_session)):
    searches = db.execute(
        select(models.Search).order_by(models.Search.created_at.desc()).limit(200)
    ).scalars().all()
    return templates.TemplateResponse("history.html", {"request": request, "searches": searches})
