from __future__ import annotations
import asyncio, re

async def network_preflight(peer_ip: str, max_rtt_ms: float, max_loss: float):
    proc = await asyncio.create_subprocess_exec(
        "ping","-n","-q","-c","5","-W","2",peer_ip,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )
    out=(await proc.communicate())[0].decode(errors="replace")
    loss_match=re.search(r"(\d+(?:\.\d+)?)% packet loss",out)
    rtt_match=re.search(r"= [\d.]+/([\d.]+)/[\d.]+/[\d.]+",out)
    loss=float(loss_match.group(1)) if loss_match else 100.0
    rtt=float(rtt_match.group(1)) if rtt_match else 999999.0
    if proc.returncode != 0 or loss > max_loss or rtt > max_rtt_ms:
        raise RuntimeError(f"Network preflight failed: loss={loss}%, avg_rtt={rtt}ms")
    return {"packet_loss_percent":loss,"average_rtt_ms":rtt}
