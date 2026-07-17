#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FLEET_FILE="${FLEET_FILE:-/etc/nekonet-autoupdate/fleet.json}"

BOOTSTRAP_USER="${BOOTSTRAP_USER:-${SUDO_USER:-}}"
SSH_KEY="${SSH_KEY:-/home/${BOOTSTRAP_USER}/.ssh/id_ed25519}"
SSH_PORT="${SSH_PORT:-2222}"

SERVER_A_IP="${SERVER_A_IP:-10.10.0.8}"
SERVER_B_IP="${SERVER_B_IP:-10.10.0.7}"
PRINCESS_IP="${PRINCESS_IP:-10.10.0.2}"

SKIP_LOCAL_A=false

if [[ "${1:-}" == "--skip-local-a" ]]; then
    SKIP_LOCAL_A=true
fi

if [[ $EUID -ne 0 ||
    -z "${SUDO_USER:-}" ||
    "$SUDO_USER" == "root" ]]; then

    echo "Run deploy-fleet.sh with sudo from a named administrator account." >&2
    exit 100
fi

[[ -n "$BOOTSTRAP_USER" ]] ||
    {
        echo "BOOTSTRAP_USER is required." >&2
        exit 2
    }

[[ -r "$SSH_KEY" ]] ||
    {
        echo "SSH key is not readable: $SSH_KEY" >&2
        exit 2
    }

[[ -r "$FLEET_FILE" ]] ||
    {
        echo "Fleet file is missing: $FLEET_FILE" >&2
        exit 2
    }

SSH_OPTIONS=(
    -i "$SSH_KEY"
    -p "$SSH_PORT"
    -o BatchMode=yes
    -o ConnectTimeout=15
    -o ServerAliveInterval=10
    -o ServerAliveCountMax=3
    -o StrictHostKeyChecking=yes
)

remote_ssh() {
    local ip="$1"
    shift

    ssh \
        "${SSH_OPTIONS[@]}" \
        "${BOOTSTRAP_USER}@${ip}" \
        "$@"
}

copy_project() {
    local ip="$1"

    remote_ssh "$ip" \
        "rm -rf /tmp/nekonet-deploy && mkdir /tmp/nekonet-deploy"

    tar \
        --exclude=".git" \
        --exclude="*.pyc" \
        --exclude="__pycache__" \
        -C "$PROJECT_ROOT" \
        -cf - \
        . |
        ssh \
            "${SSH_OPTIONS[@]}" \
            "${BOOTSTRAP_USER}@${ip}" \
            "tar -C /tmp/nekonet-deploy -xf -"
}

install_remote() {
    local ip="$1"
    local role="$2"
    local certificate_source="$3"
    local extra_option=""

    echo "Installing $ip as $role..."

    copy_project "$ip"

    if [[ "$certificate_source" == true ]]; then
        extra_option="--cert-source"
    fi

    remote_ssh "$ip" \
        "cd /tmp/nekonet-deploy &&
         sudo ./install.sh
         --role '$role'
         $extra_option
         --non-interactive"

    remote_ssh "$ip" \
        "id nekonet >/dev/null &&
         test -x /usr/local/sbin/nekonet-worker"

    remote_ssh "$ip" \
        "rm -rf /tmp/nekonet-deploy"
}

if [[ "$SKIP_LOCAL_A" != true ]]; then
    "$PROJECT_ROOT/install.sh" \
        --role A \
        --enable-service \
        --non-interactive
fi

install_remote "$SERVER_B_IP" "B" "false"
install_remote "$PRINCESS_IP" "worker" "true"

mapfile -t remaining_servers < <(
    python3 - "$FLEET_FILE" "$SERVER_A_IP" "$SERVER_B_IP" "$PRINCESS_IP" <<'PY'
import json
import sys

fleet_file, server_a, server_b, princess = sys.argv[1:]

with open(fleet_file, encoding="utf-8") as handle:
    fleet = json.load(handle)

servers = sorted(
    fleet.get("servers", []),
    key=lambda item: (
        item.get("order", 100),
        item.get("name", ""),
    ),
)

for server in servers:
    ip = server.get("ip")

    if not server.get("enabled", True):
        continue

    if ip in {server_a, server_b, princess}:
        continue

    print(f"{server.get('name', ip)}|{ip}")
PY
)

for entry in "${remaining_servers[@]}"; do
    IFS="|" read -r name ip <<<"$entry"

    echo "Deploying $name ($ip)..."
    install_remote "$ip" "worker" "false"
done

echo "Fleet deployment completed successfully."
