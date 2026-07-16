# NekoNet AutoUpdate v0.1

High-availability, fail-closed Ubuntu fleet update orchestrator for the NekoNet ecosystem.

## v0.1 scope

- reliable A/B coordination foundation;
- explicit state machine;
- shared checkpoint generations and checksums;
- sequential update/reboot phases;
- fail-closed transitions;
- REST API;
- WebSocket endpoint;
- Prometheus metrics;
- Discord notifications;
- MySQL → PostgreSQL → SQLite → JSON storage selection;
- local SQLite/JSON mirrors;
- automated tests.

## Important

This repository is a strong v0.1 implementation foundation. Remote execution, continuous heartbeat takeover, peer-to-peer synchronous dual-node commit, and full 18-node destructive integration testing still require deployment-specific validation before production use.

## Documentation

- [Getting Started](docs/getting-started/README.md)
- [Administrator Guide](docs/administrator/README.md)
- [Developer Guide](docs/developer/README.md)
- [Reference](docs/reference/README.md)

## Dynamic fleet

Servers can be added, changed, disabled, or removed through the fleet API or by editing `/etc/nekonet-autoupdate/fleet.json`.

## Resilient storage

MySQL or PostgreSQL outages do not stop maintenance when SQLite or JSON remain healthy. Recovered providers are automatically backfilled with the newest committed state.
