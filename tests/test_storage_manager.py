from types import SimpleNamespace
from nekonet_autoupdate.storage.manager import StorageManager
from nekonet_autoupdate.models.state import RunState
import pytest

@pytest.mark.asyncio
async def test_sqlite_json_mirror(tmp_path):
    settings=SimpleNamespace(
        mysql_dsn="",postgresql_dsn="",
        sqlite_path=str(tmp_path/"state.db"),
        json_path=str(tmp_path/"state.json"),
        storage_order="sqlite,json"
    )
    manager=StorageManager(settings)
    provider,_=await manager.select()
    assert provider=="sqlite"
    state=RunState(run_id="r1")
    await manager.commit(state)
    assert (tmp_path/"state.json").exists()
