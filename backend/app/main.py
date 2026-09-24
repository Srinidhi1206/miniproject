"""SENTINEL API entry point.

    cd backend && uvicorn app.main:app --reload
"""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api import analyze, community, health, history
from app.core.config import BACKEND_DIR, get_settings
from app.core.errors import file_too_large, register_error_handlers

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("sentinel")


def run_migrations() -> None:
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(cfg, "head")


@asynccontextmanager
async def lifespan(_: FastAPI):
    from app.agents.orchestrator import warm_up
    from app.db.seed import seed_all
    from app.db.session import SessionLocal

    run_migrations()
    with SessionLocal() as db:
        log.info("Seed: %s", seed_all(db))
    log.info("Components: %s", warm_up())
    yield


class BodySizeLimit:
    """Reject oversized request bodies BEFORE they are buffered.

    Without this, the multipart parser spools the whole upload (e.g. 60 MB) to
    disk before the endpoint can refuse it. Requests with a body must declare
    Content-Length (browsers always do); chunked bodies without one get 411.
    """

    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in ("POST", "PUT", "PATCH"):
            return await self.app(scope, receive, send)
        headers = dict(scope["headers"])
        declared = headers.get(b"content-length")
        if declared is None and b"chunked" in headers.get(b"transfer-encoding", b"").lower():
            return await self._reply(send, 411, {"error": {
                "code": "LENGTH_REQUIRED", "message": "The upload must declare its size."}})
        if declared is not None and declared.isdigit() and int(declared) > self.max_bytes:
            return await self._reply(send, 413, file_too_large(get_settings().max_upload_mb).to_dict())
        return await self.app(scope, receive, send)

    @staticmethod
    async def _reply(send, status: int, payload: dict):
        body = json.dumps(payload).encode()
        await send({"type": "http.response.start", "status": status,
                    "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]})
        await send({"type": "http.response.body", "body": body})


class SecurityHeaders(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="SENTINEL API",
        version="0.1.0",
        description="AI consumer scam prevention: analyze messages, links, screenshots and QR codes.",
        lifespan=lifespan,
    )
    app.add_middleware(SecurityHeaders)
    # multipart overhead allowance on top of the file limit
    app.add_middleware(BodySizeLimit, max_bytes=settings.max_upload_bytes + 256 * 1024)
    app.add_middleware(
        CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE"], allow_headers=["Content-Type", "X-Sentinel-Client"],
    )
    register_error_handlers(app)
    for router in (analyze.router, history.router, community.router, health.router):
        app.include_router(router)
    return app


app = create_app()
__all__ = ["app", "Path"]
