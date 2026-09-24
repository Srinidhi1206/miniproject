"""SENTINEL API entry point.

    cd backend && uvicorn app.main:app --reload
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api import analyze, community, health, history
from app.core.config import BACKEND_DIR, get_settings
from app.core.errors import register_error_handlers

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
