from __future__ import annotations
import httpx

class DiscordNotifier:
    def __init__(self, webhook: str):
        self.webhook = webhook
    async def send(self, title: str, description: str, color: int = 3447003):
        if not self.webhook:
            return
        async with httpx.AsyncClient(timeout=20) as client:
            await client.post(self.webhook, json={
                "username":"NekoNet AutoUpdate",
                "allowed_mentions":{"parse":[]},
                "embeds":[{"title":title,"description":description[:3900],"color":color}]
            })
