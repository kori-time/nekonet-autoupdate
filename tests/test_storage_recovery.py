import pytest
from types import SimpleNamespace
from nekonet_autoupdate.storage.manager import StorageManager
from nekonet_autoupdate.models.state import RunState

@pytest.mark.asyncio
async def test_json_and_sqlite_continue_without_remote_sql(tmp_path):
    settings = SimpleNamespace(
        mysql_dsn="",
        postgresql_dsn="",
        sqlite_path=str(tmp_path/"state.db"),
        json_path=str(tmp_path/"state.json"),
        storage_order="mysql,postgresql,sqlite,json",
        storage_retry_seconds=1,
    )
    manager = StorageManager(settings)
    provider, _, degraded = await manager.select()
    assert provider == "sqlite"
    assert degraded is True

    state = RunState(run_id="r1")
    await manager.commit(state)

    assert (tmp_path/"state.db").exists()
    assert (tmp_path/"state.json").exists()
