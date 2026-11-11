"""HTTP layer: routing only. Read-only API, served behind Home Assistant Ingress."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from . import __version__
from .history import HistoryStore
from .models import BackupSummary, HealthSummary
from .service import InspectorService
from .settings import Settings, load_settings
from .sources import BackupSource, DemoBackupSource, SupervisorBackupSource

logger = logging.getLogger("asgard_backup_inspector")

BASE_DIR = Path(__file__).parent
FRONTEND_DIR = BASE_DIR / "frontend"
STATIC_DIR = BASE_DIR / "static"

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    # Self-hosted assets only; no remote CDN. 'unsafe-inline' permitted for dynamic style calculations.
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
        "connect-src 'self'; frame-ancestors 'self'; base-uri 'self'; form-action 'none'"
    ),
    "Cache-Control": "no-store",
}


def build_source(settings: Settings) -> BackupSource:
    if settings.demo_mode:
        return DemoBackupSource()
    return SupervisorBackupSource(token=settings.supervisor_token, base_url=settings.supervisor_url)


def create_app(settings: Optional[Settings] = None, source: Optional[BackupSource] = None) -> FastAPI:
    settings = settings or load_settings()
    history_store = HistoryStore(settings.data_dir)
    service = InspectorService(
        source=source or build_source(settings),
        stale_threshold_hours=settings.stale_threshold_hours,
        cache_ttl_seconds=settings.cache_ttl_seconds,
        min_refresh_interval_seconds=settings.min_refresh_interval_seconds,
        history_store=history_store,
    )
    allowed = set(settings.allowed_clients)

    app = FastAPI(
        title="ASGARD Backup Inspector",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.service = service

    @app.middleware("http")
    async def ingress_guard(request: Request, call_next):
        # Ingress traffic always arrives from the Supervisor proxy. Anything
        # else (e.g. another container on the hassio network) is refused.
        client = request.client.host if request.client else None
        if "*" not in allowed and client not in allowed:
            return JSONResponse({"detail": "Forbidden"}, status_code=403, headers=SECURITY_HEADERS)
        response: Response = await call_next(request)
        for key, value in SECURITY_HEADERS.items():
            response.headers.setdefault(key, value)
        return response

    @app.get("/api/health")
    async def health() -> dict:
        # Deliberately minimal: no backup metadata here.
        return {"status": "ok", "version": __version__}

    @app.get("/api/summary", response_model=HealthSummary)
    async def summary() -> HealthSummary:
        await service.ensure_fresh()
        return service.summary()

    @app.get("/api/backups")
    async def backups(
        offset: int = Query(0, ge=0, le=100_000),
        limit: int = Query(50, ge=1, le=1000),
    ) -> dict:
        await service.ensure_fresh()
        items: list[BackupSummary] = service.backups()
        return {
            "total": len(items),
            "offset": offset,
            "limit": limit,
            "items": [b.model_dump(mode="json") for b in items[offset : offset + limit]],
        }

    @app.get("/api/history")
    async def history() -> dict:
        await service.ensure_fresh()
        return {"entries": service.history()}

    @app.post("/api/refresh")
    async def refresh() -> JSONResponse:
        # Re-reads metadata only. It does not create a backup.
        accepted = await service.refresh()
        if not accepted:
            wait = int(service.seconds_until_refresh_allowed()) + 1
            return JSONResponse(
                {"detail": "Refresh rate limited", "retry_after_seconds": wait},
                status_code=429,
                headers={"Retry-After": str(wait)},
            )
        return JSONResponse(service.summary().model_dump(mode="json"))

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(FRONTEND_DIR / "index.html", media_type="text/html")

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        icon_path = BASE_DIR.parent / "icon.png"
        if icon_path.exists():
            return FileResponse(icon_path, media_type="image/png")
        return Response(status_code=204)

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app
