"""Gemeinsame HTML-Darstellung und lokale Pfade für serverseitige Seiten."""

from datetime import date
from pathlib import Path
from typing import NamedTuple

from fastapi import Request
from fastapi.responses import Response
from fastapi.templating import Jinja2Templates

from lebensassistent.services.values import format_eur

FRONTEND = Path(__file__).resolve().parents[1] / "frontend"
templates = Jinja2Templates(directory=FRONTEND / "templates")
templates.env.filters["eur"] = format_eur


def format_date(value: str) -> str:
    parsed = date.fromisoformat(value)
    return f"{parsed.day:02d}.{parsed.month:02d}.{parsed.year:04d}"


templates.env.filters["local_date"] = format_date


def local_path(request: Request, name: str, **params: str) -> str:
    prefix = request.scope.get("root_path", "").rstrip("/")
    return f"{prefix}{request.app.url_path_for(name, **params)}"


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
        return local_path(request, name, **params)

    response = templates.TemplateResponse(
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
    response.headers["Cache-Control"] = "no-store"
    return response
