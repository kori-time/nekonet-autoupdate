import pytest
from nekonet_autoupdate.storage.json_store import JsonStorage
from nekonet_autoupdate.models.state import RunState

@pytest.mark.asyncio
async def test_atomic_json_round_trip(tmp_path):
    store=JsonStorage(str(tmp_path/"state.json"))
    state=RunState(run_id="test")
    await store.commit(state)
    loaded=await store.load()
    assert loaded and loaded.run_id=="test"
