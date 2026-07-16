from __future__ import annotations
import asyncio, json, os
from pathlib import Path
from nekonet_autoupdate.models.state import RunState
from .base import StorageProvider

class JsonStorage(StorageProvider):
    name = "json"
    def __init__(self, path: str):
        self.path = Path(path)
    async def health(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            probe = self.path.parent / ".write-probe"
            await asyncio.to_thread(probe.write_text, "ok")
            await asyncio.to_thread(probe.unlink)
            return True, None
        except Exception as exc:
            return False, str(exc)
    async def load(self):
        if not self.path.exists():
            return None
        data = await asyncio.to_thread(self.path.read_text)
        return RunState.model_validate_json(data)
    async def commit(self, state):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        payload = state.model_dump_json(indent=2)
        await asyncio.to_thread(tmp.write_text, payload)
        os.chmod(tmp, 0o600)
        await asyncio.to_thread(os.replace, tmp, self.path)
