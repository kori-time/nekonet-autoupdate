from __future__ import annotations
import asyncio
import re
from datetime import datetime, timezone
from nekonet_autoupdate.models.state import NetworkStatus

async def network_preflight(peer_ip, max_rtt_ms, max_loss, max_skew, remote):
    process = await asyncio.create_subprocess_exec(
        "ping", "-n", "-q", "-c", "5", "-W", "2", peer_ip,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    output = (await process.communicate())[0].decode(errors="replace")
    loss_match = re.search(r"(\d+(?:\.\d+)?)% packet loss", output)
    rtt_match = re.search(r"= [\d.]+/([\d.]+)/[\d.]+/[\d.]+", output)
    loss = float(loss_match.group(1)) if loss_match else 100.0
    rtt = float(rtt_match.group(1)) if rtt_match else 999999.0
    remote_time = await remote.run(peer_ip, "time", timeout=30)
    skew = abs(int(datetime.now(timezone.utc).timestamp()) - int(remote_time["epoch"]))
    if process.returncode or loss > max_loss or rtt > max_rtt_ms or skew > max_skew:
        raise RuntimeError(f"preflight failed: loss={loss}% rtt={rtt}ms skew={skew}s")
    return NetworkStatus(
        packet_loss_percent=loss,
        average_rtt_ms=rtt,
        clock_skew_seconds=skew,
        checked_at=datetime.now(timezone.utc),
    )
