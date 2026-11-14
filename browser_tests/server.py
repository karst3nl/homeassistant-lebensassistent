"""Lokaler Browser-Testserver mit synthetischem Präfix, ohne Home Assistant."""

import os
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path

from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from lebensassistent.integrations.homeassistant.ingress import create_addon_app
from lebensassistent.main import create_app

INGRESS_PREFIX = "/api/hassio_ingress/synthetic-browser-session"


class SimulatedHomeAssistantProxy:
    """Nur Testadapter: Supervisor-Peer und HA-Antwortpolicy simulieren."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        adapted = {
            **scope,
            "client": ("172.30.32.2", 12345),
            "headers": [
                (key, value)
                for key, value in scope["headers"]
                if key.lower() != b"x-ingress-path"
            ]
            + [(b"x-ingress-path", INGRESS_PREFIX.encode("ascii"))],
        }

        async def response_policy(message: Message) -> None:
            if message["type"] == "http.response.start":
                message = {
                    **message,
                    "headers": [
                        (key, value)
                        for key, value in message["headers"]
                        if key.lower() != b"referrer-policy"
                    ]
                    + [(b"referrer-policy", b"no-referrer")],
                }
            await send(message)

        await self.app(adapted, receive, response_policy)


directory_value = os.environ.get("LEBENSASSISTENT_BROWSER_DATA_DIR")
directory = Path(directory_value) if directory_value else None
prefixed = create_app(
    database_path=directory / "prefixed.sqlite3" if directory else None
)
root = create_app(database_path=directory / "root.sqlite3" if directory else None)
ingress = create_addon_app(
    database_path=directory / "ingress.sqlite3" if directory else None
)


@asynccontextmanager
async def lifespan(app: Starlette):
    async with AsyncExitStack() as stack:
        await stack.enter_async_context(prefixed.router.lifespan_context(prefixed))
        await stack.enter_async_context(root.router.lifespan_context(root))
        await stack.enter_async_context(
            ingress.app.router.lifespan_context(ingress.app)
        )
        yield


app = Starlette(
    routes=[
        Mount(INGRESS_PREFIX, app=SimulatedHomeAssistantProxy(ingress)),
        Mount("/synthetic-ingress", app=prefixed),
        Mount("/", app=root),
    ],
    lifespan=lifespan,
)
