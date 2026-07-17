from __future__ import annotations
import asyncio
import json
from pathlib import Path
from nekonet_autoupdate.models.state import RunState

class HistoryStore:
    def __init__(self, path: str):
        self.path = Path(path)

    async def save(self, state: RunState) -> None:
        self.path.mkdir(parents=True, exist_ok=True)
        target = self.path / f"{state.run_id}.json"
        temp = target.with_suffix(".tmp")
        await asyncio.to_thread(temp.write_text, state.model_dump_json(indent=2))
        await asyncio.to_thread(temp.replace, target)

    async def list(self) -> list[dict]:
        if not self.path.exists():
            return []
        rows = []
        for path in sorted(self.path.glob("*.json"), reverse=True):
            try:
                data = json.loads(await asyncio.to_thread(path.read_text))
                rows.append({
                    key: data.get(key)
                    for key in (
                        "run_id", "status", "phase", "active_coordinator",
                        "started_at", "completed_at", "message"
                    )
                })
            except Exception:
                continue
        return rows

    async def get(self, run_id: str) -> RunState | None:
        path = self.path / f"{run_id}.json"
        if not path.exists():
            return None
        return RunState.model_validate_json(await asyncio.to_thread(path.read_text))
