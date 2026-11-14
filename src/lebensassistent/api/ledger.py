"""Serverseitiges Formular für eine normale Einnahme oder Ausgabe."""

import sqlite3

from fastapi import APIRouter, Request
from fastapi.responses import Response
from pydantic import ValidationError

from lebensassistent.api.catalog import invalid_form, saved, service
from lebensassistent.api.forms import read_form
from lebensassistent.services.ledger import LedgerError, LedgerService, PostingInput
from lebensassistent.services.values import parse_eur

router = APIRouter()


@router.post("/buchungen", name="create_transaction")
async def create_transaction(request: Request) -> Response:
    form = await read_form(
        request,
        {
            "submission_id",
            "kind",
            "account_id",
            "category_id",
            "amount",
            "booked_date",
            "description",
        },
    )
    catalog = service(request)
    try:
        amount = parse_eur(form.get("amount", ""))
    except ValueError as error:
        return invalid_form(
            request, "transaction", form, {"transaction.amount": str(error)}
        )
    try:
        ids = {key: int(form.get(key, "")) for key in ("account_id", "category_id")}
    except ValueError:
        return invalid_form(
            request,
            "transaction",
            form,
            {"global": "Bitte ein gültiges Konto und eine Kategorie auswählen."},
        )
    try:
        data = {
            **ids,
            "kind": form.get("kind", ""),
            "amount_cents": amount,
            "description": form.get("description") or None,
            "submission_id": form.get("submission_id", ""),
        }
        if form.get("booked_date"):
            data["booked_date"] = form["booked_date"]
        LedgerService(catalog.database).post(PostingInput.model_validate(data))
    except ValidationError as error:
        messages = {
            "amount_cents": "Bitte einen positiven Betrag größer als null eingeben.",
            "account_id": "Bitte ein gültiges Konto auswählen.",
            "category_id": "Bitte eine gültige Kategorie auswählen.",
            "kind": "Bitte Einnahme oder Ausgabe wählen.",
            "booked_date": "Bitte ein gültiges Kalenderdatum eingeben.",
            "description": "Die Notiz darf höchstens 2000 Zeichen enthalten.",
            "submission_id": "Ungültige Formularanfrage. Bitte die Seite neu laden.",
        }
        errors = {}
        for item in error.errors(include_input=False, include_url=False):
            field = item["loc"][0]
            errors[f"transaction.{'amount' if field == 'amount_cents' else field}"] = (
                messages[field]
            )
        return invalid_form(request, "transaction", form, errors)
    except LedgerError as error:
        key = "global" if error.field == "global" else f"transaction.{error.field}"
        return invalid_form(
            request,
            "transaction",
            form,
            {key: str(error)},
            409 if error.conflict else 422,
        )
    except sqlite3.Error:
        return invalid_form(
            request,
            "transaction",
            form,
            {"global": "Speichern ist gerade nicht möglich. Bitte erneut versuchen."},
            503,
        )
    return saved(request, "transaction-created", "buchungen")
