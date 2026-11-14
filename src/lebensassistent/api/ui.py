"""Seitenrouting, lokale Assets und Browser-Fehlerseiten."""

from fastapi import APIRouter, FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException

from lebensassistent.api.catalog import finance_context
from lebensassistent.api.views import FRONTEND, SECTIONS, render

router = APIRouter()


@router.get("/", response_class=HTMLResponse, name="home")
async def home(request: Request) -> Response:
    return render(request, "home.html", title="Übersicht", active="home")


@router.get("/bereiche/{section_key}", response_class=HTMLResponse, name="section")
async def section(request: Request, section_key: str) -> Response:
    selected = next((item for item in SECTIONS if item.key == section_key), None)
    if selected is None:
        raise HTTPException(status_code=404)
    if selected.key == "finanzen":
        return render(
            request,
            "accounts.html",
            title=selected.title,
            active=selected.key,
            **finance_context(request),
        )
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
            or exc.status_code not in (403, 404, 405)
            or "text/html" not in request.headers.get("accept", "")
        ):
            return await http_exception_handler(request, exc)
        title, message = (
            ("Seite nicht gefunden", "Diese Seite gibt es hier leider nicht.")
            if exc.status_code == 404
            else ("Anfrage nicht unterstützt", "Diese Seite lässt sich nur anzeigen.")
        )
        if exc.status_code == 403:
            title, message = (
                "Anfrage nicht zulässig",
                "Bitte lade die Seite neu und versuche es erneut.",
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
