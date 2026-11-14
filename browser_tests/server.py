"""Lokaler Browser-Testserver mit synthetischem Präfix, ohne Home Assistant."""

from starlette.applications import Starlette
from starlette.routing import Mount

from lebensassistent.main import create_app

app = Starlette(
    routes=[
        Mount("/synthetic-ingress", app=create_app()),
        Mount("/", app=create_app()),
    ]
)
