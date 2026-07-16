from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

import httpx

from nekonet_autoupdate.models.state import RunState


class PeerSynchronizer:
    """Synchronous state replication to the peer coordinator."""

    def __init__(self, peer_url: str, token: str, timeout: float = 15.0):
        self.peer_url = peer_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def _signature(self, payload: bytes) -> str:
        return hmac.new(self.token.encode(), payload, hashlib.sha256).hexdigest()

    async def replicate(self, state: RunState) -> dict[str, Any]:
        payload = state.model_dump_json().encode()
        headers = {
            "Authorization": f"Bearer {self.token}",
            "X-NekoNet-Signature": self._signature(payload),
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.peer_url}/internal/v1/state/replicate",
                content=payload,
                headers=headers,
            )
            response.raise_for_status()
            result = response.json()
        if result.get("generation") != state.generation or result.get("checksum") != state.checksum:
            raise RuntimeError("peer acknowledgement mismatch")
        return result
