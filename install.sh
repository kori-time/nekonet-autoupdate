#!/usr/bin/env bash
set -Eeuo pipefail

ROLE="worker"
ENABLE_SERVICE="false"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
    cat <<'USAGE'
Usage: sudo ./install.sh [--role A|B|worker] [--enable-service]

Roles:
  A       Install as primary coordinator.
  B       Install as secondary coordinator.
  worker  Install project files and fleet configuration only.
USAGE
}

while (($#)); do
    case "$1" in
        --role)
            ROLE="${2:?Missing value for --role}"
            shift 2
            ;;
        --enable-service)
            ENABLE_SERVICE="true"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

case "$ROLE" in
    A|B|worker) ;;
    *) echo "Invalid role: $ROLE" >&2; exit 2 ;;
esac

[[ $EUID -eq 0 ]] || { echo "Run as root." >&2; exit 1; }

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y python3 python3-venv python3-pip openssh-client ca-certificates

rm -rf /opt/nekonet-autoupdate.new
install -d -m 755 /opt/nekonet-autoupdate.new
cp -a "$SOURCE_DIR"/. /opt/nekonet-autoupdate.new/
rm -rf /opt/nekonet-autoupdate.new/.git

python3 -m venv /opt/nekonet-autoupdate.new/.venv
/opt/nekonet-autoupdate.new/.venv/bin/pip install --upgrade pip
/opt/nekonet-autoupdate.new/.venv/bin/pip install /opt/nekonet-autoupdate.new

if [[ -d /opt/nekonet-autoupdate ]]; then
    rm -rf /opt/nekonet-autoupdate.previous
    mv /opt/nekonet-autoupdate /opt/nekonet-autoupdate.previous
fi
mv /opt/nekonet-autoupdate.new /opt/nekonet-autoupdate

install -d -m 700 /var/lib/nekonet-autoupdate
install -d -m 700 /etc/nekonet-autoupdate
install -m 600 "$SOURCE_DIR/config/fleet.json" /etc/nekonet-autoupdate/fleet.json

if [[ "$ROLE" == "A" || "$ROLE" == "B" ]]; then
    install -m 644 "$SOURCE_DIR/systemd/nekonet-autoupdate.service" /etc/systemd/system/

    if [[ ! -f /etc/nekonet-autoupdate.env ]]; then
        cp "$SOURCE_DIR/config/sample.env" /etc/nekonet-autoupdate.env
        chmod 600 /etc/nekonet-autoupdate.env
    fi

    sed -i "s/^NEKONET_ROLE=.*/NEKONET_ROLE=$ROLE/" /etc/nekonet-autoupdate.env

    if [[ "$ROLE" == "A" ]]; then
        sed -i 's/^NEKONET_COORDINATOR_NAME=.*/NEKONET_COORDINATOR_NAME=falfa.kori.cat/' /etc/nekonet-autoupdate.env
        sed -i 's/^NEKONET_COORDINATOR_IP=.*/NEKONET_COORDINATOR_IP=10.10.0.8/' /etc/nekonet-autoupdate.env
        sed -i 's/^NEKONET_PEER_NAME=.*/NEKONET_PEER_NAME=laika.kori.cat/' /etc/nekonet-autoupdate.env
        sed -i 's/^NEKONET_PEER_IP=.*/NEKONET_PEER_IP=10.10.0.7/' /etc/nekonet-autoupdate.env
        sed -i 's/^NEKONET_API_BIND=.*/NEKONET_API_BIND=10.10.0.8/' /etc/nekonet-autoupdate.env
    else
        sed -i 's/^NEKONET_COORDINATOR_NAME=.*/NEKONET_COORDINATOR_NAME=laika.kori.cat/' /etc/nekonet-autoupdate.env
        sed -i 's/^NEKONET_COORDINATOR_IP=.*/NEKONET_COORDINATOR_IP=10.10.0.7/' /etc/nekonet-autoupdate.env
        sed -i 's/^NEKONET_PEER_NAME=.*/NEKONET_PEER_NAME=falfa.kori.cat/' /etc/nekonet-autoupdate.env
        sed -i 's/^NEKONET_PEER_IP=.*/NEKONET_PEER_IP=10.10.0.8/' /etc/nekonet-autoupdate.env
        sed -i 's/^NEKONET_API_BIND=.*/NEKONET_API_BIND=10.10.0.7/' /etc/nekonet-autoupdate.env
    fi

    systemctl daemon-reload
    if [[ "$ENABLE_SERVICE" == "true" ]]; then
        systemctl enable --now nekonet-autoupdate.service
    fi
else
    systemctl disable --now nekonet-autoupdate.service 2>/dev/null || true
fi

echo "NekoNet AutoUpdate installed successfully as role: $ROLE"
