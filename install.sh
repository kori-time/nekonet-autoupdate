#!/usr/bin/env bash
set -Eeuo pipefail
ROLE=worker; ENABLE=false; CERT_SOURCE=false
while (($#));do case "$1" in --role)ROLE="$2";shift 2;;--enable-service)ENABLE=true;shift;;--cert-source)CERT_SOURCE=true;shift;;*)echo bad arg;exit 2;;esac;done
[[ $EUID -eq 0 ]]||{ echo run as root;exit 1;}
export DEBIAN_FRONTEND=noninteractive
apt-get update; apt-get install -y python3 python3-venv python3-pip openssh-client curl ca-certificates sudo openssl
if ! id nekonet >/dev/null 2>&1;then useradd --create-home --shell /bin/bash --user-group nekonet;fi
passwd -l nekonet >/dev/null 2>&1||true; install -d -m 700 -o nekonet -g nekonet /home/nekonet/.ssh
install -d -m 700 -o nekonet -g nekonet /var/lib/nekonet-autoupdate /var/lib/nekonet-autoupdate/.ssh
install -m 750 scripts/nekonet-worker /usr/local/sbin/nekonet-worker
printf '%s\n' 'nekonet ALL=(root) NOPASSWD: /usr/local/sbin/nekonet-worker *' >/etc/sudoers.d/nekonet
chmod 440 /etc/sudoers.d/nekonet; visudo -cf /etc/sudoers.d/nekonet
if $CERT_SOURCE;then apt-get install -y certbot; systemctl enable --now certbot.timer;fi
rm -rf /opt/nekonet-autoupdate.new; install -d /opt/nekonet-autoupdate.new; cp -a . /opt/nekonet-autoupdate.new/; python3 -m venv /opt/nekonet-autoupdate.new/.venv; /opt/nekonet-autoupdate.new/.venv/bin/pip install --upgrade pip; /opt/nekonet-autoupdate.new/.venv/bin/pip install /opt/nekonet-autoupdate.new; rm -rf /opt/nekonet-autoupdate; mv /opt/nekonet-autoupdate.new /opt/nekonet-autoupdate
install -d -m 700 /etc/nekonet-autoupdate; install -m 600 config/fleet.json /etc/nekonet-autoupdate/fleet.json
if [[ "$ROLE" != worker ]];then
 install -m 644 systemd/nekonet-autoupdate.service systemd/nekonet-autoupdate-run.service systemd/nekonet-autoupdate.timer systemd/nekonet-cert-sync.service systemd/nekonet-cert-sync.timer /etc/systemd/system/; install -m 750 scripts/sync-certificates.sh /usr/local/sbin/nekonet-sync-certificates
 [[ -f /etc/nekonet-autoupdate.env ]]||{ cp config/sample.env /etc/nekonet-autoupdate.env;chmod 600 /etc/nekonet-autoupdate.env;}
 sed -i "s/^NEKONET_ROLE=.*/NEKONET_ROLE=$ROLE/" /etc/nekonet-autoupdate.env
 if [[ "$ROLE" == A ]];then sed -i 's/^NEKONET_COORDINATOR_NAME=.*/NEKONET_COORDINATOR_NAME=falfa.kori.cat/;s/^NEKONET_COORDINATOR_IP=.*/NEKONET_COORDINATOR_IP=10.10.0.8/;s/^NEKONET_PEER_IP=.*/NEKONET_PEER_IP=10.10.0.7/;s/^NEKONET_API_BIND=.*/NEKONET_API_BIND=10.10.0.8/' /etc/nekonet-autoupdate.env; else sed -i 's/^NEKONET_COORDINATOR_NAME=.*/NEKONET_COORDINATOR_NAME=laika.kori.cat/;s/^NEKONET_COORDINATOR_IP=.*/NEKONET_COORDINATOR_IP=10.10.0.7/;s/^NEKONET_PEER_IP=.*/NEKONET_PEER_IP=10.10.0.8/;s/^NEKONET_API_BIND=.*/NEKONET_API_BIND=10.10.0.7/' /etc/nekonet-autoupdate.env;fi
 systemctl daemon-reload; $ENABLE&&systemctl enable --now nekonet-autoupdate.service nekonet-autoupdate.timer nekonet-cert-sync.timer
fi
