# NekoNet AutoUpdate v0.2

Complete A/B fleet updater with sequential updates, deferred reboots, fail-closed behavior, resilient storage, live API/WebSockets/metrics, dynamic fleet management, and TLS retrieval from princess.kori.cat.

See [Installation](docs/getting-started/INSTALL-v0.2.md).

## v0.2.1 correction

NekoMusic is a strictly read-only consumer. All maintenance and fleet changes
are local coordinator operations through systemd or
`nekonet-autoupdate-admin`.
