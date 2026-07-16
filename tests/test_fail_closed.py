from nekonet_autoupdate.models.state import RunPhase
from nekonet_autoupdate.coordinator.state_machine import transition
import pytest

def test_failed_state_is_terminal():
    with pytest.raises(ValueError):
        transition(RunPhase.FAILED,RunPhase.REGULAR_UPDATES)
