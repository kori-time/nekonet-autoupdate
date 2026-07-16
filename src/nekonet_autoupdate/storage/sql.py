from __future__ import annotations
import json
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from nekonet_autoupdate.models.state import RunState
from .base import StorageProvider

DDL = '''
CREATE TABLE IF NOT EXISTS nekonet_state (
    id INTEGER PRIMARY KEY,
    generation BIGINT NOT NULL,
    run_id VARCHAR(128) NOT NULL,
    checksum VARCHAR(128) NOT NULL,
    payload TEXT NOT NULL,
    updated_at VARCHAR(64) NOT NULL
)
'''

class SqlStorage(StorageProvider):
    def __init__(self, name: str, dsn: str):
        self.name = name
        self.engine = create_async_engine(dsn, pool_pre_ping=True)
    async def health(self):
        try:
            async with self.engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
                await conn.execute(text(DDL))
            return True, None
        except Exception as exc:
            return False, str(exc)
    async def load(self):
        async with self.engine.begin() as conn:
            await conn.execute(text(DDL))
            row = (await conn.execute(text("SELECT payload FROM nekonet_state WHERE id=1"))).first()
            return RunState.model_validate_json(row[0]) if row else None
    async def commit(self, state):
        payload = state.model_dump_json()
        async with self.engine.begin() as conn:
            await conn.execute(text(DDL))
            await conn.execute(text("DELETE FROM nekonet_state WHERE id=1"))
            await conn.execute(text(
                "INSERT INTO nekonet_state(id,generation,run_id,checksum,payload,updated_at) "
                "VALUES(1,:g,:r,:c,:p,:u)"
            ), {"g":state.generation,"r":state.run_id,"c":state.checksum,"p":payload,"u":state.updated_at.isoformat()})
