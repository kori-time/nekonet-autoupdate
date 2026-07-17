# NekoNet AutoUpdate v0.2

High-availability, fail-closed Ubuntu fleet update orchestrator for the NekoNet ecosystem.

## v0.2 scope

- High-availability Primary/Secondary coordinator architecture.
- Automatic coordinator failover with checkpoint recovery.
- Explicit maintenance state machine.
- Shared checkpoint generations and checksum validation.
- Sequential fleet update orchestration.
- Canary update support.
- Deferred reboot orchestration.
- Five-minute update spacing.
- Ten-minute reboot spacing.
- Fail-closed maintenance execution.
- Service-aware health verification.
- Read-only REST API.
- Read-only WebSocket interface.
- Prometheus metrics.
- Discord notifications.
- MySQL → PostgreSQL → SQLite → JSON storage fallback.
- Automatic storage recovery and backfill.
- Dynamic fleet management.
- Package inventory and maintenance history.
- Centralized SSL certificate synchronization.
- Comprehensive automated testing.

## Important

NekoNet AutoUpdate is designed around reliability before automation.

Maintenance begins only after coordinator, network, storage, and fleet health checks complete successfully. Any critical failure immediately stops the maintenance run, preserves the latest checkpoint, and notifies administrators.

`princess.kori.cat` (`10.10.0.2`) is the only server responsible for SSL certificate creation and renewal using Certbot. Coordinator servers retrieve validated certificates from Princess and do **not** install or run Certbot themselves.

NekoMusic is a **read-only client**. It consumes the REST API and WebSocket interface for monitoring and reporting only. It cannot start maintenance, modify the fleet, manage certificates, or change system configuration.

## Documentation

- [Getting Started](docs/getting-started/README.md)
- [Administrator Guide](docs/administrator/README.md)
- [Developer Guide](docs/developer/README.md)
- [Reference](docs/reference/README.md)

## Dynamic Fleet

Fleet members are managed through the local coordinator and synchronized across the maintenance state.

Servers can be added, updated, disabled, re-enabled, or removed.

Fleet configuration is stored in:

```text
/etc/nekonet-autoupdate/fleet.json
```

## Resilient Storage

Storage providers are used in the following order:

1. MySQL / MariaDB
2. PostgreSQL
3. SQLite
4. JSON

If a provider becomes unavailable, maintenance automatically continues using the next healthy provider. When a failed provider returns, it is synchronized with the newest committed checkpoint.

## SSL Certificate Management

SSL certificates are centralized on:

```text
princess.kori.cat
WireGuard: 10.10.0.2
```

Only Princess runs Certbot and `certbot.timer`. Coordinator servers receive and validate certificates before activation.

## Automatic Fleet Installation

Deploy from **Server A** in this order:

```text
Server A
→ Server B
→ princess.kori.cat
→ Remaining enabled fleet servers
```

Run:

```bash
sudo ./deploy-fleet.sh
```

Deployment stops immediately if installation or verification fails on any server.

## API Access

NekoMusic and other external consumers receive read-only access through:

```text
GET /health
GET /api/v1/version
GET /api/v1/status
GET /api/v1/fleet
GET /api/v1/servers
GET /api/v1/history
GET /api/v1/events
GET /api/v1/storage
GET /api/v1/network
GET /api/v1/certificates
GET /metrics
WS  /ws
```

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE), [NOTICE](NOTICE), [ATTRIBUTION.md](ATTRIBUTION.md), and [SUPPORT.md](SUPPORT.md).
