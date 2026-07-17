from __future__ import annotations
import asyncio,httpx,uuid
from datetime import datetime,timezone
from nekonet_autoupdate.models.state import RunState,RunPhase,ServerStatus,ServerState,FailureInfo
from nekonet_autoupdate.storage.manager import StorageManager
from nekonet_autoupdate.coordinator.preflight import network_preflight
from nekonet_autoupdate.coordinator.remote import RemoteClient,RemoteError
from nekonet_autoupdate.notifications.discord import DiscordNotifier
from nekonet_autoupdate.coordinator.fleet_registry import FleetRegistry
from nekonet_autoupdate.storage.history import HistoryStore
class CoordinatorService:
 def __init__(self,s):
  self.settings=s; self.storage=StorageManager(s); self.notifier=DiscordNotifier(s.discord_webhook); self.state=RunState(run_id='idle'); self.events=[]; self.fleet=FleetRegistry(s.fleet_path); self.remote=RemoteClient(s); self.subscribers=set(); self.run_lock=asyncio.Lock(); self.run_task=None; self.history=HistoryStore(s.history_path)
 async def emit(self,t,p):
  e={'type':t,'time':datetime.now(timezone.utc).isoformat(),'payload':p}; self.events.append(e)
  dead=[]
  for ws in self.subscribers:
   try: await ws.send_json(e)
   except Exception:dead.append(ws)
  for ws in dead:self.subscribers.discard(ws)
 async def checkpoint(self,event=None,payload=None,replicate=True):
  await self.storage.commit(self.state)
  if event:await self.emit(event,payload or {})
  await self.history.save(self.state)
  if replicate and self.settings.peer_ip:
   try:
    async with httpx.AsyncClient(timeout=20) as c: await c.post(f'http://{self.settings.peer_ip}:{self.settings.api_port}/internal/v1/replicate',headers={'X-NekoNet-Token':self.settings.internal_token or self.settings.api_token},json=self.state.model_dump(mode='json'))
   except Exception: pass
 async def receive_replica(self,state):
  if state.generation>=self.state.generation:self.state=state; await self.storage.write_exact(state)
 async def fail(self,stage,reason,server=None):
  self.state.status='failed'; self.state.phase=RunPhase.FAILED; self.state.failure=FailureInfo(server=server,stage=stage,reason=reason); self.state.message=reason; await self.checkpoint('maintenance.failed',self.state.failure.model_dump()); await self.notifier.send('⛔ Maintenance stopped',f'**Stage:** `{stage}`\n**Server:** `{server or "n/a"}`\n**Reason:** {reason}',15158332)
 async def start_or_resume(self,run_id=None):
  if self.run_task and not self.run_task.done():return
  self.run_task=asyncio.create_task(self.run(run_id))
 async def run(self,run_id=None):
  async with self.run_lock:
   try:
    existing=await self.storage.load_best()
    if existing and existing.status=='running' and existing.phase not in (RunPhase.COMPLETE,RunPhase.FAILED): self.state=existing; self.state.active_coordinator=self.settings.coordinator_name; self.state.coordinator_role=self.settings.role
    else:
     rid=run_id or datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:6]
     servers=[ServerStatus(id=x.id,name=x.name,ip=x.ip,role=x.role) for x in self.fleet.list(False)]
     self.state=RunState(run_id=rid,status='running',phase=RunPhase.LEADER_ELECTION,active_coordinator=self.settings.coordinator_name,coordinator_role=self.settings.role,servers=servers,message='Leadership established')
    await self.checkpoint('maintenance.started',{'run_id':self.state.run_id}); await self.notifier.send('Fleet maintenance started',f'Run `{self.state.run_id}` on `{self.settings.coordinator_name}`')
    self.state.phase=RunPhase.NETWORK_PREFLIGHT; self.state.message='Network preflight'; await self.checkpoint()
    network=await network_preflight(self.settings.peer_ip,self.settings.max_avg_rtt_ms,self.settings.max_packet_loss_percent,self.settings.max_clock_skew_seconds,self.remote); self.state.network=network; await self.checkpoint('preflight.network',network.model_dump(mode='json'))
    self.state.phase=RunPhase.STORAGE_SELECTION; self.state.message='Storage selection'; await self.checkpoint(); p,_,d=await self.storage.select(); self.state.storage_provider=p; self.state.degraded_storage=d; await self.checkpoint('preflight.passed',{})
    await self._canary_updates(); await self._regular_updates(); await self._regular_reboots(); await self._coordinator('B'); await self._coordinator('A')
    self.state.status='complete'; self.state.phase=RunPhase.COMPLETE; self.state.completed_at=datetime.now(timezone.utc); self.state.message='Maintenance completed'; await self.checkpoint('maintenance.completed',{}); await self.notifier.send('✅ Maintenance complete',f'Run `{self.state.run_id}` completed successfully.',3066993)
   except Exception as e:
    if self.state.phase!=RunPhase.FAILED: await self.fail(str(self.state.phase),str(e))
 def _ss(self,ip):return next(x for x in self.state.servers if x.ip==ip)
 async def _update_target(self,target):
  st=self._ss(target.ip)
  if st.state in (ServerState.UPDATED,ServerState.CURRENT,ServerState.ONLINE):return
  st.state=ServerState.CHECKING; st.started_at=datetime.now(timezone.utc); st.message='Checking updates'; await self.checkpoint('server.update.checking',{'server':target.name})
  policy=target.update_policy
  try:r=await self.remote.run(target.ip,'update',policy.mode,','.join(policy.exclude_packages),str(policy.max_packages or ''))
  except Exception as e:st.state=ServerState.FAILED; await self.fail('update',str(e),target.name); raise
  st.packages_updated=int(r.get('packages',0)); st.package_changes=r.get('package_changes',[]); st.kernel_updated=bool(r.get('kernel_updated')); st.reboot_required=bool(r.get('reboot_required')); st.reboot_reason=r.get('reboot_reason'); st.state=ServerState.UPDATED if st.packages_updated else ServerState.CURRENT; st.completed_at=datetime.now(timezone.utc); st.message='Update completed' if st.packages_updated else 'Already current'; await self.checkpoint('server.update.completed',{'server':target.name,'result':r}); await self.notifier.send(f'✅ {target.name} updated' if st.packages_updated else f'ℹ️ {target.name} current',f'Packages: `{st.packages_updated}`\nReboot required: `{st.reboot_required}`',3066993)
 async def _canary_updates(self):
  targets=sorted([x for x in self.fleet.list(False) if not x.is_coordinator and x.canary],key=lambda x:(x.order,x.name))
  if not targets:return
  self.state.phase=RunPhase.CANARY_UPDATES; self.state.message='Updating canary servers'; await self.checkpoint()
  for target in targets:
   await self._update_target(target); await asyncio.sleep(self.settings.update_spacing_seconds)
 async def _regular_updates(self):
  self.state.phase=RunPhase.REGULAR_UPDATES; self.state.message='Updating regular fleet'; await self.checkpoint()
  targets=sorted([x for x in self.fleet.list(False) if not x.is_coordinator and not x.canary],key=lambda x:(x.order,x.name))
  for target in targets:
   await self._update_target(target); await asyncio.sleep(self.settings.update_spacing_seconds)
 async def _regular_reboots(self):
  self.state.phase=RunPhase.REGULAR_REBOOTS; self.state.message='Rebooting regular fleet'; await self.checkpoint()
  targets=[x for x in self.fleet.list(False) if not x.is_coordinator]
  for t in targets:
   st=self._ss(t.ip)
   if not st.reboot_required or st.state==ServerState.ONLINE:continue
   st.state=ServerState.REBOOTING; await self.checkpoint('server.reboot.started',{'server':t.name}); await self.remote.run(t.ip,'reboot',timeout=60); await asyncio.sleep(60)
   deadline=asyncio.get_running_loop().time()+self.settings.server_return_timeout_seconds
   while asyncio.get_running_loop().time()<deadline:
    if await self.remote.reachable(t.ip):
     try:h=await self.remote.run(t.ip,'health',','.join(t.services),timeout=60)
     except Exception:h={'healthy':False}
     if h.get('healthy'):st.state=ServerState.ONLINE; st.health_ok=True; st.health_results=h.get('health_results',[]); await self.checkpoint('server.reboot.completed',{'server':t.name}); await self.notifier.send(f'✅ {t.name} rebooted','Server returned online and passed health checks.',3066993); break
    await asyncio.sleep(15)
   else:st.state=ServerState.FAILED; await self.fail('reboot-recovery','Server did not return healthy',t.name); raise RuntimeError(f'{t.name} did not return')
   await asyncio.sleep(self.settings.reboot_spacing_seconds)
 async def _coordinator(self,role):
  ip=self.settings.server_b_ip if role=='B' else self.settings.server_a_ip; phase=RunPhase.SERVER_B if role=='B' else RunPhase.SERVER_A; self.state.phase=phase; self.state.message=f'Coordinator {role} maintenance'; await self.checkpoint()
  st=self._ss(ip)
  if st.state in (ServerState.UPDATED,ServerState.CURRENT,ServerState.ONLINE):return
  if ip==self.settings.coordinator_ip:r=await self.remote.run('127.0.0.1','update-local')
  else:r=await self.remote.run(ip,'update')
  st.packages_updated=int(r.get('packages',0)); st.reboot_required=bool(r.get('reboot_required')); st.kernel_updated=bool(r.get('kernel_updated')); st.state=ServerState.UPDATED if st.packages_updated else ServerState.CURRENT; await self.checkpoint('coordinator.update.completed',{'role':role,'result':r})
  if st.reboot_required:
   if ip==self.settings.coordinator_ip:
    st.state=ServerState.REBOOTING; await self.checkpoint('coordinator.reboot.started',{'role':role}); await self.remote.run('127.0.0.1','reboot-local',timeout=60); return
   st.state=ServerState.REBOOTING; await self.checkpoint(); await self.remote.run(ip,'reboot',timeout=60); await asyncio.sleep(60)
   deadline=asyncio.get_running_loop().time()+self.settings.server_return_timeout_seconds
   while asyncio.get_running_loop().time()<deadline:
    if await self.remote.reachable(ip):st.state=ServerState.ONLINE; await self.checkpoint('coordinator.reboot.completed',{'role':role}); return
    await asyncio.sleep(15)
   await self.fail('coordinator-reboot','Coordinator did not return',role); raise RuntimeError(f'Coordinator {role} did not return')
 async def monitor_peer(self):
  if self.settings.role!='B':return
  while True:
   await asyncio.sleep(self.settings.heartbeat_seconds)
   try:
    async with httpx.AsyncClient(timeout=10) as c:r=await c.get(f'http://{self.settings.peer_ip}:{self.settings.api_port}/health'); online=r.status_code==200
   except Exception:online=False
   local=await self.storage.load_best()
   if not online and local and local.status=='running' and local.active_coordinator!=self.settings.coordinator_name: await self.start_or_resume(local.run_id)
