# Automatic Fleet Installation

Run the deployment from **Server A** (`10.10.0.8`) as root.

## Requirements

- Passwordless SSH from Server A to every enabled fleet server
- Dedicated key at `/root/.ssh/nekonet-autoupdate`
- SSH port `2222`
- WireGuard connectivity to every configured server

## Deployment order

1. Server A installs locally and is verified.
2. Server B installs remotely and is verified.
3. Every remaining enabled server installs in `config/fleet.json` order.
4. Deployment stops immediately when an install or verification fails.

## Run

```bash
sudo ./deploy-fleet.sh
```

Server A and Server B receive the coordinator systemd service. Other servers receive the application files and shared fleet configuration but do not run the coordinator service.

## Disable automatic coordinator startup

```bash
sudo ENABLE_COORDINATORS=false ./deploy-fleet.sh
```

## Custom key or SSH user

```bash
sudo SSH_USER=root \
  SSH_PORT=2222 \
  SSH_KEY=/root/.ssh/nekonet-autoupdate \
  ./deploy-fleet.sh
```
