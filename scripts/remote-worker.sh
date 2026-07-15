#!/usr/bin/env bash
set -Eeuo pipefail

MODE="${1:-apply}"
LOCK_DIR="/run/nekonet-autoupdate-target.lock"
TMP_LOG="$(mktemp)"

cleanup() {
    rm -f "$TMP_LOG"
    [[ -d "$LOCK_DIR" ]] && rm -rf "$LOCK_DIR"
}
trap cleanup EXIT

if [[ "$MODE" == "health" ]]; then
    systemctl is-system-running --wait 2>/dev/null || true
    echo "STATUS=ONLINE"
    exit 0
fi

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    echo "STATUS=SKIPPED"
    echo "REASON=target-lock-held"
    exit 75
fi

start="$(date +%s)"

if ! apt-get -o DPkg::Lock::Timeout=900 update >"$TMP_LOG" 2>&1; then
    cat "$TMP_LOG"
    echo "STATUS=FAILED"
    echo "STAGE=apt-update"
    exit 20
fi

simulation="$(apt-get -o DPkg::Lock::Timeout=900 --simulate dist-upgrade 2>>"$TMP_LOG")" || {
    cat "$TMP_LOG"
    echo "STATUS=FAILED"
    echo "STAGE=simulation"
    exit 21
}

count="$(awk '/^Inst /{c++} END{print c+0}' <<<"$simulation")"
kernel="No"
if grep -Eq '^Inst (linux-image|linux-headers|linux-generic|linux-modules|linux-virtual)' <<<"$simulation"; then
    kernel="Yes"
fi

if (( count == 0 )); then
    reboot="No"
    [[ -f /var/run/reboot-required ]] && reboot="Yes"
    echo "STATUS=CURRENT"
    echo "PACKAGES=0"
    echo "KERNEL_UPDATED=No"
    echo "REBOOT_REQUIRED=$reboot"
    echo "DURATION_SECONDS=$(($(date +%s)-start))"
    exit 0
fi

export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a

if ! apt-get -o DPkg::Lock::Timeout=900 -y dist-upgrade >>"$TMP_LOG" 2>&1; then
    cat "$TMP_LOG"
    echo "STATUS=FAILED"
    echo "STAGE=dist-upgrade"
    exit 22
fi

if ! apt-get -o DPkg::Lock::Timeout=900 -y autoremove >>"$TMP_LOG" 2>&1; then
    cat "$TMP_LOG"
    echo "STATUS=FAILED"
    echo "STAGE=autoremove"
    exit 23
fi

apt-get clean >>"$TMP_LOG" 2>&1 || true

reboot="No"
[[ -f /var/run/reboot-required ]] && reboot="Yes"
[[ "$kernel" == "Yes" ]] && reboot="Yes"

echo "STATUS=SUCCESS"
echo "PACKAGES=$count"
echo "KERNEL_UPDATED=$kernel"
echo "REBOOT_REQUIRED=$reboot"
echo "DURATION_SECONDS=$(($(date +%s)-start))"
