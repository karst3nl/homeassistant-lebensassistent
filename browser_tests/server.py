"""Lokaler Browser-Testserver mit synthetischem Präfix, ohne Home Assistant."""

import os
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path

from starlette.applications import Starlette
from starlette.routing import Mount

from lebensassistent.main import create_app

directory_value = os.environ.get("LEBENSASSISTENT_BROWSER_DATA_DIR")
directory = Path(directory_value) if directory_value else None
prefixed = create_app(
    database_path=directory / "prefixed.sqlite3" if directory else None
)
root = create_app(database_path=directory / "root.sqlite3" if directory else None)


@asynccontextmanager
async def lifespan(app: Starlette):
    async with AsyncExitStack() as stack:
        await stack.enter_async_context(prefixed.router.lifespan_context(prefixed))
        await stack.enter_async_context(root.router.lifespan_context(root))
        yield


app = Starlette(
    routes=[
        Mount("/synthetic-ingress", app=prefixed),
        Mount("/", app=root),
    ],
    lifespan=lifespan,
)
