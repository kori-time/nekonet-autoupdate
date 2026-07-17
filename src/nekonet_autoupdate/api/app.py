from __future__ import annotations
from fastapi import FastAPI,Header,HTTPException,WebSocket,Request
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST,Gauge,Counter,generate_latest
from nekonet_autoupdate.models.fleet import FleetServer
from nekonet_autoupdate.models.state import RunState
RUNNING=Gauge('nekonet_autoupdate_running','Whether maintenance is running'); GENERATION=Gauge('nekonet_autoupdate_checkpoint_generation','Current generation'); FAILURES=Counter('nekonet_autoupdate_failures_total','Failures'); SERVERS=Gauge('nekonet_autoupdate_servers','Fleet servers',['state'])
def create_app(service,settings):
 app=FastAPI(title='NekoNet AutoUpdate',version='0.2.0')
 def auth(h):
  if settings.api_token and h!=f'Bearer {settings.api_token}':raise HTTPException(401,'Unauthorized')
 @app.on_event('startup')
 async def startup(): service.subscribers=app.state.subscribers; await service.storage.select(); saved=await service.storage.load_best();
 @app.on_event('startup')
 async def monitor(): import asyncio; asyncio.create_task(service.monitor_peer())
 @app.get('/health')
 async def health():return {'status':'ok','version':'0.2.0','role':settings.role,'run_status':service.state.status,'generation':service.state.generation}
 @app.post('/api/v1/runs/start')
 async def start(authorization:str|None=Header(None)):auth(authorization); await service.start_or_resume(); return {'accepted':True}
 @app.get('/api/v1/status')
 async def status(authorization:str|None=Header(None)):auth(authorization); return service.state
 @app.get('/api/v1/servers')
 async def servers(authorization:str|None=Header(None)):auth(authorization); return {'servers':service.state.servers}
 @app.get('/api/v1/storage')
 async def storage(authorization:str|None=Header(None)):auth(authorization); return {'active':service.state.storage_provider,'degraded':service.state.degraded_storage,'providers':service.storage.health_state}
 @app.get('/api/v1/events')
 async def events(authorization:str|None=Header(None)):auth(authorization); return {'events':service.events[-1000:]}
 @app.get('/api/v1/fleet')
 async def fleet(authorization:str|None=Header(None)):auth(authorization); return {'servers':service.fleet.list(True)}
 @app.put('/api/v1/fleet/{sid}')
 async def put(sid:str,server:FleetServer,authorization:str|None=Header(None)):
  auth(authorization)
  if sid!=server.id: raise HTTPException(400,'ID mismatch')
  return service.fleet.upsert(server)
 @app.delete('/api/v1/fleet/{sid}')
 async def delete(sid:str,authorization:str|None=Header(None)):auth(authorization); return {'removed':service.fleet.remove(sid)}
 @app.post('/internal/v1/replicate')
 async def replicate(request:Request,x_nekonet_token:str|None=Header(None)):
  if (settings.internal_token or settings.api_token) and x_nekonet_token!=(settings.internal_token or settings.api_token):raise HTTPException(401,'Unauthorized')
  st=RunState.model_validate(await request.json()); await service.receive_replica(st); return {'generation':st.generation,'checksum':st.checksum}
 @app.get('/metrics',response_class=PlainTextResponse)
 async def metrics():
  RUNNING.set(1 if service.state.status=='running' else 0); GENERATION.set(service.state.generation)
  for s in service.state.servers:SERVERS.labels(state=str(s.state)).inc(0)
  return PlainTextResponse(generate_latest().decode(),media_type=CONTENT_TYPE_LATEST)
 @app.websocket('/ws')
 async def ws(sock:WebSocket):
  if settings.api_token and sock.query_params.get('token')!=settings.api_token:await sock.close(4401);return
  await sock.accept(); app.state.subscribers.add(sock)
  try:
   while True:await sock.receive_text()
  finally:app.state.subscribers.discard(sock)
 app.state.subscribers=set(); return app
