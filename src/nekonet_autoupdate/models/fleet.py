from __future__ import annotations
from pydantic import BaseModel, Field

class FleetServer(BaseModel):
    id: str
    name: str
    ip: str
    role: str = ""
    enabled: bool = True
    is_coordinator: bool = False
    metadata: dict[str, str] = Field(default_factory=dict)
