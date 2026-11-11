"""SQLite persistence layer for ASGARD NotifyHub.

Stores recipients, routes, groups, quiet hour policies, and delivery audit history.
Runs in-process using standard library sqlite3 without external dependencies.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Union
from app.models import (
    Recipient,
    Route,
    RecipientGroup,
    QuietPolicy,
    DeliveryRecord,
    DeliveryStatus,
    Priority,
    TargetType,
)


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS recipients (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    timezone TEXT NOT NULL DEFAULT 'UTC',
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS routes (
    id TEXT PRIMARY KEY,
    recipient_id TEXT NOT NULL REFERENCES recipients(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    ha_domain TEXT NOT NULL DEFAULT 'notify',
    ha_service TEXT NOT NULL,
    target_data TEXT,
    priority_min TEXT NOT NULL DEFAULT 'informational',
    enabled INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS groups_table (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS group_memberships (
    group_id TEXT NOT NULL REFERENCES groups_table(id) ON DELETE CASCADE,
    recipient_id TEXT NOT NULL REFERENCES recipients(id) ON DELETE CASCADE,
    PRIMARY KEY (group_id, recipient_id)
);

CREATE TABLE IF NOT EXISTS policies (
    id TEXT PRIMARY KEY,
    target_id TEXT NOT NULL,
    target_type TEXT NOT NULL DEFAULT 'recipient',
    quiet_start TEXT NOT NULL DEFAULT '22:00',
    quiet_end TEXT NOT NULL DEFAULT '07:00',
    day_mask TEXT NOT NULL DEFAULT '0,1,2,3,4,5,6',
    timezone TEXT NOT NULL DEFAULT 'UTC',
    urgent_override INTEGER NOT NULL DEFAULT 0,
    enabled INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS delivery_history (
    id TEXT PRIMARY KEY,
    idempotency_key TEXT,
    created_utc TEXT NOT NULL,
    priority TEXT NOT NULL,
    title TEXT,
    recipient_id TEXT,
    recipient_name TEXT,
    route_id TEXT,
    route_name TEXT,
    ha_service TEXT NOT NULL,
    status TEXT NOT NULL,
    details TEXT,
    content_hash TEXT
);

CREATE INDEX IF NOT EXISTS idx_history_created ON delivery_history(created_utc);
CREATE INDEX IF NOT EXISTS idx_history_content_hash ON delivery_history(content_hash, created_utc);
CREATE INDEX IF NOT EXISTS idx_history_idempotency ON delivery_history(idempotency_key);
"""


