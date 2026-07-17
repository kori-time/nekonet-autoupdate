# Install NekoNet AutoUpdate v0.2.1

## 1. Prepare bootstrap SSH access

From Server A, verify your existing sudo-capable administrator account can SSH
to every WireGuard address on port `2222`.

## 2. Deploy the software

```bash
sudo env   BOOTSTRAP_USER="your-admin-user"   SSH_KEY="/home/your-admin-user/.ssh/id_ed25519"   SSH_PORT="2222"   ./deploy-fleet.sh
```

Deployment order is Server A, Server B, Princess, then every other enabled fleet
server. The installer creates the locked `nekonet` service account and installs
the restricted privileged worker.

## 3. Configure coordinator SSH

Create the coordinator key at:

```text
/var/lib/nekonet-autoupdate/.ssh/id_ed25519
```

Place its public key in `/home/nekonet/.ssh/authorized_keys` on every fleet
server.

## 4. Configure both coordinators

Edit `/etc/nekonet-autoupdate.env` on A and B. Configure database DSNs, API and
internal tokens, Discord webhook, certificate settings, and each coordinator's
role, address, and peer address.

## 5. Configure certificates

Certbot is installed only on `princess.kori.cat` (`10.10.0.2`). Coordinators
only retrieve, validate, install, and roll back certificates.

## 6. Enable services

```bash
sudo systemctl enable --now nekonet-autoupdate.service
sudo systemctl enable --now nekonet-autoupdate.timer
sudo systemctl enable --now nekonet-cert-sync.timer
```

## 7. Start a manual run

```bash
sudo systemctl start nekonet-autoupdate-run.service
```

NekoMusic cannot start or cancel maintenance. It can only read the API and
WebSocket.

## 8. Manage the fleet locally

```bash
sudo /opt/nekonet-autoupdate/.venv/bin/nekonet-autoupdate-admin   fleet-upsert server.json

sudo /opt/nekonet-autoupdate/.venv/bin/nekonet-autoupdate-admin   fleet-remove server-id
```
