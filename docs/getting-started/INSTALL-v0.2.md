# Install v0.2

1. Extract on Server A (`10.10.0.8`).
2. Run:
```bash
sudo env BOOTSTRAP_USER='your-sudo-user' SSH_KEY='/home/your-sudo-user/.ssh/id_ed25519' SSH_PORT=2222 ./deploy-fleet.sh
```
3. Generate a dedicated Ed25519 key for the `nekonet` account, install its public key in `/home/nekonet/.ssh/authorized_keys` on every server, and copy the private key to both coordinators as `/var/lib/nekonet-autoupdate/.ssh/id_ed25519` with mode `600`.
4. Edit `/etc/nekonet-autoupdate.env` on both coordinators. Set API/internal tokens, Discord webhook, database DSNs, and certificate fields.
5. Certbot is installed only on `princess.kori.cat` (`10.10.0.2`). Configure `NEKONET_CERT_NAME`, domains, email, and webroot. Coordinators only receive validated certificate files.
6. Enable services:
```bash
sudo systemctl enable --now nekonet-autoupdate.service nekonet-autoupdate.timer nekonet-cert-sync.timer
```
7. Verify:
```bash
curl http://10.10.0.8:8088/health
systemctl list-timers 'nekonet-*'
```
8. Start manually:
```bash
curl -X POST -H 'Authorization: Bearer TOKEN' http://10.10.0.8:8088/api/v1/runs/start
```
9. Monitor:
```bash
journalctl -u nekonet-autoupdate.service -f
curl -H 'Authorization: Bearer TOKEN' http://10.10.0.8:8088/api/v1/status
```
