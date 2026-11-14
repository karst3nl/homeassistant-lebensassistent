"""Atomare Einnahmen/Ausgaben mit einer vollständigen Kategoriezuordnung."""

from datetime import UTC, date, datetime
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from lebensassistent.database.audit import append_audit
from lebensassistent.database.connection import Database, transaction
from lebensassistent.repositories import catalog
from lebensassistent.repositories import ledger as repository
from lebensassistent.services.values import MAX_CENTS, parse_date


def today_berlin() -> date:
    return datetime.now(ZoneInfo("Europe/Berlin")).date()


class PostingInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)
    account_id: Annotated[int, Field(gt=0, le=MAX_CENTS)]
    category_id: Annotated[int, Field(gt=0, le=MAX_CENTS)]
    kind: Literal["income", "expense"]
    amount_cents: Annotated[int, Field(gt=0, le=MAX_CENTS)]
    booked_date: date = Field(default_factory=today_berlin)
    description: Annotated[str, StringConstraints(max_length=2000)] | None = None
    submission_id: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{32}$")]

    @field_validator("booked_date", mode="before")
    @classmethod
    def calendar_date(cls, value: object) -> date:
        if type(value) is date:
            return value
        if isinstance(value, str):
            return parse_date(value)
        raise ValueError("Ein gültiges Kalenderdatum ist erforderlich.")


class LedgerError(ValueError):
    def __init__(self, field: str, message: str, *, conflict: bool = False) -> None:
        super().__init__(message)
        self.field = field
        self.conflict = conflict


class LedgerService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def post(self, values: PostingInput) -> dict:
        data = values.model_dump()
        data["booked_date"] = values.booked_date.isoformat()
        with self.database.connect() as connection, transaction(connection):
            previous = repository.submitted(connection, values.submission_id)
            if previous is not None:
                same = all(
                    previous[key] == value
                    for key, value in data.items()
                    if key != "category_id"
                ) and (
                    len(previous["splits"]) == 1
                    and previous["splits"][0]["category_id"] == values.category_id
                )
                if not same:
                    raise LedgerError(
                        "global",
                        "Diese Formularanfrage wurde bereits anders gespeichert. "
                        "Bitte die Seite neu laden.",
                        conflict=True,
                    )
                return previous
            account = catalog.record(connection, "accounts", values.account_id)
            if account is None or not account["is_active"]:
                raise LedgerError("account_id", "Bitte ein aktives Konto auswählen.")
            category = catalog.record(connection, "categories", values.category_id)
            if (
                category is None
                or not category["is_active"]
                or category["kind"] != values.kind
            ):
                raise LedgerError(
                    "category_id",
                    "Bitte eine aktive Kategorie derselben Art auswählen.",
                )
            if data["booked_date"] < account["opening_date"]:
                raise LedgerError(
                    "booked_date",
                    "Das Buchungsdatum darf nicht vor dem Kontostart liegen.",
                )
            record = repository.insert(connection, data, datetime.now(UTC).isoformat())
            append_audit(
                connection,
                entity_type="transactions",
                entity_id=record["id"],
                action="create",
                after=record,
            )
            return record

    def transactions(
        self, account_id: int | None = None, limit: int = 50
    ) -> list[dict]:
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError("Invalid list limit")
        if account_id is not None and (
            type(account_id) is not int or not 0 < account_id <= MAX_CENTS
        ):
            raise ValueError("Invalid account ID")
        with self.database.connect() as connection:
            return repository.records(connection, account_id, limit)

    def balances(self, on: date) -> dict[int, int | None]:
        if type(on) is not date:
            raise ValueError("A calendar date is required")
        with self.database.connect() as connection:
            return repository.balances(connection, on)

    def balance(self, account_id: int, on: date) -> int | None:
        balances = self.balances(on)
        if type(account_id) is not int or account_id not in balances:
            raise LedgerError("account_id", "Konto nicht gefunden.")
        return balances[account_id]
