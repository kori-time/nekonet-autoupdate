from __future__ import annotations
from fastapi import FastAPI, Header, HTTPException, WebSocket, Request
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, Counter, generate_latest
from nekonet_autoupdate.models.state import RunState

RUNNING = Gauge("nekonet_autoupdate_running", "Whether maintenance is running")
GENERATION = Gauge("nekonet_autoupdate_checkpoint_generation", "Current generation")
FAILURES = Counter("nekonet_autoupdate_failures_total", "Maintenance failures")
FAILOVERS = Counter("nekonet_autoupdate_failovers_total", "Coordinator failovers")
SERVER_STATES = Gauge("nekonet_autoupdate_servers", "Fleet servers by state", ["state"])
STORAGE_HEALTH = Gauge("nekonet_autoupdate_storage_healthy", "Storage provider health", ["provider"])
NETWORK_RTT = Gauge("nekonet_autoupdate_network_rtt_ms", "Coordinator average RTT")
NETWORK_LOSS = Gauge("nekonet_autoupdate_network_packet_loss_percent", "Coordinator packet loss")

def create_app(service, settings):
    app = FastAPI(title="NekoNet AutoUpdate", version="0.2.1")

    def authenticate(header: str | None) -> None:
        if settings.api_token and header != f"Bearer {settings.api_token}":
            raise HTTPException(status_code=401, detail="Unauthorized")

    @app.on_event("startup")
    async def startup():
        service.subscribers = app.state.subscribers
        await service.storage.select()
        saved = await service.storage.load_best()
        if saved:
            service.state = saved

    @app.on_event("startup")
    async def monitor():
        import asyncio
        asyncio.create_task(service.monitor_peer())

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "version": "0.2.1",
            "role": settings.role,
            "run_status": service.state.status,
            "generation": service.state.generation,
        }

    @app.get("/api/v1/version")
    async def version(authorization: str | None = Header(default=None)):
        authenticate(authorization)
        return {"version": "0.2.1"}

    @app.get("/api/v1/status")
    async def status(authorization: str | None = Header(default=None)):
        authenticate(authorization)
        return service.state

    @app.get("/api/v1/servers")
    async def servers(authorization: str | None = Header(default=None)):
        authenticate(authorization)
        return {"servers": service.state.servers}

    @app.get("/api/v1/servers/{server_id}")
    async def server(server_id: str, authorization: str | None = Header(default=None)):
        authenticate(authorization)
        result = next((item for item in service.state.servers if item.id == server_id), None)
        if result is None:
            raise HTTPException(status_code=404, detail="Server not found")
        return result

    @app.get("/api/v1/storage")
    async def storage(authorization: str | None = Header(default=None)):
        authenticate(authorization)
        return {
            "active": service.state.storage_provider,
            "degraded": service.state.degraded_storage,
            "providers": service.storage.health_state,
        }

    @app.get("/api/v1/network")
    async def network(authorization: str | None = Header(default=None)):
        authenticate(authorization)
        return service.state.network

    @app.get("/api/v1/certificates")
    async def certificates(authorization: str | None = Header(default=None)):
        authenticate(authorization)
        return service.state.certificate

    @app.get("/api/v1/events")
    async def events(authorization: str | None = Header(default=None)):
        authenticate(authorization)
        return {"events": service.events[-1000:]}

    @app.get("/api/v1/fleet")
    async def fleet(authorization: str | None = Header(default=None)):
        authenticate(authorization)
        return {"servers": service.fleet.list(True)}

    @app.get("/api/v1/history")
    async def history(authorization: str | None = Header(default=None)):
        authenticate(authorization)
        return {"runs": await service.history.list()}

    @app.get("/api/v1/history/{run_id}")
    async def history_run(run_id: str, authorization: str | None = Header(default=None)):
        authenticate(authorization)
        result = await service.history.get(run_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return result

    @app.post("/internal/v1/replicate", include_in_schema=False)
    async def replicate(request: Request, x_nekonet_token: str | None = Header(default=None)):
        token = settings.internal_token or settings.api_token
        if token and x_nekonet_token != token:
            raise HTTPException(status_code=401, detail="Unauthorized")
        state = RunState.model_validate(await request.json())
        await service.receive_replica(state)
        return {"generation": state.generation, "checksum": state.checksum}

    @app.get("/metrics", response_class=PlainTextResponse)
    async def metrics():
        RUNNING.set(1 if service.state.status == "running" else 0)
        GENERATION.set(service.state.generation)
        states = {str(server.state) for server in service.state.servers}
        for state in states:
            SERVER_STATES.labels(state=state).set(
                sum(1 for server in service.state.servers if str(server.state) == state)
            )
        for provider, info in service.storage.health_state.items():
            STORAGE_HEALTH.labels(provider=provider).set(1 if info.get("healthy") else 0)
        if service.state.network.average_rtt_ms is not None:
            NETWORK_RTT.set(service.state.network.average_rtt_ms)
        if service.state.network.packet_loss_percent is not None:
            NETWORK_LOSS.set(service.state.network.packet_loss_percent)
        return PlainTextResponse(generate_latest().decode(), media_type=CONTENT_TYPE_LATEST)

    @app.websocket("/ws")
    async def websocket(socket: WebSocket):
        if settings.api_token and socket.query_params.get("token") != settings.api_token:
            await socket.close(code=4401)
            return
        await socket.accept()
        app.state.subscribers.add(socket)
        try:
            while True:
                await socket.receive_text()
        finally:
            app.state.subscribers.discard(socket)

    app.state.subscribers = set()
    return app
