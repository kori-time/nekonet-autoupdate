from __future__ import annotations
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from pydantic import BaseModel, Field

def utcnow() -> datetime: return datetime.now(timezone.utc)

class RunPhase(StrEnum):
    IDLE='idle'; LEADER_ELECTION='leader-election'; NETWORK_PREFLIGHT='network-preflight'; STORAGE_SELECTION='storage-selection'; REGULAR_UPDATES='regular-updates'; REGULAR_REBOOTS='regular-reboots'; SERVER_B='server-b'; SERVER_A='server-a'; COMPLETE='complete'; FAILED='failed'
class ServerState(StrEnum):
    PENDING='pending'; CHECKING='checking'; CURRENT='current'; UPDATING='updating'; UPDATED='updated'; REBOOT_REQUIRED='reboot-required'; REBOOTING='rebooting'; ONLINE='online'; FAILED='failed'; SKIPPED='skipped'
class ServerStatus(BaseModel):
    id:str=''; name:str; ip:str; role:str=''; state:ServerState=ServerState.PENDING; packages_updated:int=0; kernel_updated:bool=False; reboot_required:bool=False; health_ok:bool|None=None; message:str|None=None; updated_at:datetime=Field(default_factory=utcnow)
class FailureInfo(BaseModel):
    server:str|None=None; stage:str; reason:str; details:dict[str,Any]=Field(default_factory=dict)
class RunState(BaseModel):
    run_id:str; generation:int=0; checksum:str=''; previous_checksum:str=''; status:str='idle'; phase:RunPhase=RunPhase.IDLE; active_coordinator:str|None=None; coordinator_role:str|None=None; started_at:datetime=Field(default_factory=utcnow); updated_at:datetime=Field(default_factory=utcnow); heartbeat_at:datetime=Field(default_factory=utcnow); storage_provider:str|None=None; degraded_storage:bool=False; message:str=''; failure:FailureInfo|None=None; servers:list[ServerStatus]=Field(default_factory=list)
