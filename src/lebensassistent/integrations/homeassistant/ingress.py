"""Ingress nur vom echten Supervisor-Peer, ohne Vertrauen in Forwarded-Header."""

import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from lebensassistent.main import create_app

SUPERVISOR_PEER = "172.30.32.2"
INGRESS_PATH = re.compile(rb"/api/hassio_ingress/[A-Za-z0-9_-]{1,256}")


class IngressMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        async def reject(status: int, detail: str) -> None:
            if scope["type"] == "websocket":
                await send({"type": "websocket.close", "code": 1008})
            else:
                await JSONResponse({"detail": detail}, status_code=status)(
                    scope, receive, send
                )

        peer = scope.get("client")
        if not peer or peer[0] != SUPERVISOR_PEER:
            await reject(403, "Forbidden")
            return

        prefixes = [
            value for key, value in scope["headers"] if key.lower() == b"x-ingress-path"
        ]
        if len(prefixes) != 1 or not INGRESS_PATH.fullmatch(prefixes[0]):
            await reject(400, "Invalid ingress path")
            return

        prefix_bytes = prefixes[0]
        prefix = prefix_bytes.decode("ascii")
        path = scope["path"]
        raw_path = scope.get("raw_path", path.encode("utf-8"))
        if path == prefix or path.startswith(f"{prefix}/"):
            path = path[len(prefix) :] or "/"
            raw_path = raw_path[len(prefix_bytes) :] or b"/"
        adapted = dict(scope)
        adapted["lebensassistent.ingress_verified"] = True
        adapted["root_path"] = prefix
        adapted["path"] = prefix + path
        adapted["raw_path"] = prefix_bytes + raw_path

        async def relative_redirect(message: Message) -> None:
            if (
                message["type"] == "http.response.start"
                and 300 <= message["status"] < 400
            ):
                message = dict(message)
                headers = []
                for key, value in message.get("headers", []):
                    if key.lower() == b"location":
                        target = urlsplit(value.decode("latin-1"))
                        value = urlunsplit(
                            ("", "", target.path, target.query, target.fragment)
                        ).encode("latin-1")
                    headers.append((key, value))
                message["headers"] = headers
            await send(message)

        await self.app(adapted, receive, relative_redirect)


def create_addon_app(*, database_path: Path | None = None) -> IngressMiddleware:
    """Sicherer App-Einstiegspunkt; lokale Entwicklung bleibt separat."""
    return IngressMiddleware(create_app(database_path=database_path))
