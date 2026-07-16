from __future__ import annotations
from abc import ABC, abstractmethod
from nekonet_autoupdate.models.state import RunState

class StorageProvider(ABC):
    name: str
    @abstractmethod
    async def health(self) -> tuple[bool, str | None]: ...
    @abstractmethod
    async def load(self) -> RunState | None: ...
    @abstractmethod
    async def commit(self, state: RunState) -> None: ...
