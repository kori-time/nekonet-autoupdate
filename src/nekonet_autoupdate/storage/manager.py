from __future__ import annotations
import asyncio
import hashlib
from datetime import datetime, timezone
from nekonet_autoupdate.models.state import RunState
from .json_store import JsonStorage
from .sql import SqlStorage

class StorageManager:
    def __init__(self, settings):
        self.settings = settings
        self.providers = {}
        if settings.mysql_dsn:
            self.providers["mysql"] = SqlStorage("mysql", settings.mysql_dsn)
        if settings.postgresql_dsn:
            self.providers["postgresql"] = SqlStorage("postgresql", settings.postgresql_dsn)
        self.providers["sqlite"] = SqlStorage("sqlite", f"sqlite+aiosqlite:///{settings.sqlite_path}")
        self.providers["json"] = JsonStorage(settings.json_path)
        self.active = None
        self.latest_state: RunState | None = None
        self.health_state: dict[str, dict] = {}
        self._recovery_task: asyncio.Task | None = None

    async def select(self):
        errors = {}
        preferred = self.settings.storage_order.split(",")[0].strip()

        for name in self.settings.storage_order.split(","):
            name = name.strip()
            provider = self.providers.get(name)
            if provider is None:
                continue

            ok, error = await provider.health()
            self.health_state[name] = {"healthy": ok, "error": error}

            if ok:
                self.active = provider
                return provider.name, errors, provider.name != preferred

            errors[name] = error

        raise RuntimeError(f"No storage provider healthy: {errors}")

    @staticmethod
    def checksum(state: RunState) -> str:
        clone = state.model_copy(deep=True)
        clone.checksum = ""
        raw = clone.model_dump_json(exclude_none=False)
        return hashlib.sha256(raw.encode()).hexdigest()

    async def _write_available(self, state: RunState) -> dict[str, str]:
        failures = {}
        for name, provider in self.providers.items():
            try:
                ok, error = await provider.health()
                self.health_state[name] = {"healthy": ok, "error": error}
                if ok:
                    await provider.commit(state)
                else:
                    failures[name] = error or "unhealthy"
            except Exception as exc:
                failures[name] = str(exc)
                self.health_state[name] = {"healthy": False, "error": str(exc)}
        return failures

    async def commit(self, state: RunState):
        # Maintenance does not stop because MySQL/PostgreSQL are unavailable.
        # State is committed to every currently healthy provider.
        state.generation += 1
        state.previous_checksum = state.checksum
        state.updated_at = datetime.now(timezone.utc)
        state.checksum = self.checksum(state)
        self.latest_state = state.model_copy(deep=True)

        failures = await self._write_available(state)

        healthy = [name for name, info in self.health_state.items() if info.get("healthy")]
        if not healthy:
            raise RuntimeError("No storage provider accepted the checkpoint.")

        preferred = self.settings.storage_order.split(",")[0].strip()
        state.storage_provider = self.active.name if self.active else healthy[0]
        state.degraded_storage = preferred not in healthy

        if self._recovery_task is None or self._recovery_task.done():
            self._recovery_task = asyncio.create_task(self._recovery_loop())

        return failures

    async def _recovery_loop(self):
        # Recheck failed providers and backfill the newest state automatically.
        while self.latest_state is not None:
            pending = [
                name for name, info in self.health_state.items()
                if not info.get("healthy", False)
            ]
            if not pending:
                return

            for name in pending:
                provider = self.providers[name]
                try:
                    ok, error = await provider.health()
                    self.health_state[name] = {"healthy": ok, "error": error}
                    if ok and self.latest_state is not None:
                        await provider.commit(self.latest_state)
                except Exception as exc:
                    self.health_state[name] = {"healthy": False, "error": str(exc)}

            await asyncio.sleep(self.settings.storage_retry_seconds)
