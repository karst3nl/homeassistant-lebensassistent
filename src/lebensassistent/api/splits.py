"""Aufteilungsformular mit geschützten serverseitigen Zeilenaktionen."""

import sqlite3
import uuid

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from pydantic import ValidationError

from lebensassistent.api.catalog import saved, service
from lebensassistent.api.forms import read_form
from lebensassistent.api.views import render
from lebensassistent.services.ledger import (
    MAX_SPLITS,
    LedgerError,
    LedgerService,
    SplitPostingInput,
    today_berlin,
)
from lebensassistent.services.values import parse_eur

router = APIRouter()
CORE_FIELDS = {
    "submission_id",
    "row_count",
    "intent",
    "kind",
    "account_id",
    "amount",
    "booked_date",
    "description",
}
ROW_FIELDS = {
    f"{name}_{index}"
    for index in range(MAX_SPLITS)
    for name in ("category", "amount", "memo")
}
SPLIT_FORM_FIELDS = 10 + 3 * MAX_SPLITS


def show(
    request: Request,
    values: dict | None = None,
    errors: dict | None = None,
    status: int = 200,
) -> Response:
    catalog = service(request)
    initial = {
        "submission_id": uuid.uuid4().hex,
        "kind": "expense",
        "account_id": "",
        "amount": "",
        "booked_date": today_berlin().isoformat(),
        "description": "",
        "rows": [{"category": "", "amount": "", "memo": ""} for _ in range(2)],
    }
    return render(
        request,
        "split_booking.html",
        title="Buchung aufteilen",
        active="finanzen",
        values=initial if values is None else values,
        errors=errors or {},
        accounts=catalog.accounts(),
        categories=catalog.categories(),
        csrf_token=request.app.state.csrf_token,
        max_splits=MAX_SPLITS,
        status_code=status,
    )


@router.get("/buchungen/aufteilen", name="split_booking", response_class=HTMLResponse)
async def split_booking(request: Request) -> Response:
    return show(request)


@router.post("/buchungen/aufteilen", name="submit_split_booking")
async def submit_split_booking(request: Request) -> Response:
    form = await read_form(
        request, CORE_FIELDS | ROW_FIELDS, max_fields=SPLIT_FORM_FIELDS
    )
    try:
        count = int(form.get("row_count", ""))
    except ValueError:
        raise HTTPException(400, "Invalid row count") from None
    if not 2 <= count <= MAX_SPLITS or any(
        int(key.rsplit("_", 1)[1]) >= count for key in form if key in ROW_FIELDS
    ):
        raise HTTPException(400, "Invalid row fields")
    values = {key: form.get(key, "") for key in CORE_FIELDS - {"intent", "row_count"}}
    values["rows"] = [
        {
            name: form.get(f"{name}_{index}", "")
            for name in ("category", "amount", "memo")
        }
        for index in range(count)
    ]
    intent = form.get("intent", "save")
    if intent == "add":
        if count == MAX_SPLITS:
            return show(
                request,
                values,
                {"global": "Höchstens 20 Teilbeträge sind möglich."},
                422,
            )
        values["rows"].append({"category": "", "amount": "", "memo": ""})
        return show(request, values)
    if intent.startswith("remove:"):
        try:
            index = int(intent.removeprefix("remove:"))
        except ValueError:
            raise HTTPException(400, "Invalid row action") from None
        if count <= 2 or not 0 <= index < count:
            raise HTTPException(400, "Invalid row action")
        values["rows"].pop(index)
        return show(request, values)
    if intent != "save":
        raise HTTPException(400, "Invalid form action")

    errors = {}
    data = {
        "kind": values["kind"],
        "submission_id": values["submission_id"],
        "description": values["description"] or None,
        "splits": [],
    }
    try:
        data["account_id"] = int(values["account_id"])
    except ValueError:
        errors["account_id"] = "Bitte ein gültiges Konto auswählen."
    money = [("amount_cents", "amount", values["amount"], data)]
    for index, row in enumerate(values["rows"]):
        part = {"memo": row["memo"] or None}
        try:
            part["category_id"] = int(row["category"])
        except ValueError:
            errors[f"splits.{index}.category_id"] = "Bitte eine Kategorie auswählen."
        money.append(
            ("amount_cents", f"splits.{index}.amount_cents", row["amount"], part)
        )
        data["splits"].append(part)
    for key, field, text, target in money:
        try:
            target[key] = parse_eur(text)
        except ValueError as error:
            errors[field] = str(error)
    if errors:
        return show(request, values, errors, 422)
    if values["booked_date"]:
        data["booked_date"] = values["booked_date"]
    try:
        parsed = SplitPostingInput.model_validate(data)
        LedgerService(service(request).database).post_split(parsed)
    except ValidationError as error:
        messages = {
            "amount_cents": "Bitte einen positiven Betrag größer als null eingeben.",
            "account_id": "Bitte ein gültiges Konto auswählen.",
            "category_id": "Bitte eine gültige Kategorie auswählen.",
            "kind": "Bitte Einnahme oder Ausgabe wählen.",
            "booked_date": "Bitte ein gültiges Kalenderdatum eingeben.",
            "description": "Die Notiz darf höchstens 2000 Zeichen enthalten.",
            "memo": "Die Teilnotiz darf höchstens 2000 Zeichen enthalten.",
            "submission_id": "Ungültiges Formular. Bitte die Seite neu laden.",
        }
        for item in error.errors(include_input=False, include_url=False):
            location = item["loc"]
            key = ".".join(map(str, location)) if location else "global"
            if key == "amount_cents":
                key = "amount"
            errors[key] = messages.get(
                location[-1] if location else "",
                "Die Summe der Teilbeträge muss dem Gesamtbetrag entsprechen.",
            )
        return show(request, values, errors, 422)
    except LedgerError as error:
        return show(
            request, values, {error.field: str(error)}, 409 if error.conflict else 422
        )
    except sqlite3.Error:
        return show(
            request,
            values,
            {"global": "Speichern ist gerade nicht möglich. Bitte erneut versuchen."},
            503,
        )
    return saved(request, "transaction-created", "buchungen")
