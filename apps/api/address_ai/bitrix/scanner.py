from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from address_ai.bitrix.automation import (
    AutomationResult,
    BitrixAutomationConfig,
    BitrixOpenLineAutomation,
)
from address_ai.bitrix.client import BitrixClient, BitrixError


logger = logging.getLogger("address-ai.bitrix.scanner")


@dataclass(frozen=True)
class ScanRecord:
    timestamp: str
    status: str
    reason: str
    deal_id: int | None
    chat_id: int | None
    dry_run: bool
    actions: tuple[str, ...]
    source: str


class BitrixScanner:
    def __init__(self) -> None:
        self._lock = Lock()
        self._task: asyncio.Task[None] | None = None
        self._paused = False
        self._last_error: str | None = None
        self._last_started_at: str | None = None
        self._last_finished_at: str | None = None
        self._scan_count = 0
        self._results: deque[ScanRecord] = deque(maxlen=80)
        self._current: dict[int, ScanRecord] = {}
        self._seen_until: dict[str, float] = {}

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._loop(), name="bitrix-scanner")

    async def stop(self) -> None:
        if not self._task:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    def pause(self) -> None:
        with self._lock:
            self._paused = True

    def resume(self) -> None:
        with self._lock:
            self._paused = False

    async def run_once(self, source: str = "manual") -> list[ScanRecord]:
        return await asyncio.to_thread(self._run_once_sync, source)

    def snapshot(self) -> dict[str, Any]:
        config = BitrixAutomationConfig.from_env()
        with self._lock:
            task_running = bool(self._task and not self._task.done())
            return {
                "enabled": config.scan_enabled,
                "task_running": task_running,
                "paused": self._paused,
                "interval_seconds": config.scan_interval_seconds,
                "limit": config.scan_limit,
                "scan_count": self._scan_count,
                "last_error": self._last_error,
                "last_started_at": self._last_started_at,
                "last_finished_at": self._last_finished_at,
                "current_candidates": [asdict(record) for record in self._current.values()],
                "recent": [asdict(record) for record in list(self._results)],
            }

    async def _loop(self) -> None:
        while True:
            config = BitrixAutomationConfig.from_env()
            if config.scan_enabled and not self._paused:
                await self.run_once(source="auto")
            await asyncio.sleep(max(config.scan_interval_seconds, 1.0))

    def _run_once_sync(self, source: str) -> list[ScanRecord]:
        config = BitrixAutomationConfig.from_env()
        records: list[ScanRecord] = []
        started_at = now_iso()

        with self._lock:
            self._last_started_at = started_at
            self._scan_count += 1
            self._last_error = None

        if not config.webhook_base_url:
            return self._finish_with_error("BITRIX_WEBHOOK_BASE_URL is not configured", records)
        if not config.assignment_stage_id:
            return self._finish_with_error("BITRIX_ASSIGNMENT_STAGE_ID is not configured", records)

        automation = BitrixOpenLineAutomation(BitrixClient(config.webhook_base_url), config)
        try:
            for result in automation.scan_assignment(config.scan_limit):
                self._update_current(result)
                if self._should_record(result):
                    record = to_record(result, source)
                    self._append(record)
                    records.append(record)
        except BitrixError as error:
            return self._finish_with_error(str(error), records)
        except Exception as error:  # defensive guard for the background task
            logger.exception("bitrix.scan.unexpected_error")
            return self._finish_with_error(str(error), records)

        with self._lock:
            self._last_finished_at = now_iso()
        return records

    def _update_current(self, result: AutomationResult) -> None:
        if result.deal_id is None:
            return

        with self._lock:
            if result.status in {"candidate", "claimed"}:
                self._current[result.deal_id] = to_record(result, "current")
            else:
                self._current.pop(result.deal_id, None)

            now = time.monotonic()
            max_age = 45.0
            self._current = {
                deal_id: record
                for deal_id, record in self._current.items()
                if parse_record_age_seconds(record.timestamp, now) <= max_age
            }

    def _finish_with_error(self, error: str, records: list[ScanRecord]) -> list[ScanRecord]:
        record = ScanRecord(
            timestamp=now_iso(),
            status="error",
            reason=error,
            deal_id=None,
            chat_id=None,
            dry_run=True,
            actions=(),
            source="scanner",
        )
        with self._lock:
            self._last_error = error
            self._last_finished_at = record.timestamp
            self._results.appendleft(record)
        records.append(record)
        return records

    def _append(self, record: ScanRecord) -> None:
        with self._lock:
            self._results.appendleft(record)

    def _should_record(self, result: AutomationResult) -> bool:
        key = f"{result.status}:{result.deal_id}:{result.chat_id}:{result.reason}"
        ttl = 8.0 if result.status in {"candidate", "claimed"} else 45.0
        now = time.monotonic()

        with self._lock:
            self._seen_until = {
                item_key: expires_at
                for item_key, expires_at in self._seen_until.items()
                if expires_at > now
            }
            if key in self._seen_until:
                return False
            self._seen_until[key] = now + ttl
            return True


def to_record(result: AutomationResult, source: str) -> ScanRecord:
    return ScanRecord(
        timestamp=now_iso(),
        status=result.status,
        reason=result.reason,
        deal_id=result.deal_id,
        chat_id=result.chat_id,
        dry_run=result.dry_run,
        actions=result.actions,
        source=source,
    )


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_record_age_seconds(timestamp: str, now_monotonic: float) -> float:
    try:
        created = datetime.fromisoformat(timestamp)
    except ValueError:
        return 0
    age = datetime.now(timezone.utc) - created
    return max(age.total_seconds(), 0.0)


scanner = BitrixScanner()