class Storage:
    def __init__(self, db_path: Union[Path, str]):
        self.db_path = Path(db_path)
        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            with self._get_connection() as conn:
                conn.executescript(SCHEMA_SQL)

    # ---- Recipients & Routes ----

    def list_recipients(self) -> list[Recipient]:
        with self._lock:
            with self._get_connection() as conn:
                r_rows = conn.execute("SELECT id, name, timezone, enabled FROM recipients ORDER BY name ASC").fetchall()
                routes_by_r: dict[str, list[Route]] = {}
                route_rows = conn.execute("SELECT * FROM routes ORDER BY name ASC").fetchall()
                for rw in route_rows:
                    t_data = json.loads(rw["target_data"]) if rw["target_data"] else None
                    r_id = rw["recipient_id"]
                    if r_id not in routes_by_r:
                        routes_by_r[r_id] = []
                    routes_by_r[r_id].append(
                        Route(
                            id=rw["id"],
                            recipient_id=rw["recipient_id"],
                            name=rw["name"],
                            ha_domain=rw["ha_domain"],
                            ha_service=rw["ha_service"],
                            target_data=t_data,
                            priority_min=Priority(rw["priority_min"]),
                            enabled=bool(rw["enabled"]),
                        )
                    )

                recipients = []
                for row in r_rows:
                    recipients.append(
                        Recipient(
                            id=row["id"],
                            name=row["name"],
                            timezone=row["timezone"],
                            enabled=bool(row["enabled"]),
                            routes=routes_by_r.get(row["id"], []),
                        )
                    )
                return recipients

    def get_recipient(self, recipient_id: str) -> Optional[Recipient]:
        with self._lock:
            with self._get_connection() as conn:
                r_row = conn.execute("SELECT * FROM recipients WHERE id = ?", (recipient_id,)).fetchone()
                if not r_row:
                    return None
                route_rows = conn.execute("SELECT * FROM routes WHERE recipient_id = ? ORDER BY name ASC", (recipient_id,)).fetchall()
                routes = []
                for rw in route_rows:
                    t_data = json.loads(rw["target_data"]) if rw["target_data"] else None
                    routes.append(
                        Route(
                            id=rw["id"],
                            recipient_id=rw["recipient_id"],
                            name=rw["name"],
                            ha_domain=rw["ha_domain"],
                            ha_service=rw["ha_service"],
                            target_data=t_data,
                            priority_min=Priority(rw["priority_min"]),
                            enabled=bool(rw["enabled"]),
                        )
                    )
                return Recipient(
                    id=r_row["id"],
                    name=r_row["name"],
                    timezone=r_row["timezone"],
                    enabled=bool(r_row["enabled"]),
                    routes=routes,
                )

    def save_recipient(self, recipient: Recipient) -> None:
        with self._lock:
            with self._get_connection() as conn:
                now_str = datetime.now(timezone.utc).isoformat()
                conn.execute(
                    """
                    INSERT INTO recipients (id, name, timezone, enabled, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        name = excluded.name,
                        timezone = excluded.timezone,
                        enabled = excluded.enabled
                    """,
                    (recipient.id, recipient.name, recipient.timezone, 1 if recipient.enabled else 0, now_str),
                )
                conn.commit()

    def delete_recipient(self, recipient_id: str) -> bool:
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute("DELETE FROM recipients WHERE id = ?", (recipient_id,))
                conn.commit()
                return cur.rowcount > 0

    def save_route(self, route: Route) -> None:
        with self._lock:
            with self._get_connection() as conn:
                t_json = json.dumps(route.target_data) if route.target_data else None
                conn.execute(
                    """
                    INSERT INTO routes (id, recipient_id, name, ha_domain, ha_service, target_data, priority_min, enabled)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        name = excluded.name,
                        ha_domain = excluded.ha_domain,
                        ha_service = excluded.ha_service,
                        target_data = excluded.target_data,
                        priority_min = excluded.priority_min,
                        enabled = excluded.enabled
                    """,
                    (
                        route.id,
                        route.recipient_id,
                        route.name,
                        route.ha_domain,
                        route.ha_service,
                        t_json,
                        route.priority_min.value,
                        1 if route.enabled else 0,
                    ),
                )
                conn.commit()

    def delete_route(self, route_id: str) -> bool:
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute("DELETE FROM routes WHERE id = ?", (route_id,))
                conn.commit()
                return cur.rowcount > 0

    # ---- Groups ----

    def list_groups(self) -> list[RecipientGroup]:
        with self._lock:
            with self._get_connection() as conn:
                g_rows = conn.execute("SELECT * FROM groups_table ORDER BY name ASC").fetchall()
                mem_rows = conn.execute("SELECT group_id, recipient_id FROM group_memberships").fetchall()
                mems_by_g: dict[str, list[str]] = {}
                for m in mem_rows:
                    mems_by_g.setdefault(m["group_id"], []).append(m["recipient_id"])

                groups = []
                for gr in g_rows:
                    groups.append(
                        RecipientGroup(
                            id=gr["id"],
                            name=gr["name"],
                            description=gr["description"],
                            recipient_ids=mems_by_g.get(gr["id"], []),
                        )
                    )
                return groups

    def get_group(self, group_id: str) -> Optional[RecipientGroup]:
        with self._lock:
            with self._get_connection() as conn:
                gr = conn.execute("SELECT * FROM groups_table WHERE id = ?", (group_id,)).fetchone()
                if not gr:
                    return None
                mem_rows = conn.execute("SELECT recipient_id FROM group_memberships WHERE group_id = ?", (group_id,)).fetchall()
                return RecipientGroup(
                    id=gr["id"],
                    name=gr["name"],
                    description=gr["description"],
                    recipient_ids=[m["recipient_id"] for m in mem_rows],
                )

    def save_group(self, group: RecipientGroup) -> None:
        with self._lock:
            with self._get_connection() as conn:
                now_str = datetime.now(timezone.utc).isoformat()
                conn.execute(
                    """
                    INSERT INTO groups_table (id, name, description, created_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        name = excluded.name,
                        description = excluded.description
                    """,
                    (group.id, group.name, group.description, now_str),
                )
                # update memberships
                conn.execute("DELETE FROM group_memberships WHERE group_id = ?", (group.id,))
                for rid in group.recipient_ids:
                    # check recipient exists
                    chk = conn.execute("SELECT 1 FROM recipients WHERE id = ?", (rid,)).fetchone()
                    if chk:
                        conn.execute("INSERT OR IGNORE INTO group_memberships (group_id, recipient_id) VALUES (?, ?)", (group.id, rid))
                conn.commit()

    def delete_group(self, group_id: str) -> bool:
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute("DELETE FROM groups_table WHERE id = ?", (group_id,))
                conn.commit()
                return cur.rowcount > 0

    # ---- Policies (Quiet Hours) ----

    def list_policies(self, target_id: Optional[str] = None) -> list[QuietPolicy]:
        with self._lock:
            with self._get_connection() as conn:
                if target_id:
                    rows = conn.execute("SELECT * FROM policies WHERE target_id = ?", (target_id,)).fetchall()
                else:
                    rows = conn.execute("SELECT * FROM policies").fetchall()
                policies = []
                for r in rows:
                    dm = [int(x.strip()) for x in r["day_mask"].split(",") if x.strip().isdigit()]
                    policies.append(
                        QuietPolicy(
                            id=r["id"],
                            target_id=r["target_id"],
                            target_type=TargetType(r["target_type"]),
                            quiet_start=r["quiet_start"],
                            quiet_end=r["quiet_end"],
                            day_mask=dm or [0, 1, 2, 3, 4, 5, 6],
                            timezone=r["timezone"],
                            urgent_override=bool(r["urgent_override"]),
                            enabled=bool(r["enabled"]),
                        )
                    )
                return policies

    def save_policy(self, policy: QuietPolicy) -> None:
        with self._lock:
            with self._get_connection() as conn:
                dm_str = ",".join(str(d) for d in policy.day_mask)
                conn.execute(
                    """
                    INSERT INTO policies (id, target_id, target_type, quiet_start, quiet_end, day_mask, timezone, urgent_override, enabled)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        target_id = excluded.target_id,
                        target_type = excluded.target_type,
                        quiet_start = excluded.quiet_start,
                        quiet_end = excluded.quiet_end,
                        day_mask = excluded.day_mask,
                        timezone = excluded.timezone,
                        urgent_override = excluded.urgent_override,
                        enabled = excluded.enabled
                    """,
                    (
                        policy.id,
                        policy.target_id,
                        policy.target_type.value,
                        policy.quiet_start,
                        policy.quiet_end,
                        dm_str,
                        policy.timezone,
                        1 if policy.urgent_override else 0,
                        1 if policy.enabled else 0,
                    ),
                )
                conn.commit()

    def delete_policy(self, policy_id: str) -> bool:
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute("DELETE FROM policies WHERE id = ?", (policy_id,))
                conn.commit()
                return cur.rowcount > 0

    # ---- Delivery History & Deduplication ----

    def record_delivery(self, record: DeliveryRecord) -> None:
        with self._lock:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO delivery_history (
                        id, idempotency_key, created_utc, priority, title,
                        recipient_id, recipient_name, route_id, route_name,
                        ha_service, status, details, content_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.id,
                        record.idempotency_key,
                        record.created_utc.isoformat(),
                        record.priority.value,
                        record.title,
                        record.recipient_id,
                        record.recipient_name,
                        record.route_id,
                        record.route_name,
                        record.ha_service,
                        record.status.value,
                        record.details,
                        record.content_hash,
                    ),
                )
                conn.commit()

    def is_recent_duplicate(self, content_hash: str, window_seconds: int, now: Optional[datetime] = None) -> bool:
        if not content_hash or window_seconds <= 0:
            return False
        current = now or datetime.now(timezone.utc)
        cutoff = (current - timedelta(seconds=window_seconds)).isoformat()
        with self._lock:
            with self._get_connection() as conn:
                row = conn.execute(
                    """
                    SELECT 1 FROM delivery_history
                    WHERE content_hash = ? AND created_utc >= ? AND status = ?
                    LIMIT 1
                    """,
                    (content_hash, cutoff, DeliveryStatus.SUBMITTED.value),
                ).fetchone()
                return row is not None

    def is_idempotency_key_seen(self, idempotency_key: str) -> bool:
        if not idempotency_key:
            return False
        with self._lock:
            with self._get_connection() as conn:
                row = conn.execute(
                    "SELECT 1 FROM delivery_history WHERE idempotency_key = ? LIMIT 1",
                    (idempotency_key,),
                ).fetchone()
                return row is not None

    def list_history(self, limit: int = 100) -> list[DeliveryRecord]:
        with self._lock:
            with self._get_connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM delivery_history ORDER BY created_utc DESC LIMIT ?",
                    (max(1, min(limit, 500)),),
                ).fetchall()
                records = []
                for r in rows:
                    c_utc = datetime.fromisoformat(r["created_utc"])
                    records.append(
                        DeliveryRecord(
                            id=r["id"],
                            idempotency_key=r["idempotency_key"],
                            created_utc=c_utc,
                            priority=Priority(r["priority"]),
                            title=r["title"],
                            recipient_id=r["recipient_id"],
                            recipient_name=r["recipient_name"],
                            route_id=r["route_id"],
                            route_name=r["route_name"],
                            ha_service=r["ha_service"],
                            status=DeliveryStatus(r["status"]),
                            details=r["details"],
                            content_hash=r["content_hash"],
                        )
                    )
                return records

    def purge_history(self, older_than_days: int) -> int:
        if older_than_days < 0:
            return 0
        cutoff = (datetime.now(timezone.utc) - timedelta(days=older_than_days)).isoformat()
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute("DELETE FROM delivery_history WHERE created_utc < ?", (cutoff,))
                conn.commit()
                return cur.rowcount

    def get_stats_24h(self, now: Optional[datetime] = None) -> dict[str, int]:
        current = now or datetime.now(timezone.utc)
        cutoff = (current - timedelta(hours=24)).isoformat()
        with self._lock:
            with self._get_connection() as conn:
                submitted = conn.execute(
                    "SELECT COUNT(*) FROM delivery_history WHERE created_utc >= ? AND status = ?",
                    (cutoff, DeliveryStatus.SUBMITTED.value),
                ).fetchone()[0]
                quiet = conn.execute(
                    "SELECT COUNT(*) FROM delivery_history WHERE created_utc >= ? AND status = ?",
                    (cutoff, DeliveryStatus.BLOCKED_QUIET_HOURS.value),
                ).fetchone()[0]
                failed = conn.execute(
                    "SELECT COUNT(*) FROM delivery_history WHERE created_utc >= ? AND status = ?",
                    (cutoff, DeliveryStatus.FAILED.value),
                ).fetchone()[0]
                recipients_cnt = conn.execute("SELECT COUNT(*) FROM recipients").fetchone()[0]
                routes_cnt = conn.execute("SELECT COUNT(*) FROM routes").fetchone()[0]
                groups_cnt = conn.execute("SELECT COUNT(*) FROM groups_table").fetchone()[0]
                policies_cnt = conn.execute("SELECT COUNT(*) FROM policies").fetchone()[0]

                return {
                    "submissions_24h": submitted,
                    "blocked_quiet_hours_24h": quiet,
                    "failures_24h": failed,
                    "recipients_count": recipients_cnt,
                    "routes_count": routes_cnt,
                    "groups_count": groups_cnt,
                    "policies_count": policies_cnt,
                }
