from __future__ import annotations
import asyncio, json, shlex
class RemoteError(RuntimeError): pass
class RemoteClient:
    def __init__(self, settings): self.s=settings
    def _base(self,ip): return ['ssh','-i',self.s.ssh_key,'-p',str(self.s.ssh_port),'-o','BatchMode=yes','-o','ConnectTimeout=15','-o','ServerAliveInterval=20','-o','ServerAliveCountMax=3','-o','StrictHostKeyChecking=accept-new',f'{self.s.ssh_user}@{ip}']
    async def run(self,ip,action,*args,timeout=1800):
        cmd=self._base(ip)+['sudo','/usr/local/sbin/nekonet-worker',action,*args]
        p=await asyncio.create_subprocess_exec(*cmd,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.STDOUT)
        try: out=await asyncio.wait_for(p.communicate(),timeout)
        except asyncio.TimeoutError: p.kill(); await p.wait(); raise RemoteError(f'{action} timed out on {ip}')
        text=out[0].decode(errors='replace')
        if p.returncode: raise RemoteError(f'{action} failed on {ip}: {text[-2000:]}')
        try: return json.loads(text.strip().splitlines()[-1])
        except Exception: raise RemoteError(f'Invalid worker response from {ip}: {text[-2000:]}')
    async def reachable(self,ip):
        p=await asyncio.create_subprocess_exec(*(self._base(ip)+['true']),stdout=asyncio.subprocess.DEVNULL,stderr=asyncio.subprocess.DEVNULL)
        try: return await asyncio.wait_for(p.wait(),15)==0
        except asyncio.TimeoutError: p.kill(); return False
