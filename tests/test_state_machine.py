import pytest
from nekonet_autoupdate.coordinator.state_machine import transition
from nekonet_autoupdate.models.state import RunPhase

def test_valid_transition():
    assert transition(RunPhase.IDLE,RunPhase.LEADER_ELECTION)==RunPhase.LEADER_ELECTION

def test_invalid_transition():
    with pytest.raises(ValueError):
        transition(RunPhase.IDLE,RunPhase.COMPLETE)
