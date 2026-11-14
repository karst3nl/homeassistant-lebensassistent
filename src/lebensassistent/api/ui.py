"""Statische Seiten; Pfade stammen ausschließlich aus dem ASGI-Kontext."""

from pathlib import Path
from typing import NamedTuple

from fastapi import APIRouter, FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException

FRONTEND = Path(__file__).resolve().parents[1] / "frontend"
templates = Jinja2Templates(directory=FRONTEND / "templates")
router = APIRouter()


class Section(NamedTuple):
    key: str
    title: str
    description: str
    icon: str


SECTIONS = (
    Section(
        "finanzen", "Konten & Buchungen", "Einnahmen und Ausgaben im Blick.", "wallet"
    ),
    Section(
        "fixkosten",
        "Fixkosten & Planung",
        "Regelmäßige Kosten vorausschauend planen.",
        "calendar",
    ),
    Section(
        "sparziele", "Sparziele", "Schritt für Schritt deinen Zielen näher.", "target"
    ),
    Section(
        "fahrzeuge", "Fahrzeuge", "Tanken, Wartung und Termine an einem Ort.", "car"
    ),
    Section(
        "projekte", "Projekte", "Ideen ordnen und Vorhaben voranbringen.", "folder"
    ),
    Section(
        "zeit",
        "Zeit & Kalender",
        "Aufgaben, Termine und Zeit zusammenbringen.",
        "clock",
    ),
    Section(
        "einstellungen",
        "Einstellungen",
        "Lebensassistent passend zu deinem Alltag.",
        "settings",
    ),
)


def render(
    request: Request, template: str, *, status_code: int = 200, **context: object
) -> Response:
    def local_url_for(name: str, **params: str) -> str:
        prefix = request.scope.get("root_path", "").rstrip("/")
        return f"{prefix}{request.app.url_path_for(name, **params)}"

    return templates.TemplateResponse(
        request=request,
        name=template,
        context={
            "sections": SECTIONS,
            "active": "",
            "url_for": local_url_for,
            **context,
        },
        status_code=status_code,
    )


@router.get("/", response_class=HTMLResponse, name="home")
async def home(request: Request) -> Response:
    return render(request, "home.html", title="Übersicht", active="home")


@router.get("/bereiche/{section_key}", response_class=HTMLResponse, name="section")
async def section(request: Request, section_key: str) -> Response:
    selected = next((item for item in SECTIONS if item.key == section_key), None)
    if selected is None:
        raise HTTPException(status_code=404)
    return render(
        request,
        "section.html",
        title=selected.title,
        active=selected.key,
        section=selected,
    )


def install_ui(application: FastAPI) -> None:
    application.mount(
        "/static", StaticFiles(directory=FRONTEND / "static"), name="static"
    )
    application.include_router(router)

    @application.exception_handler(HTTPException)
    async def browser_error(request: Request, exc: HTTPException) -> Response:
        health_paths = {"/health", f"{request.scope.get('root_path', '')}/health"}
        if (
            isinstance(request.scope.get("endpoint"), StaticFiles)
            or request.scope["path"] in health_paths
            or exc.status_code not in (404, 405)
            or "text/html" not in request.headers.get("accept", "")
        ):
            return await http_exception_handler(request, exc)
        title, message = (
            ("Seite nicht gefunden", "Diese Seite gibt es hier leider nicht.")
            if exc.status_code == 404
            else ("Anfrage nicht unterstützt", "Diese Seite lässt sich nur anzeigen.")
        )
        response = render(
            request,
            "error.html",
            status_code=exc.status_code,
            title=title,
            message=message,
            error_code=exc.status_code,
        )
        response.headers.update(exc.headers or {})
        return response
