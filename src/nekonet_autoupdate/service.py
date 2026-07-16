from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from nekonet_autoupdate.models.state import RunState, RunPhase
from nekonet_autoupdate.storage.manager import StorageManager
from nekonet_autoupdate.coordinator.state_machine import transition
from nekonet_autoupdate.coordinator.preflight import network_preflight
from nekonet_autoupdate.notifications.discord import DiscordNotifier
from nekonet_autoupdate.coordinator.fleet_registry import FleetRegistry

class CoordinatorService:
    def __init__(self, settings):
        self.settings=settings
        self.storage=StorageManager(settings)
        self.notifier=DiscordNotifier(settings.discord_webhook)
        self.state=RunState(run_id="idle")
        self.events=[]
        self.fleet=FleetRegistry(settings.fleet_path)

    async def emit(self,event_type,payload):
        event={"type":event_type,"time":datetime.now(timezone.utc).isoformat(),"payload":payload}
        self.events.append(event)

    async def set_phase(self,phase,message):
        self.state.phase=transition(self.state.phase,phase)
        self.state.message=message
        await self.storage.commit(self.state)
        await self.emit("phase.changed",{"phase":phase,"message":message})

    async def start_run(self, run_id: str):
        self.state=RunState(
            run_id=run_id,status="running",phase=RunPhase.IDLE,
            active_coordinator=self.settings.coordinator_name,
            coordinator_role=self.settings.role
        )
        await self.set_phase(RunPhase.LEADER_ELECTION,"Coordinator leadership established.")
        await self.set_phase(RunPhase.NETWORK_PREFLIGHT,"Running network preflight.")
        await network_preflight(
            self.settings.peer_ip,
            self.settings.max_avg_rtt_ms,
            self.settings.max_packet_loss_percent
        )
        await self.set_phase(RunPhase.STORAGE_SELECTION,"Selecting storage provider.")
        provider, errors = await self.storage.select()
        self.state.storage_provider=provider
        self.state.degraded_storage=(provider != self.settings.storage_order.split(",")[0])
        await self.storage.commit(self.state)
        await self.set_phase(RunPhase.REGULAR_UPDATES,"Ready to begin sequential updates.")
        await self.notifier.send("Fleet maintenance started",f"Run `{run_id}` started on `{self.settings.coordinator_name}`.")
