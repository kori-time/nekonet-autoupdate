from __future__ import annotations
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from pydantic import BaseModel, Field

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

class RunPhase(StrEnum):
    IDLE = "idle"
    LEADER_ELECTION = "leader-election"
    NETWORK_PREFLIGHT = "network-preflight"
    STORAGE_SELECTION = "storage-selection"
    CANARY_UPDATES = "canary-updates"
    REGULAR_UPDATES = "regular-updates"
    REGULAR_REBOOTS = "regular-reboots"
    SERVER_B = "server-b"
    SERVER_A = "server-a"
    COMPLETE = "complete"
    FAILED = "failed"

class ServerState(StrEnum):
    PENDING = "pending"
    CHECKING = "checking"
    CURRENT = "current"
    UPDATING = "updating"
    UPDATED = "updated"
    REBOOT_REQUIRED = "reboot-required"
    REBOOTING = "rebooting"
    ONLINE = "online"
    FAILED = "failed"
    SKIPPED = "skipped"

class PackageChange(BaseModel):
    name: str
    old_version: str | None = None
    new_version: str | None = None
    action: str = "upgrade"

class HealthResult(BaseModel):
    kind: str
    target: str
    healthy: bool
    message: str = ""

class ServerStatus(BaseModel):
    id: str = ""
    name: str
    ip: str
    role: str = ""
    state: ServerState = ServerState.PENDING
    packages_updated: int = 0
    package_changes: list[PackageChange] = Field(default_factory=list)
    kernel_updated: bool = False
    reboot_required: bool = False
    reboot_reason: str | None = None
    health_ok: bool | None = None
    health_results: list[HealthResult] = Field(default_factory=list)
    message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    updated_at: datetime = Field(default_factory=utcnow)

class FailureInfo(BaseModel):
    server: str | None = None
    stage: str
    reason: str
    details: dict[str, Any] = Field(default_factory=dict)

class NetworkStatus(BaseModel):
    packet_loss_percent: float | None = None
    average_rtt_ms: float | None = None
    clock_skew_seconds: int | None = None
    checked_at: datetime | None = None

class CertificateStatus(BaseModel):
    name: str = ""
    source_ip: str = "10.10.0.2"
    serial: str | None = None
    expires_at: str | None = None
    checksum: str | None = None
    status: str = "unknown"
    last_sync_at: datetime | None = None
    message: str = ""

class RunState(BaseModel):
    run_id: str
    generation: int = 0
    checksum: str = ""
    previous_checksum: str = ""
    status: str = "idle"
    phase: RunPhase = RunPhase.IDLE
    active_coordinator: str | None = None
    coordinator_role: str | None = None
    started_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    heartbeat_at: datetime = Field(default_factory=utcnow)
    completed_at: datetime | None = None
    storage_provider: str | None = None
    degraded_storage: bool = False
    network: NetworkStatus = Field(default_factory=NetworkStatus)
    certificate: CertificateStatus = Field(default_factory=CertificateStatus)
    message: str = ""
    failure: FailureInfo | None = None
    servers: list[ServerStatus] = Field(default_factory=list)
