from types import SimpleNamespace
import pytest

from nekonet_autoupdate.models.state import RunState
from nekonet_autoupdate.storage.manager import StorageManager


@pytest.mark.asyncio
async def test_commit_survives_missing_remote_databases(tmp_path):
    settings = SimpleNamespace(
        mysql_dsn="",
        postgresql_dsn="",
        sqlite_path=str(tmp_path / "state.db"),
        json_path=str(tmp_path / "status.json"),
        storage_order="mysql,postgresql,sqlite,json",
    )
    manager = StorageManager(settings)
    state = RunState(run_id="run-1")
    report = await manager.commit(state)
    assert "sqlite" in report.committed
    assert "json" in report.committed
    assert state.generation == 1


@pytest.mark.asyncio
async def test_repair_keeps_generation_and_checksum(tmp_path):
    settings = SimpleNamespace(
        mysql_dsn="",
        postgresql_dsn="",
        sqlite_path=str(tmp_path / "state.db"),
        json_path=str(tmp_path / "status.json"),
        storage_order="sqlite,json",
    )
    manager = StorageManager(settings)
    state = RunState(run_id="run-2")
    await manager.commit(state)
    result = await manager.repair()
    assert result["generation"] == state.generation
    assert result["checksum"] == state.checksum
