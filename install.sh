#!/usr/bin/env bash
set -Eeuo pipefail
[[ $EUID -eq 0 ]] || { echo "Run as root."; exit 1; }

install -d -m 755 /opt/nekonet-autoupdate
cp -a . /opt/nekonet-autoupdate/
python3 -m venv /opt/nekonet-autoupdate/.venv
/opt/nekonet-autoupdate/.venv/bin/pip install --upgrade pip
/opt/nekonet-autoupdate/.venv/bin/pip install /opt/nekonet-autoupdate

install -d -m 700 /var/lib/nekonet-autoupdate
install -d -m 700 /etc/nekonet-autoupdate
install -m 600 config/fleet.json /etc/nekonet-autoupdate/fleet.json
install -m 644 systemd/nekonet-autoupdate.service /etc/systemd/system/
[[ -f /etc/nekonet-autoupdate.env ]] || {
  cp config/sample.env /etc/nekonet-autoupdate.env
  chmod 600 /etc/nekonet-autoupdate.env
}

systemctl daemon-reload
echo "Edit /etc/nekonet-autoupdate.env, then enable:"
echo "systemctl enable --now nekonet-autoupdate.service"
