"""Schlanke Formular-Endpunkte; Fachregeln bleiben in den Services."""

import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from pydantic import ValidationError

from lebensassistent.api.forms import read_form
from lebensassistent.api.views import local_path, render
from lebensassistent.services.catalog import (
    AccountInput,
    CatalogError,
    CatalogService,
    CategoryInput,
)
from lebensassistent.services.values import parse_eur

router = APIRouter()
ACCOUNT_TYPES = {
    "checking": "Girokonto",
    "savings": "Sparkonto",
    "cash": "Bargeld",
    "credit_card": "Kreditkarte",
}
NOTICES = {
    "account-created": "Konto angelegt.",
    "category-created": "Kategorie angelegt.",
    "status-saved": "Status gespeichert.",
}


def service(request: Request) -> CatalogService:
    database = getattr(request.app.state, "database", None)
    if database is None:
        raise HTTPException(503, "Kontoverwaltung derzeit nicht verfügbar.")
    return CatalogService(database)


def finance_context(request: Request) -> dict:
    available = hasattr(request.app.state, "database")
    catalog = service(request) if available else None
    return {
        "db_available": available,
        "accounts": catalog.accounts() if catalog else [],
        "categories": catalog.categories() if catalog else [],
        "csrf_token": request.app.state.csrf_token,
        "account_types": ACCOUNT_TYPES,
        "notice": NOTICES.get(request.query_params.get("notice", "")),
        "errors": {},
        "values": {
            "account": {
                "name": "",
                "account_type": "checking",
                "opening_balance": "0,00",
                "opening_date": datetime.now(ZoneInfo("Europe/Berlin"))
                .date()
                .isoformat(),
                "notes": "",
            },
            "category": {"name": "", "kind": "expense", "parent_id": ""},
        },
    }


def invalid_form(
    request: Request, section: str, values: dict, errors: dict, status: int = 422
) -> Response:
    context = finance_context(request)
    context["values"][section].update(values)
    context["errors"] = errors
    return render(
        request,
        "accounts.html",
        title="Konten & Buchungen",
        active="finanzen",
        status_code=status,
        **context,
    )


def saved(request: Request, notice: str, anchor: str) -> RedirectResponse:
    target = local_path(request, "section", section_key="finanzen")
    return RedirectResponse(
        f"{target}?notice={notice}#{anchor}",
        status_code=303,
        headers={"Cache-Control": "no-store"},
    )


def validation_errors(error: ValidationError, section: str) -> dict[str, str]:
    result = {}
    for item in error.errors(include_input=False, include_url=False):
        field = item["loc"][0]
        messages = {
            "name": "Bitte einen Namen mit 1 bis 100 Zeichen eingeben.",
            "opening_date": "Bitte ein gültiges Kalenderdatum eingeben.",
            "account_type": "Bitte eine gültige Kontoart auswählen.",
            "notes": "Die Notiz darf höchstens 2000 Zeichen enthalten.",
            "kind": "Bitte Einnahme oder Ausgabe wählen.",
            "parent_id": "Bitte eine gültige Oberkategorie wählen.",
        }
        result[f"{section}.{field}"] = messages.get(
            field, "Bitte eine gültige Angabe machen."
        )
    return result


@router.post("/konten", name="create_account")
async def create_account(request: Request) -> Response:
    form = await read_form(
        request, {"name", "account_type", "opening_balance", "opening_date", "notes"}
    )
    catalog = service(request)
    try:
        cents = parse_eur(form.get("opening_balance", ""))
    except ValueError as error:
        return invalid_form(
            request, "account", form, {"account.opening_balance": str(error)}
        )
    try:
        values = AccountInput.model_validate(
            {
                "name": form.get("name", ""),
                "account_type": form.get("account_type", ""),
                "opening_balance_cents": cents,
                "opening_date": form.get("opening_date", ""),
                "notes": form.get("notes") or None,
            }
        )
        catalog.create_account(values)
    except ValidationError as error:
        return invalid_form(
            request, "account", form, validation_errors(error, "account")
        )
    except sqlite3.Error:
        return invalid_form(
            request,
            "account",
            form,
            {"global": "Speichern ist gerade nicht möglich. Bitte erneut versuchen."},
            503,
        )
    return saved(request, "account-created", "konten")


@router.post("/kategorien", name="create_category")
async def create_category(request: Request) -> Response:
    form = await read_form(request, {"name", "kind", "parent_id"})
    catalog = service(request)
    try:
        parent_id = int(form["parent_id"]) if form.get("parent_id") else None
        values = CategoryInput.model_validate(
            {
                "name": form.get("name", ""),
                "kind": form.get("kind", ""),
                "parent_id": parent_id,
            }
        )
        catalog.create_category(values)
    except ValidationError as error:
        return invalid_form(
            request, "category", form, validation_errors(error, "category")
        )
    except CatalogError as error:
        return invalid_form(
            request, "category", form, {f"category.{error.field}": str(error)}
        )
    except ValueError:
        return invalid_form(
            request,
            "category",
            form,
            {"category.parent_id": "Bitte eine gültige Oberkategorie wählen."},
        )
    except sqlite3.Error:
        return invalid_form(
            request,
            "category",
            form,
            {"global": "Speichern ist gerade nicht möglich. Bitte erneut versuchen."},
            503,
        )
    return saved(request, "category-created", "kategorien")


async def change_status(request: Request, table: str, entity_id: int) -> Response:
    form = await read_form(request, {"active"})
    if form.get("active") not in ("0", "1"):
        raise HTTPException(400, "Invalid status")
    catalog = service(request)
    try:
        catalog.set_active(table, entity_id, form["active"] == "1")
    except CatalogError as error:
        if error.not_found:
            raise HTTPException(404, "Not Found") from None
        return invalid_form(
            request,
            "category" if table == "categories" else "account",
            {},
            {"global": str(error)},
        )
    except sqlite3.Error:
        return invalid_form(
            request,
            "account",
            {},
            {"global": "Speichern ist gerade nicht möglich. Bitte erneut versuchen."},
            503,
        )
    return saved(
        request, "status-saved", "kategorien" if table == "categories" else "konten"
    )


@router.post("/konten/{entity_id}/status", name="account_status")
async def account_status(request: Request, entity_id: int) -> Response:
    return await change_status(request, "accounts", entity_id)


@router.post("/kategorien/{entity_id}/status", name="category_status")
async def category_status(request: Request, entity_id: int) -> Response:
    return await change_status(request, "categories", entity_id)
