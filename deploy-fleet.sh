#!/usr/bin/env bash
set -Eeuo pipefail

[[ $EUID -eq 0 ]] || { echo "Run this deployment from Server A as root." >&2; exit 1; }

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FLEET_FILE="${FLEET_FILE:-$PROJECT_DIR/config/fleet.json}"
SSH_USER="${SSH_USER:-root}"
SSH_PORT="${SSH_PORT:-2222}"
SSH_KEY="${SSH_KEY:-/root/.ssh/nekonet-autoupdate}"
SERVER_A_IP="${SERVER_A_IP:-10.10.0.8}"
SERVER_B_IP="${SERVER_B_IP:-10.10.0.7}"
REMOTE_DIR="/tmp/nekonet-autoupdate-deploy"
ENABLE_COORDINATORS="${ENABLE_COORDINATORS:-true}"

SSH_OPTS=(
    -i "$SSH_KEY"
    -p "$SSH_PORT"
    -o BatchMode=yes
    -o ConnectTimeout=15
    -o ServerAliveInterval=20
    -o ServerAliveCountMax=3
    -o StrictHostKeyChecking=accept-new
)

log() { printf '[%s] %s\n' "$(date --iso-8601=seconds)" "$*"; }
fail() { log "FAILED: $*" >&2; exit 1; }

[[ -r "$FLEET_FILE" ]] || fail "Cannot read fleet file: $FLEET_FILE"
[[ -r "$SSH_KEY" ]] || fail "Cannot read SSH key: $SSH_KEY"

mapfile -t FLEET_ROWS < <(python3 - "$FLEET_FILE" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as handle:
    data=json.load(handle)
for server in data.get("servers", []):
    if not server.get("enabled", True):
        continue
    print("|".join([
        str(server.get("id", "")),
        str(server.get("name", "")),
        str(server.get("ip", "")),
        "true" if server.get("is_coordinator", False) else "false",
    ]))
PY
)

find_row_by_ip() {
    local wanted="$1" row ip
    for row in "${FLEET_ROWS[@]}"; do
        IFS='|' read -r _ _ ip _ <<<"$row"
        [[ "$ip" == "$wanted" ]] && { printf '%s' "$row"; return 0; }
    done
    return 1
}

local_wireguard_ips() {
    ip -4 -o addr show 2>/dev/null | awk '{print $4}' | cut -d/ -f1
}

is_local_ip() {
    local wanted="$1"
    local_wireguard_ips | grep -Fxq "$wanted"
}

verify_local() {
    [[ -x /opt/nekonet-autoupdate/.venv/bin/nekonet-autoupdate ]] || return 1
    [[ -r /etc/nekonet-autoupdate/fleet.json ]] || return 1
}

verify_remote() {
    local ip="$1" role="$2"
    ssh "${SSH_OPTS[@]}" "${SSH_USER}@${ip}" "
        test -x /opt/nekonet-autoupdate/.venv/bin/nekonet-autoupdate &&
        test -r /etc/nekonet-autoupdate/fleet.json &&
        if [ '$role' = worker ]; then
            true
        else
            test -r /etc/nekonet-autoupdate.env &&
            systemctl is-enabled nekonet-autoupdate.service >/dev/null
        fi
    "
}

install_local_a() {
    log "Installing Server A locally (${SERVER_A_IP})..."
    local args=(--role A)
    [[ "$ENABLE_COORDINATORS" == "true" ]] && args+=(--enable-service)
    "$PROJECT_DIR/install.sh" "${args[@]}"
    verify_local || fail "Server A verification failed"
    log "Server A installation verified."
}

deploy_remote() {
    local name="$1" ip="$2" role="$3"
    log "Deploying to ${name} (${ip}) as ${role}..."

    ssh "${SSH_OPTS[@]}" "${SSH_USER}@${ip}" "rm -rf '$REMOTE_DIR' && mkdir -p '$REMOTE_DIR'"
    tar --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' -C "$PROJECT_DIR" -czf - . \
        | ssh "${SSH_OPTS[@]}" "${SSH_USER}@${ip}" "tar -xzf - -C '$REMOTE_DIR'"

    local command="cd '$REMOTE_DIR' && chmod +x install.sh deploy-fleet.sh && ./install.sh --role '$role'"
    if [[ "$role" != "worker" && "$ENABLE_COORDINATORS" == "true" ]]; then
        command+=" --enable-service"
    fi
    command+=" && rm -rf '$REMOTE_DIR'"

    ssh "${SSH_OPTS[@]}" "${SSH_USER}@${ip}" "$command"
    verify_remote "$ip" "$role" || fail "Verification failed on ${name} (${ip})"
    log "Installation verified on ${name} (${ip})."
}

# Required order: A, B, then all remaining enabled servers.
install_local_a

b_row="$(find_row_by_ip "$SERVER_B_IP")" || fail "Server B is missing from fleet.json"
IFS='|' read -r _ b_name b_ip _ <<<"$b_row"
deploy_remote "$b_name" "$b_ip" B

for row in "${FLEET_ROWS[@]}"; do
    IFS='|' read -r _ name ip is_coordinator <<<"$row"
    [[ "$ip" == "$SERVER_A_IP" || "$ip" == "$SERVER_B_IP" ]] && continue

    if is_local_ip "$ip"; then
        log "Skipping ${name} (${ip}); it is a local address already handled."
        continue
    fi

    deploy_remote "$name" "$ip" worker
done

log "SUCCESS: NekoNet AutoUpdate installed on Server A, Server B, and all enabled fleet servers."
