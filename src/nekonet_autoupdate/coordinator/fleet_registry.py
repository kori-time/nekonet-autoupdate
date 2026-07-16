from __future__ import annotations
import json
from pathlib import Path
from typing import Iterable
from nekonet_autoupdate.models.fleet import FleetServer

class FleetRegistry:
    def __init__(self, path: str):
        self.path = Path(path)

    def _read(self) -> list[FleetServer]:
        if not self.path.exists():
            return []
        data = json.loads(self.path.read_text())
        return [FleetServer.model_validate(item) for item in data.get("servers", [])]

    def _write(self, servers: Iterable[FleetServer]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        payload = {"servers": [s.model_dump() for s in servers]}
        tmp.write_text(json.dumps(payload, indent=2))
        tmp.replace(self.path)

    def list(self, include_disabled: bool = True) -> list[FleetServer]:
        servers = self._read()
        return servers if include_disabled else [s for s in servers if s.enabled]

    def get(self, server_id: str) -> FleetServer | None:
        return next((s for s in self._read() if s.id == server_id), None)

    def upsert(self, server: FleetServer) -> FleetServer:
        servers = self._read()
        for index, existing in enumerate(servers):
            if existing.id == server.id:
                servers[index] = server
                self._write(servers)
                return server
        servers.append(server)
        self._write(servers)
        return server

    def remove(self, server_id: str) -> bool:
        servers = self._read()
        filtered = [s for s in servers if s.id != server_id]
        if len(filtered) == len(servers):
            return False
        self._write(filtered)
        return True
