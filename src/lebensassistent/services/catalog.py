"""Konten/Kategorien anlegen und archivieren, ohne Buchungsfunktionen."""

from datetime import UTC, date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from lebensassistent.database.audit import append_audit
from lebensassistent.database.connection import Database, transaction
from lebensassistent.repositories import catalog as repository
from lebensassistent.services.values import MAX_CENTS, MIN_CENTS, parse_date

Name = Annotated[str, StringConstraints(min_length=1, max_length=100)]


class AccountInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)
    name: Name
    account_type: Literal["checking", "savings", "cash", "credit_card"]
    opening_balance_cents: Annotated[int, Field(ge=MIN_CENTS, le=MAX_CENTS)]
    opening_date: date
    notes: Annotated[str, StringConstraints(max_length=2000)] | None = None

    @field_validator("opening_date", mode="before")
    @classmethod
    def calendar_date(cls, value: object) -> date:
        if type(value) is date:
            return value
        if isinstance(value, str):
            return parse_date(value)
        raise ValueError("Ein gültiges Kalenderdatum ist erforderlich.")


class CategoryInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)
    name: Name
    kind: Literal["income", "expense"]
    parent_id: Annotated[int, Field(gt=0, le=MAX_CENTS)] | None = None


class CatalogError(ValueError):
    def __init__(self, field: str, message: str, *, not_found: bool = False) -> None:
        super().__init__(message)
        self.field = field
        self.not_found = not_found


class CatalogService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def accounts(self) -> list[dict]:
        with self.database.connect() as connection:
            return repository.records(connection, "accounts")

    def categories(self) -> list[dict]:
        with self.database.connect() as connection:
            return repository.records(connection, "categories")

    def create_account(self, values: AccountInput) -> dict:
        with self.database.connect() as connection, transaction(connection):
            data = values.model_dump()
            data["opening_date"] = values.opening_date.isoformat()
            record = repository.insert_account(
                connection, data, datetime.now(UTC).isoformat()
            )
            append_audit(
                connection,
                entity_type="accounts",
                entity_id=record["id"],
                action="create",
                after=record,
            )
            return record

    def create_category(self, values: CategoryInput) -> dict:
        with self.database.connect() as connection, transaction(connection):
            if values.parent_id is not None:
                parent = repository.record(connection, "categories", values.parent_id)
                if (
                    parent is None
                    or not parent["is_active"]
                    or parent["kind"] != values.kind
                ):
                    raise CatalogError(
                        "parent_id",
                        "Eine aktive Oberkategorie derselben Art auswählen.",
                    )
            record = repository.insert_category(
                connection, values.model_dump(), datetime.now(UTC).isoformat()
            )
            append_audit(
                connection,
                entity_type="categories",
                entity_id=record["id"],
                action="create",
                after=record,
            )
            return record

    def set_active(self, table: repository.Table, entity_id: int, active: bool) -> dict:
        if (
            type(entity_id) is not int
            or not 0 < entity_id <= MAX_CENTS
            or type(active) is not bool
        ):
            raise CatalogError("status", "Ungültige Statusänderung.")
        with self.database.connect() as connection, transaction(connection):
            before = repository.record(connection, table, entity_id)
            if before is None:
                raise CatalogError("status", "Eintrag nicht gefunden.", not_found=True)
            if bool(before["is_active"]) == active:
                return before
            if table == "categories":
                if not active and repository.has_active_children(connection, entity_id):
                    raise CatalogError(
                        "status",
                        "Bitte zuerst die aktiven Unterkategorien archivieren.",
                    )
                if active and before["parent_id"] is not None:
                    parent = repository.record(
                        connection, "categories", before["parent_id"]
                    )
                    if parent is None or not parent["is_active"]:
                        raise CatalogError(
                            "status", "Bitte zuerst die Oberkategorie aktivieren."
                        )
            after = repository.set_active(
                connection, table, entity_id, active, datetime.now(UTC).isoformat()
            )
            append_audit(
                connection,
                entity_type=table,
                entity_id=entity_id,
                action="reactivate" if active else "archive",
                before=before,
                after=after,
            )
            return after
