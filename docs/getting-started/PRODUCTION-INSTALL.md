# Production Installation

Run NekoNet AutoUpdate from a named administrator account:

```bash
sudo ./install.sh
```

Direct root execution is rejected with exit code `100`.

The installer performs:

- Production preflight validation
- Installation locking
- Three private-network or public-network acknowledgements
- Existing-install detection
- Backups
- `nekonet` account provisioning
- Restricted sudo installation
- Atomic application installation
- Fleet IP management
- Role-specific systemd setup
- Princess-only Certbot setup
- Post-install verification
- Optional fleet deployment from Coordinator A
