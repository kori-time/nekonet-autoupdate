from __future__ import annotations
import asyncio,hashlib
from datetime import datetime,timezone
from .json_store import JsonStorage
from .sql import SqlStorage
class StorageManager:
 def __init__(self,s):
  self.settings=s; self.providers={}; self.health_state={}; self.active=None; self.latest_state=None; self._task=None
  if s.mysql_dsn:self.providers['mysql']=SqlStorage('mysql',s.mysql_dsn)
  if s.postgresql_dsn:self.providers['postgresql']=SqlStorage('postgresql',s.postgresql_dsn)
  self.providers['sqlite']=SqlStorage('sqlite',f'sqlite+aiosqlite:///{s.sqlite_path}'); self.providers['json']=JsonStorage(s.json_path)
 async def select(self):
  errors={}; preferred=self.settings.storage_order.split(',')[0].strip()
  for n in self.settings.storage_order.split(','):
   n=n.strip(); p=self.providers.get(n)
   if not p:continue
   ok,e=await p.health(); self.health_state[n]={'healthy':ok,'error':e}
   if ok:self.active=p; return n,errors,n!=preferred
   errors[n]=e
  raise RuntimeError(f'No healthy storage: {errors}')
 @staticmethod
 def checksum(state):
  c=state.model_copy(deep=True); c.checksum=''; return hashlib.sha256(c.model_dump_json(exclude_none=False).encode()).hexdigest()
 async def write_exact(self,state):
  healthy=[]; failures={}
  for n,p in self.providers.items():
   try:
    ok,e=await p.health(); self.health_state[n]={'healthy':ok,'error':e}
    if ok: await p.commit(state); healthy.append(n)
    else: failures[n]=e or 'unhealthy'
   except Exception as e: self.health_state[n]={'healthy':False,'error':str(e)}; failures[n]=str(e)
  if not healthy: raise RuntimeError('No storage provider accepted checkpoint')
  self.latest_state=state.model_copy(deep=True)
  if self._task is None or self._task.done(): self._task=asyncio.create_task(self._recovery())
  return failures
 async def commit(self,state):
  state.generation+=1; state.previous_checksum=state.checksum; state.updated_at=datetime.now(timezone.utc); state.heartbeat_at=state.updated_at; state.checksum=self.checksum(state)
  f=await self.write_exact(state); preferred=self.settings.storage_order.split(',')[0].strip(); healthy=[n for n,v in self.health_state.items() if v.get('healthy')]; state.storage_provider=self.active.name if self.active else healthy[0]; state.degraded_storage=preferred not in healthy; return f
 async def load_best(self):
  candidates=[]
  for p in self.providers.values():
   try:
    s=await p.load()
    if s:candidates.append(s)
   except Exception:pass
  return max(candidates,key=lambda x:x.generation) if candidates else None
 async def _recovery(self):
  while self.latest_state:
   pending=[n for n,v in self.health_state.items() if not v.get('healthy')]
   if not pending:return
   for n in pending:
    try:
     p=self.providers[n]; ok,e=await p.health(); self.health_state[n]={'healthy':ok,'error':e}
     if ok:await p.commit(self.latest_state)
    except Exception as e:self.health_state[n]={'healthy':False,'error':str(e)}
   await asyncio.sleep(self.settings.storage_retry_seconds)
