#!/usr/bin/env bash
set -Eeuo pipefail
[[ $EUID -eq 0 ]] || { echo "Run as root."; exit 1; }

systemctl disable --now nekonet-autoupdate.timer 2>/dev/null || true
systemctl stop nekonet-autoupdate.service 2>/dev/null || true

rm -f /usr/local/sbin/nekonet-autoupdate-coordinator
rm -rf /usr/local/lib/nekonet-autoupdate
rm -f /etc/systemd/system/nekonet-autoupdate.service
rm -f /etc/systemd/system/nekonet-autoupdate.timer

systemctl daemon-reload
systemctl reset-failed
echo "Removed. Configuration and state were preserved under /etc and /var/lib."
