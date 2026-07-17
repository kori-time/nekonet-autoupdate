from __future__ import annotations
import asyncio,re,time
async def network_preflight(peer_ip,max_rtt_ms,max_loss,max_clock_skew,remote):
 p=await asyncio.create_subprocess_exec('ping','-n','-q','-c','5','-W','2',peer_ip,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.STDOUT)
 out=(await p.communicate())[0].decode(errors='replace'); lm=re.search(r'(\d+(?:\.\d+)?)% packet loss',out); rm=re.search(r'= [\d.]+/([\d.]+)/[\d.]+/([\d.]+)',out)
 loss=float(lm.group(1)) if lm else 100.; rtt=float(rm.group(1)) if rm else 999999.; jitter=float(rm.group(2)) if rm else 999999.
 peer=await remote.run(peer_ip,'time',timeout=30); skew=abs(int(time.time())-int(peer['epoch']))
 if p.returncode or loss>max_loss or rtt>max_rtt_ms or skew>max_clock_skew: raise RuntimeError(f'preflight failed: loss={loss}% rtt={rtt}ms skew={skew}s')
 return {'packet_loss_percent':loss,'average_rtt_ms':rtt,'jitter_ms':jitter,'clock_skew_seconds':skew}
