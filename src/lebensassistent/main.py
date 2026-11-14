"""ASGI-Einstiegspunkt mit optionalem, explizitem Datenbankpfad."""

import os
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from lebensassistent.api.catalog import router as catalog_router
from lebensassistent.api.health import router as health_router
from lebensassistent.api.ledger import router as ledger_router
from lebensassistent.api.ui import install_ui
from lebensassistent.database import DATABASE_FILENAME
from lebensassistent.database.connection import Database
from lebensassistent.database.migrations import migrate


def create_app(*, database_path: Path | None = None) -> FastAPI:
    """Initialisiert eine konfigurierte Datenbank vor Annahme von HTTP-Anfragen."""

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        if database_path is not None:
            database = Database(database_path)
            migrate(database)
            application.state.database = database
        yield

    application = FastAPI(
        title="Lebensassistent",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    application.include_router(health_router)
    application.include_router(catalog_router)
    application.include_router(ledger_router)
    application.state.csrf_token = secrets.token_urlsafe(32)
    install_ui(application)
    return application


local_data_directory = os.environ.get("LEBENSASSISTENT_DATA_DIR")
app = create_app(
    database_path=(Path(local_data_directory) / DATABASE_FILENAME)
    if local_data_directory
    else None
)
