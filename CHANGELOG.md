# Changelog

## 0.2.0
- Real update and reboot orchestration
- A/B checkpoint replication and takeover monitor
- Dedicated nekonet account and restricted sudo worker
- Certbot only on princess; TLS pulled to coordinators
- Weekly update and daily certificate timers
- WebSocket events and Prometheus metrics

## 0.2.1

- Made the public API and WebSocket strictly read-only.
- Moved run and fleet control to local CLI and systemd.
- Added run history and detailed per-server package inventory.
- Added canary ordering and per-server update policies.
- Added service-aware health checks and detailed network status.
- Added certificate status and rollback support.
- Expanded Prometheus metrics.
