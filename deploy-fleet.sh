#!/usr/bin/env bash
set -Eeuo pipefail

# NekoNet AutoUpdate fleet deployment script
#
# Run this script from Server A.
#
# Deployment order:
#   1. Server A
#   2. Server B
#   3. princess.kori.cat
#   4. All remaining enabled fleet servers
#
# The deployment stops immediately if any installation or verification fails.

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FLEET_FILE="${FLEET_FILE:-$PROJECT_ROOT/config/fleet.json}"

BOOTSTRAP_USER="${BOOTSTRAP_USER:-}"
SSH_KEY="${SSH_KEY:-}"
SSH_PORT="${SSH_PORT:-2222}"

SERVER_A_IP="${SERVER_A_IP:-10.10.0.8}"
SERVER_B_IP="${SERVER_B_IP:-10.10.0.7}"
PRINCESS_IP="${PRINCESS_IP:-10.10.0.2}"

REMOTE_DIRECTORY="/tmp/nekonet-autoupdate-deploy"

show_help() {
    cat <<'EOF'
Usage:
  sudo env \
    BOOTSTRAP_USER="admin-user" \
    SSH_KEY="/home/admin-user/.ssh/id_ed25519" \
    SSH_PORT="2222" \
    ./deploy-fleet.sh

Required environment variables:
  BOOTSTRAP_USER   Existing sudo-capable account on remote servers
  SSH_KEY          Private SSH key used for bootstrap deployment

Optional environment variables:
  SSH_PORT         SSH port. Default: 2222
  FLEET_FILE       Fleet JSON path
  SERVER_A_IP      Primary coordinator IP
  SERVER_B_IP      Secondary coordinator IP
  PRINCESS_IP      Certificate-source fleet server IP
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    show_help
    exit 0
fi

if [[ $EUID -ne 0 ]]; then
    echo "Run this deployment script with sudo." >&2
    exit 1
fi

if [[ -z "$BOOTSTRAP_USER" ]]; then
    echo "BOOTSTRAP_USER is required." >&2
    show_help >&2
    exit 2
fi

if [[ -z "$SSH_KEY" || ! -r "$SSH_KEY" ]]; then
    echo "SSH_KEY must point to a readable private key." >&2
    show_help >&2
    exit 2
fi

if [[ ! -r "$FLEET_FILE" ]]; then
    echo "Fleet file not found: $FLEET_FILE" >&2
    exit 1
fi

SSH_OPTIONS=(
    -i "$SSH_KEY"
    -p "$SSH_PORT"
    -o BatchMode=yes
    -o ConnectTimeout=15
    -o ServerAliveInterval=10
    -o ServerAliveCountMax=3
    -o StrictHostKeyChecking=accept-new
)

remote_ssh() {
    local ip="$1"
    shift

    ssh         "${SSH_OPTIONS[@]}"         "${BOOTSTRAP_USER}@${ip}"         "$@"
}

copy_project() {
    local ip="$1"

    echo "Copying project files to ${ip}..."

    remote_ssh "$ip"         "rm -rf '$REMOTE_DIRECTORY' && mkdir -p '$REMOTE_DIRECTORY'"

    tar         --exclude='.git'         --exclude='__pycache__'         --exclude='*.pyc'         -C "$PROJECT_ROOT"         -cf -         . |
        ssh             "${SSH_OPTIONS[@]}"             "${BOOTSTRAP_USER}@${ip}"             "tar -C '$REMOTE_DIRECTORY' -xf -"
}

install_local_server_a() {
    echo
    echo "============================================================"
    echo "Installing Server A locally: ${SERVER_A_IP}"
    echo "============================================================"

    "$PROJECT_ROOT/install.sh"         --role A         --enable-service

    systemctl is-active --quiet nekonet-autoupdate.service
}

install_remote_server() {
    local ip="$1"
    local role="$2"
    local certificate_source="$3"

    echo
    echo "============================================================"
    echo "Installing ${ip} as role ${role}"
    echo "============================================================"

    copy_project "$ip"

    local cert_option=""
    if [[ "$certificate_source" == "true" ]]; then
        cert_option="--cert-source"
    fi

    remote_ssh "$ip"         "cd '$REMOTE_DIRECTORY' &&          sudo ./install.sh --role '$role' $cert_option"

    verify_remote_install "$ip" "$role"

    remote_ssh "$ip"         "rm -rf '$REMOTE_DIRECTORY'"
}

verify_remote_install() {
    local ip="$1"
    local role="$2"

    echo "Verifying installation on ${ip}..."

    remote_ssh "$ip"         "test -x /usr/local/sbin/nekonet-worker"

    remote_ssh "$ip"         "id nekonet >/dev/null"

    remote_ssh "$ip"         "test -r /etc/nekonet-autoupdate/fleet.json"

    if [[ "$role" == "A" || "$role" == "B" ]]; then
        remote_ssh "$ip"             "systemctl is-enabled nekonet-autoupdate.service >/dev/null"
    fi
}

fleet_servers() {
    python3 - "$FLEET_FILE" "$SERVER_A_IP" "$SERVER_B_IP" "$PRINCESS_IP" <<'PY'
import json
import sys

fleet_path, server_a, server_b, princess = sys.argv[1:]

with open(fleet_path, encoding="utf-8") as handle:
    fleet = json.load(handle)

servers = []

for entry in fleet.get("servers", []):
    if not entry.get("enabled", True):
        continue

    ip = entry.get("ip")

    if not ip or ip in {server_a, server_b, princess}:
        continue

    servers.append(
        (
            int(entry.get("order", 100)),
            entry.get("name", ip),
            ip,
        )
    )

for _, name, ip in sorted(servers):
    print(f"{name}|{ip}")
PY
}

main() {
    echo "Starting NekoNet AutoUpdate fleet deployment."
    echo "Fleet file: $FLEET_FILE"

    # Step 1: Install the primary coordinator locally.
    install_local_server_a

    # Step 2: Install the secondary coordinator.
    install_remote_server "$SERVER_B_IP" "B" "false"

    # Step 3: Install Princess as a regular worker and Certbot source.
    install_remote_server "$PRINCESS_IP" "worker" "true"

    # Step 4: Install all remaining enabled fleet servers.
    while IFS='|' read -r name ip; do
        [[ -n "$ip" ]] || continue

        echo "Deploying fleet server: ${name} (${ip})"
        install_remote_server "$ip" "worker" "false"
    done < <(fleet_servers)

    echo
    echo "Fleet deployment completed successfully."
}

main "$@"
