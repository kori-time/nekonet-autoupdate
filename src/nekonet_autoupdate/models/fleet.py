from __future__ import annotations
from pydantic import BaseModel, Field

class HealthCheck(BaseModel):
    kind: str = "systemd"
    target: str
    required: bool = True
    timeout_seconds: int = 15

class UpdatePolicy(BaseModel):
    mode: str = "all"
    exclude_packages: list[str] = Field(default_factory=list)
    max_packages: int | None = None

class FleetServer(BaseModel):
    id: str
    name: str
    ip: str
    role: str = ""
    enabled: bool = True
    is_coordinator: bool = False
    coordinator_role: str | None = None
    canary: bool = False
    order: int = 100
    services: list[str] = Field(default_factory=list)
    health_checks: list[HealthCheck] = Field(default_factory=list)
    update_policy: UpdatePolicy = Field(default_factory=UpdatePolicy)
    metadata: dict[str, str] = Field(default_factory=dict)
