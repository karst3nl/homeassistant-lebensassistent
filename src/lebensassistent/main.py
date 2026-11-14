"""ASGI-Einstiegspunkt für den lokalen FastAPI-Webserver."""

from fastapi import FastAPI

from lebensassistent.api.health import router as health_router


def create_app() -> FastAPI:
    """Erstellt eine isoliert testbare Anwendung mit dem Health-Endpunkt."""
    application = FastAPI(
        title="Lebensassistent",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    application.include_router(health_router)
    return application


app = create_app()
