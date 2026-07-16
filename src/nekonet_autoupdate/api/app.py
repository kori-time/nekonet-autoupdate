from __future__ import annotations
from fastapi import FastAPI, Header, HTTPException, WebSocket
from nekonet_autoupdate.models.fleet import FleetServer
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, generate_latest

RUNNING = Gauge("nekonet_autoupdate_running","Whether maintenance is running")
GENERATION = Gauge("nekonet_autoupdate_checkpoint_generation","Current checkpoint generation")

def create_app(service, settings):
    app=FastAPI(title="NekoNet AutoUpdate",version="0.1.0")
    subscribers=set()

    def auth(header: str | None):
        if settings.api_token and header != f"Bearer {settings.api_token}":
            raise HTTPException(status_code=401, detail="Unauthorized")

    @app.get("/health")
    async def health():
        return {"status":"ok","version":"0.1.0"}

    @app.get("/api/v1/status")
    async def status(authorization: str | None = Header(default=None)):
        auth(authorization)
        return service.state

    @app.get("/api/v1/servers")
    async def servers(authorization: str | None = Header(default=None)):
        auth(authorization)
        return {"servers":service.state.servers}

    @app.get("/api/v1/storage")
    async def storage(authorization: str | None = Header(default=None)):
        auth(authorization)
        return {
            "active": service.state.storage_provider,
            "degraded": service.state.degraded_storage,
            "providers": service.storage.health_state,
        }

    @app.get("/api/v1/fleet")
    async def fleet(authorization: str | None = Header(default=None)):
        auth(authorization)
        return {"servers": service.fleet.list(include_disabled=True)}

    @app.get("/api/v1/fleet/{server_id}")
    async def get_fleet_server(server_id: str, authorization: str | None = Header(default=None)):
        auth(authorization)
        server = service.fleet.get(server_id)
        if server is None:
            raise HTTPException(status_code=404, detail="Server not found")
        return server

    @app.put("/api/v1/fleet/{server_id}")
    async def upsert_fleet_server(
        server_id: str,
        server: FleetServer,
        authorization: str | None = Header(default=None),
    ):
        auth(authorization)
        if server.id != server_id:
            raise HTTPException(status_code=400, detail="Path ID and payload ID must match")
        saved = service.fleet.upsert(server)
        await service.emit("fleet.server.updated", saved.model_dump())
        return saved

    @app.delete("/api/v1/fleet/{server_id}")
    async def delete_fleet_server(server_id: str, authorization: str | None = Header(default=None)):
        auth(authorization)
        if not service.fleet.remove(server_id):
            raise HTTPException(status_code=404, detail="Server not found")
        await service.emit("fleet.server.removed", {"id": server_id})
        return {"removed": True, "id": server_id}

    @app.get("/api/v1/events")
    async def events(authorization: str | None = Header(default=None)):
        auth(authorization)
        return {"events":service.events[-500:]}

    @app.get("/metrics", response_class=PlainTextResponse)
    async def metrics():
        RUNNING.set(1 if service.state.status=="running" else 0)
        GENERATION.set(service.state.generation)
        return PlainTextResponse(generate_latest().decode(), media_type=CONTENT_TYPE_LATEST)

    @app.websocket("/ws")
    async def ws(socket: WebSocket):
        token=socket.query_params.get("token")
        if settings.api_token and token != settings.api_token:
            await socket.close(code=4401)
            return
        await socket.accept()
        subscribers.add(socket)
        try:
            while True:
                await socket.receive_text()
        finally:
            subscribers.discard(socket)

    app.state.subscribers=subscribers
    return app
