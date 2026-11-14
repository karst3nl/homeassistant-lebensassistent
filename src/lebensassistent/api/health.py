"""Zustandsloser Lebenszeichen-Endpunkt ohne externe Abhängigkeiten."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    """Bestätigt, dass der lokale Webserver Anfragen beantwortet."""
    return {"status": "ok"}
