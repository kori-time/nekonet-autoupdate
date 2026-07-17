# NekoNet AutoUpdate Versions

## Current Version

**v0.2**

## v0.1 — Foundation

- A/B coordinator foundation
- Explicit maintenance state machine
- Checkpoint generations and checksums
- Sequential update and reboot phases
- Fail-closed transitions
- REST API and WebSocket foundation
- Prometheus metrics
- Discord notifications
- MySQL, PostgreSQL, SQLite, and JSON storage foundation
- Automated tests

## v0.2 — High Availability and Fleet Operations

- Primary and secondary coordinator architecture
- Coordinator heartbeat and failover
- Shared checkpoint recovery
- Sequential fleet updates
- Canary updates
- Deferred reboot orchestration
- Dynamic fleet management
- Service-aware health checks
- Package inventory and maintenance history
- Storage fallback and automatic backfill
- Centralized certificate synchronization from `princess.kori.cat`
- Dedicated `nekonet` service account
- Read-only REST API and WebSocket for NekoMusic
- Expanded metrics and Discord notifications

## Planned v0.3

- Production hardening
- Stronger split-brain protection
- Multi-site and multi-fleet support
- Expanded operating-system support
- Backup and snapshot hooks
- Extended audit retention
- Additional failure-simulation testing
