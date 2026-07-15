#!/usr/bin/env bash
set -Eeuo pipefail

[[ $EUID -eq 0 ]] || { echo "Run this installer as root."; exit 1; }
BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

apt-get update
apt-get install -y openssh-client python3 util-linux

install -d -m 700 /etc/nekonet-autoupdate
install -d -m 755 /usr/local/lib/nekonet-autoupdate
install -d -m 700 /var/lib/nekonet-autoupdate

install -m 700 "$BASE/scripts/nekonet-autoupdate-coordinator" /usr/local/sbin/
install -m 700 "$BASE/scripts/remote-worker.sh" /usr/local/lib/nekonet-autoupdate/
install -m 600 "$BASE/config/fleet.conf" /etc/nekonet-autoupdate/
install -m 644 "$BASE/systemd/nekonet-autoupdate.service" /etc/systemd/system/
install -m 644 "$BASE/systemd/nekonet-autoupdate.timer" /etc/systemd/system/

if [[ ! -f /etc/nekonet-autoupdate.env ]]; then
    cp "$BASE/sample.env" /etc/nekonet-autoupdate.env
    chmod 600 /etc/nekonet-autoupdate.env
fi

if [[ ! -f /root/.ssh/nekonet-autoupdate ]]; then
    ssh-keygen -t ed25519 -N "" -f /root/.ssh/nekonet-autoupdate -C "NekoNet AutoUpdate"
fi

systemctl daemon-reload

echo
echo "Installed."
echo "1. Edit /etc/nekonet-autoupdate.env"
echo "2. Copy /root/.ssh/nekonet-autoupdate.pub to every fleet server"
echo "3. Enable with: systemctl enable --now nekonet-autoupdate.timer"
