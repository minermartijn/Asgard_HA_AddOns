"""FastAPI Application for ASGARD NotifyHub with Home Assistant Ingress support."""

from __future__ import annotations

import ipaddress
import logging
import re
import uuid
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.models import (
    Priority,
    QuietPolicy,
    Recipient,
    RecipientGroup,
    Route,
    SendRequest,
    TargetType,
    summarize_records,
)
from app.settings import Settings, load_settings
from app.storage import Storage
from app.client import (
    DemoHomeAssistantClient,
    RestHomeAssistantClient,
    is_allowed_action,
    unsupported_action_reason,
)
from app.service import NotifyHubService

logger = logging.getLogger("asgard_notifyhub")

_HHMM_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def validate_timezone(tz: str) -> str:
    """Return a valid IANA timezone name or raise HTTP 400."""
    cleaned = (tz or "").strip()
    if not cleaned:
        raise HTTPException(status_code=400, detail="Timezone cannot be empty")
    try:
        ZoneInfo(cleaned)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown timezone '{cleaned}'. Use an IANA name such as Europe/Amsterdam or UTC.",
        )
    return cleaned


APP_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = APP_DIR / "frontend"
STATIC_DIR = APP_DIR / "static"


def create_app(
    settings: Optional[Settings] = None,
    service: Optional[NotifyHubService] = None,
) -> FastAPI:
    cfg = settings or load_settings()

    if service is None:
        storage = Storage(cfg.db_path)
        if cfg.demo_mode:
            client = DemoHomeAssistantClient()
        else:
            client = RestHomeAssistantClient(core_api_url=cfg.core_api_url, token=cfg.supervisor_token)
        svc = NotifyHubService(storage=storage, ha_client=client, demo_mode=cfg.demo_mode)
    else:
        svc = service

    allowed_networks = []
    allow_all = False
    for item in (cfg.allowed_source_ips or "").split(","):
        cleaned = item.strip()
        if cleaned == "*":
            allow_all = True
            break
        if cleaned:
            try:
                allowed_networks.append(ipaddress.ip_network(cleaned, strict=False))
            except ValueError:
                pass

    app = FastAPI(
        title="ASGARD NotifyHub",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.service = svc
    app.state.settings = cfg

    # ---- Security & Ingress Middleware ----
    @app.middleware("http")
    async def security_and_ingress_guard(request: Request, call_next):
        if not allow_all:
            client_host = request.client.host if request.client else None
            if not client_host:
                logger.warning("Rejected request: missing client IP")
                return JSONResponse(status_code=403, content={"detail": "Forbidden: missing client IP"})
            try:
                c_ip = ipaddress.ip_address(client_host)
                if not any(c_ip in net for net in allowed_networks):
                    logger.warning("Rejected request from untrusted IP %s for path %s", client_host, request.url.path)
                    return JSONResponse(status_code=403, content={"detail": "Forbidden: untrusted source IP"})
            except ValueError:
                logger.warning("Rejected request with invalid client IP: %s", client_host)
                return JSONResponse(status_code=403, content={"detail": "Forbidden: invalid source IP"})

        # Extract Ingress path for redirect rewriting
        ingress_path = request.headers.get("x-ingress-path", "")

        response: Response = await call_next(request)

        # Fix any redirect Location headers to retain Ingress path prefix
        if ingress_path and response.status_code in (301, 302, 307, 308):
            loc = response.headers.get("location", "")
            if loc.startswith("/") and not loc.startswith(ingress_path):
                response.headers["location"] = f"{ingress_path.rstrip('/')}{loc}"

        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # ---- Routes ----

    @app.get("/")
    @app.get("/index.html")
    async def index(request: Request):
        index_file = FRONTEND_DIR / "index.html"
        if not index_file.exists():
            return JSONResponse({"status": "NotifyHub running", "version": __version__})

        ingress_path = request.headers.get("x-ingress-path", "")
        content = index_file.read_text(encoding="utf-8")
        if ingress_path:
            base_url = ingress_path.rstrip("/") + "/"
            content = content.replace("<!-- INGRESS_BASE -->", f'<base href="{base_url}">')
            content = content.replace("window.__INGRESS_BASE__ = null;", f'window.__INGRESS_BASE__ = "{base_url}";')
        else:
            content = content.replace("<!-- INGRESS_BASE -->", '<base href="./">')
        return Response(content=content, media_type="text/html")

    @app.get("/favicon.ico")
    async def favicon():
        fav = STATIC_DIR / "favicon.ico"
        if fav.exists():
            return FileResponse(fav)
        return Response(status_code=204)

    @app.get("/api/health")
    @app.get("/api/health/")
    async def health():
        return {
            "status": "ok",
            "version": __version__,
            "demo_mode": svc.demo_mode,
            "default_timezone": cfg.default_timezone,
        }

    @app.get("/api/summary")
    @app.get("/api/summary/")
    async def summary():
        data = (await svc.get_summary()).model_dump(mode="json")
        data["default_timezone"] = cfg.default_timezone
        return data

    @app.get("/api/services")
    @app.get("/api/services/")
    async def list_services(refresh: bool = False):
        services = await svc.get_services(force_refresh=refresh)
        return {"services": services}

    # Recipients
    @app.get("/api/recipients")
    @app.get("/api/recipients/")
    async def get_recipients():
        recipients = svc.storage.list_recipients()
        return {"recipients": recipients}

    @app.post("/api/recipients")
    @app.post("/api/recipients/")
    async def save_recipient(payload: dict):
        rid = str(payload.get("id") or f"rec_{uuid.uuid4().hex[:8]}")
        name = str(payload.get("name", "")).strip()
        if not name:
            raise HTTPException(status_code=400, detail="Recipient name cannot be empty")
        tz = validate_timezone(str(payload.get("timezone") or cfg.default_timezone))
        enabled = bool(payload.get("enabled", True))
        rec = Recipient(id=rid, name=name, timezone=tz, enabled=enabled)
        svc.storage.save_recipient(rec)
        return {"status": "saved", "recipient": rec}

    @app.delete("/api/recipients/{recipient_id}")
    async def delete_recipient(recipient_id: str):
        ok = svc.storage.delete_recipient(recipient_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Recipient not found")
        return {"status": "deleted"}

    # Routes
    @app.post("/api/routes")
    @app.post("/api/routes/")
    async def save_route(payload: dict):
        rt_id = str(payload.get("id") or f"rt_{uuid.uuid4().hex[:8]}")
        rec_id = str(payload.get("recipient_id", "")).strip()
        if not rec_id or not svc.storage.get_recipient(rec_id):
            raise HTTPException(status_code=400, detail="Valid recipient_id required")
        name = str(payload.get("name", "")).strip()
        ha_service = str(payload.get("ha_service", "")).strip()
        if not name or not ha_service:
            raise HTTPException(status_code=400, detail="Route name and ha_service cannot be empty")

        domain = str(payload.get("ha_domain", "notify")).strip().lower()
        ha_service = ha_service.lower()
        if domain == "notify" and ha_service.startswith("notify."):
            ha_service = ha_service.split(".", 1)[1]
        if not is_allowed_action(domain, ha_service):
            raise HTTPException(status_code=400, detail=unsupported_action_reason(domain, ha_service))
        try:
            priority_min = Priority(str(payload.get("priority_min", "informational")))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid priority_min")
        route = Route(
            id=rt_id,
            recipient_id=rec_id,
            name=name,
            ha_domain=domain,
            ha_service=ha_service,
            target_data=payload.get("target_data"),
            priority_min=priority_min,
            enabled=bool(payload.get("enabled", True)),
        )
        svc.storage.save_route(route)
        return {"status": "saved", "route": route}

    @app.delete("/api/routes/{route_id}")
    async def delete_route(route_id: str):
        ok = svc.storage.delete_route(route_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Route not found")
        return {"status": "deleted"}

    # Groups
    @app.get("/api/groups")
    @app.get("/api/groups/")
    async def get_groups():
        groups = svc.storage.list_groups()
        return {"groups": groups}

    @app.post("/api/groups")
    @app.post("/api/groups/")
    async def save_group(payload: dict):
        gid = str(payload.get("id") or f"grp_{uuid.uuid4().hex[:8]}")
        name = str(payload.get("name", "")).strip()
        if not name:
            raise HTTPException(status_code=400, detail="Group name cannot be empty")
        desc = payload.get("description")
        rec_ids = [str(r).strip() for r in payload.get("recipient_ids", []) if str(r).strip()]
        grp = RecipientGroup(id=gid, name=name, description=desc, recipient_ids=rec_ids)
        svc.storage.save_group(grp)
        return {"status": "saved", "group": grp}

    @app.delete("/api/groups/{group_id}")
    async def delete_group(group_id: str):
        ok = svc.storage.delete_group(group_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Group not found")
        return {"status": "deleted"}

    # Policies
    @app.get("/api/policies")
    @app.get("/api/policies/")
    async def get_policies(target_id: Optional[str] = None):
        policies = svc.storage.list_policies(target_id=target_id)
        out = []
        for pol in policies:
            item = pol.model_dump(mode="json")
            item["orphaned"] = _policy_target_missing(pol.target_type, pol.target_id)
            out.append(item)
        return {"policies": out}

    def _policy_target_missing(target_type, target_id: str) -> bool:
        ttype = target_type.value if isinstance(target_type, TargetType) else str(target_type)
        if ttype == TargetType.RECIPIENT.value:
            return svc.storage.get_recipient(target_id) is None
        if ttype == TargetType.GROUP.value:
            return svc.storage.get_group(target_id) is None
        return False

    @app.post("/api/policies")
    @app.post("/api/policies/")
    async def save_policy(payload: dict):
        pid = str(payload.get("id") or f"pol_{uuid.uuid4().hex[:8]}")
        tid = str(payload.get("target_id", "")).strip()
        if not tid:
            raise HTTPException(status_code=400, detail="target_id cannot be empty")
        try:
            ttype = TargetType(str(payload.get("target_type", "recipient")))
        except ValueError:
            raise HTTPException(status_code=400, detail="target_type must be recipient, group or global")
        if _policy_target_missing(ttype, tid):
            kind = "Recipient" if ttype == TargetType.RECIPIENT else "Group"
            raise HTTPException(status_code=400, detail=f"{kind} '{tid}' does not exist. Choose an existing target.")
        q_start = str(payload.get("quiet_start", "22:00")).strip()
        q_end = str(payload.get("quiet_end", "07:00")).strip()
        if not _HHMM_RE.match(q_start) or not _HHMM_RE.match(q_end):
            raise HTTPException(status_code=400, detail="quiet_start and quiet_end must use HH:MM (24h)")
        raw_mask = payload.get("day_mask", [0, 1, 2, 3, 4, 5, 6])
        try:
            day_mask = sorted({int(d) for d in raw_mask})
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="day_mask must be a list of weekday numbers 0-6")
        if not day_mask or any(d < 0 or d > 6 for d in day_mask):
            raise HTTPException(status_code=400, detail="Select at least one active day (0=Mon … 6=Sun)")
        tz = validate_timezone(str(payload.get("timezone") or cfg.default_timezone))
        urg_override = bool(payload.get("urgent_override", False))
        enabled = bool(payload.get("enabled", True))

        policy = QuietPolicy(
            id=pid,
            target_id=tid,
            target_type=ttype,
            quiet_start=q_start,
            quiet_end=q_end,
            day_mask=day_mask,
            timezone=tz,
            urgent_override=urg_override,
            enabled=enabled,
        )
        svc.storage.save_policy(policy)
        return {"status": "saved", "policy": policy}

    @app.delete("/api/policies/{policy_id}")
    async def delete_policy(policy_id: str):
        ok = svc.storage.delete_policy(policy_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Policy not found")
        return {"status": "deleted"}

    # Dispatch & Simulation
    @app.post("/api/send/preview")
    async def preview_send(req: SendRequest):
        res = svc.engine.preview(req, dedup_window_seconds=cfg.dedup_window_seconds)
        return res

    @app.post("/api/send")
    async def execute_send(req: SendRequest):
        if not req.message.strip():
            raise HTTPException(status_code=400, detail="Message body cannot be empty")
        records = await svc.engine.execute(req, dedup_window_seconds=cfg.dedup_window_seconds)
        return {"records": records, "summary": summarize_records(records)}

    @app.post("/api/routes/{route_id}/test")
    async def test_route(route_id: str):
        # Find recipient with route
        recipients = svc.storage.list_recipients()
        found_route: Optional[Route] = None
        for r in recipients:
            for rt in r.routes:
                if rt.id == route_id:
                    found_route = rt
                    break
            if found_route:
                break

        if not found_route:
            raise HTTPException(status_code=404, detail="Route not found")
        if not is_allowed_action(found_route.ha_domain, found_route.ha_service):
            return {
                "success": False,
                "route_id": route_id,
                "ha_service": f"{found_route.ha_domain}.{found_route.ha_service}",
                "error": unsupported_action_reason(found_route.ha_domain, found_route.ha_service),
            }

        success, err = await svc.ha_client.send_notification(
            domain=found_route.ha_domain,
            service=found_route.ha_service,
            title="ASGARD NotifyHub Route Test",
            message=f"Test ping verifying route '{found_route.name}'.",
            data=found_route.target_data,
        )
        return {
            "success": success,
            "route_id": route_id,
            "ha_service": f"{found_route.ha_domain}.{found_route.ha_service}",
            "error": err,
        }

    # History & Purge
    @app.get("/api/history")
    @app.get("/api/history/")
    async def list_history(limit: int = 100):
        records = svc.storage.list_history(limit=limit)
        return {"history": records}

    @app.post("/api/history/purge")
    async def purge_history(days: int = 30):
        purged = svc.storage.purge_history(older_than_days=days)
        return {"status": "purged", "count": purged}

    return app


app = create_app()
