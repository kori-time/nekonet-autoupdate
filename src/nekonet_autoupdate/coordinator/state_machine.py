from __future__ import annotations
from nekonet_autoupdate.models.state import RunPhase

ALLOWED = {
    RunPhase.IDLE: {RunPhase.LEADER_ELECTION},
    RunPhase.LEADER_ELECTION: {RunPhase.NETWORK_PREFLIGHT, RunPhase.FAILED},
    RunPhase.NETWORK_PREFLIGHT: {RunPhase.STORAGE_SELECTION, RunPhase.FAILED},
    RunPhase.STORAGE_SELECTION: {RunPhase.REGULAR_UPDATES, RunPhase.FAILED},
    RunPhase.REGULAR_UPDATES: {RunPhase.REGULAR_REBOOTS, RunPhase.FAILED},
    RunPhase.REGULAR_REBOOTS: {RunPhase.SERVER_B, RunPhase.FAILED},
    RunPhase.SERVER_B: {RunPhase.SERVER_A, RunPhase.FAILED},
    RunPhase.SERVER_A: {RunPhase.COMPLETE, RunPhase.FAILED},
    RunPhase.COMPLETE: set(),
    RunPhase.FAILED: set(),
}

def transition(current: RunPhase, target: RunPhase) -> RunPhase:
    if target not in ALLOWED[current]:
        raise ValueError(f"Invalid transition: {current} -> {target}")
    return target
