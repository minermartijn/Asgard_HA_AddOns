"""Historical storage and backup count measurements.

Stored in ``/data/history.json``. Safe against crashes, bounded retention,
zero secrets, zero modifications to Home Assistant backups.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("asgard_backup_inspector.history")

MAX_HISTORY_ENTRIES = 500
MIN_RECORD_INTERVAL_SECONDS = 3600  # 1 hour minimum between duplicate records unless values change


@dataclass
class HistoryEntry:
    recorded_utc: str
    total_count: int
    full_count: int
    partial_count: int
    known_size_bytes: int
    unknown_size_count: int
    freshness: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "recorded_utc": self.recorded_utc,
            "total_count": self.total_count,
            "full_count": self.full_count,
            "partial_count": self.partial_count,
            "known_size_bytes": self.known_size_bytes,
            "unknown_size_count": self.unknown_size_count,
            "freshness": self.freshness,
        }


class HistoryStore:
    def __init__(self, data_dir: str | os.PathLike = "/data"):
        self.data_dir = Path(data_dir)
        self.file_path = self.data_dir / "history.json"
        self._entries: list[HistoryEntry] = []
        self._loaded = False

    def _ensure_dir(self) -> bool:
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            test_file = self.data_dir / ".write_test"
            test_file.touch()
            test_file.unlink()
            return True
        except (OSError, PermissionError):
            fallback = Path(tempfile.gettempdir()) / "asgard_backup_inspector"
            try:
                fallback.mkdir(parents=True, exist_ok=True)
                self.data_dir = fallback
                self.file_path = self.data_dir / "history.json"
                return True
            except OSError:
                return False

    def load(self) -> list[HistoryEntry]:
        if not self.file_path.exists():
            self._entries = []
            self._loaded = True
            return self._entries
        try:
            content = self.file_path.read_text(encoding="utf-8")
            raw_list = json.loads(content)
            entries = []
            if isinstance(raw_list, list):
                for item in raw_list:
                    if isinstance(item, dict) and "recorded_utc" in item:
                        entries.append(
                            HistoryEntry(
                                recorded_utc=str(item.get("recorded_utc", "")),
                                total_count=int(item.get("total_count", 0)),
                                full_count=int(item.get("full_count", 0)),
                                partial_count=int(item.get("partial_count", 0)),
                                known_size_bytes=int(item.get("known_size_bytes", 0)),
                                unknown_size_count=int(item.get("unknown_size_count", 0)),
                                freshness=str(item.get("freshness", "unknown")),
                            )
                        )
            self._entries = entries[-MAX_HISTORY_ENTRIES:]
        except Exception as err:
            logger.warning("Could not read backup history; starting fresh: %s", err)
            self._entries = []
        self._loaded = True
        return self._entries

    def get_entries(self) -> list[HistoryEntry]:
        if not self._loaded:
            self.load()
        return list(self._entries)

    def record_snapshot(
        self,
        *,
        total_count: int,
        full_count: int,
        partial_count: int,
        known_size_bytes: int,
        unknown_size_count: int,
        freshness: str,
        now: Optional[datetime] = None,
    ) -> bool:
        if not self._loaded:
            self.load()

        dt = now or datetime.now(timezone.utc)
        iso_now = dt.isoformat()

        # Check if last entry is identical and recent
        if self._entries:
            last = self._entries[-1]
            try:
                last_dt = datetime.fromisoformat(last.recorded_utc)
                age = (dt - last_dt).total_seconds()
            except Exception:
                age = MIN_RECORD_INTERVAL_SECONDS + 1

            unchanged = (
                last.total_count == total_count
                and last.known_size_bytes == known_size_bytes
                and last.unknown_size_count == unknown_size_count
                and last.freshness == freshness
            )
            if unchanged and age < MIN_RECORD_INTERVAL_SECONDS:
                return False

        entry = HistoryEntry(
            recorded_utc=iso_now,
            total_count=total_count,
            full_count=full_count,
            partial_count=partial_count,
            known_size_bytes=known_size_bytes,
            unknown_size_count=unknown_size_count,
            freshness=freshness,
        )
        self._entries.append(entry)
        self._entries = self._entries[-MAX_HISTORY_ENTRIES:]

        return self._save()

    def _save(self) -> bool:
        if not self._ensure_dir():
            return False
        raw_list = [e.to_dict() for e in self._entries]
        try:
            # Atomic write via temporary file
            with tempfile.NamedTemporaryFile("w", dir=str(self.data_dir), delete=False, encoding="utf-8") as tf:
                json.dump(raw_list, tf, indent=2)
                temp_name = tf.name
            os.replace(temp_name, str(self.file_path))
            return True
        except OSError as err:
            logger.warning("Could not save backup history to %s: %s", self.file_path, err)
            return False
