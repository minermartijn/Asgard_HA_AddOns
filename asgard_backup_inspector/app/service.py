"""Caching layer between the HTTP API and a backup source.

* One fetch at a time (asyncio lock); concurrent callers share the result.
* Manual refreshes are rate limited.
* On failure, the last successful data is kept and flagged as cached.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from .aggregator import AggregationResult, BackupAggregator
from .health import evaluate
from .history import HistoryStore
from .models import ApiStatus, BackupSummary, GoogleDriveSummary, HealthSummary
from .providers import CloudBackupProvider
from .sources import BackupSource, SourceError


@dataclass
class _Snapshot:
    backups: list[BackupSummary]
    aggregation: Optional[AggregationResult]
    google_drive: Optional[GoogleDriveSummary]
    days_until_stale: Optional[int]
    warnings: list[str]
    partial: bool
    fetched_utc: datetime
    fetched_monotonic: float


@dataclass
class InspectorService:
    source: BackupSource
    stale_threshold_hours: int
    cloud_provider: Optional[CloudBackupProvider] = None
    cache_ttl_seconds: float = 300.0
    min_refresh_interval_seconds: float = 10.0
    history_store: Optional[HistoryStore] = None
    clock: Callable[[], datetime] = field(default=lambda: datetime.now(timezone.utc))
    monotonic: Callable[[], float] = field(default=time.monotonic)

    _snapshot: Optional[_Snapshot] = field(default=None, init=False)
    _last_error: Optional[SourceError] = field(default=None, init=False)
    _last_attempt_utc: Optional[datetime] = field(default=None, init=False)
    _last_attempt_monotonic: Optional[float] = field(default=None, init=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)

    async def _fetch(self) -> None:
        self._last_attempt_utc = self.clock()
        self._last_attempt_monotonic = self.monotonic()

        try:
            local_result = await self.source.fetch()
            self._last_error = None
        except SourceError as err:
            self._last_error = err
            return

        gdrive_summary: Optional[GoogleDriveSummary] = None
        gdrive_items = []
        if self.cloud_provider is not None:
            try:
                gdrive_summary, gdrive_items = await self.cloud_provider.fetch(
                    self.stale_threshold_hours, now=self._last_attempt_utc
                )
            except Exception as e:
                gdrive_summary = GoogleDriveSummary(
                    enabled=getattr(self.cloud_provider, "enabled", True),
                    available=False,
                    error_message=f"Google Drive provider error: {e}",
                )
                gdrive_items = []

        locals_list = local_result.backups
        days_stale = local_result.days_until_stale
        warnings = list(local_result.warnings)
        is_partial = local_result.skipped > 0

        agg = BackupAggregator.aggregate(
            locals_list,
            gdrive_summary,
            gdrive_items,
            stale_threshold_hours=self.stale_threshold_hours,
            now=self._last_attempt_utc,
        )

        all_warnings = warnings + [w for w in agg.warnings if w not in warnings]

        self._snapshot = _Snapshot(
            backups=agg.backups,
            aggregation=agg,
            google_drive=gdrive_summary,
            days_until_stale=days_stale,
            warnings=all_warnings,
            partial=is_partial,
            fetched_utc=self._last_attempt_utc,
            fetched_monotonic=self._last_attempt_monotonic,
        )
        if self.history_store is not None:
            try:
                sum_val = self.summary()
                self.history_store.record_snapshot(
                    total_count=sum_val.total_count,
                    full_count=sum_val.full_backup_count,
                    partial_count=sum_val.partial_backup_count,
                    known_size_bytes=sum_val.known_size_total_bytes,
                    unknown_size_count=sum_val.unknown_size_count,
                    freshness=sum_val.freshness.value,
                    now=self._last_attempt_utc,
                )
            except Exception:
                pass

    def _cache_valid(self) -> bool:
        if self._last_attempt_monotonic is None:
            return False
        return (self.monotonic() - self._last_attempt_monotonic) < self.cache_ttl_seconds

    async def ensure_fresh(self) -> None:
        async with self._lock:
            if not self._cache_valid():
                await self._fetch()

    def seconds_until_refresh_allowed(self) -> float:
        if self._last_attempt_monotonic is None:
            return 0.0
        elapsed = self.monotonic() - self._last_attempt_monotonic
        return max(0.0, self.min_refresh_interval_seconds - elapsed)

    async def refresh(self) -> bool:
        """Force a fetch. Returns False if rate limited."""
        async with self._lock:
            if self.seconds_until_refresh_allowed() > 0:
                return False
            await self._fetch()
            return True

    def backups(self) -> list[BackupSummary]:
        if self._snapshot is None:
            return []
        epoch = datetime.min.replace(tzinfo=timezone.utc)
        return sorted(self._snapshot.backups, key=lambda b: b.created_utc or epoch, reverse=True)

    def history(self) -> list[dict[str, Any]]:
        if self.history_store is None:
            return []
        return [e.to_dict() for e in self.history_store.get_entries()]

    def summary(self) -> HealthSummary:
        snap = self._snapshot
        err = self._last_error
        if err is not None:
            api_status = err.status
        elif snap is not None and snap.partial:
            api_status = ApiStatus.PARTIAL
        else:
            api_status = ApiStatus.OK

        if snap is not None and snap.aggregation is not None:
            agg = snap.aggregation
            result = evaluate(
                snap.backups,
                now=self.clock(),
                stale_threshold_hours=self.stale_threshold_hours,
                api_status=api_status,
                supervisor_days_until_stale=snap.days_until_stale,
                extra_warnings=snap.warnings,
                local_count=agg.local_count,
                remote_count=agg.remote_count,
                both_count=agg.both_count,
                pending_count=agg.pending_count,
                local_only_count=agg.local_only_count,
                remote_only_count=agg.remote_only_count,
                cloud_freshness=agg.cloud_freshness,
                offsite_coverage=agg.offsite_coverage,
                full_backup_coverage=agg.full_backup_coverage,
                google_drive=snap.google_drive,
            )
        else:
            result = evaluate(
                snap.backups if snap else None,
                now=self.clock(),
                stale_threshold_hours=self.stale_threshold_hours,
                api_status=api_status,
                supervisor_days_until_stale=snap.days_until_stale if snap else None,
                extra_warnings=snap.warnings if snap else None,
            )
        result.last_checked_utc = self._last_attempt_utc
        result.last_success_utc = snap.fetched_utc if snap else None
        result.showing_cached_data = err is not None and snap is not None
        result.demo_mode = bool(getattr(self.source, "demo", False))
        result.error_message = err.message if err else None
        return result
