#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCK_FILE="/run/lock/nekonet-autoupdate-install.lock"
LOG_DIR="/var/log/nekonet-autoupdate"
LOG_FILE="$LOG_DIR/install.log"
BACKUP_ROOT="/var/backups/nekonet-autoupdate"
FLEET_FILE="/etc/nekonet-autoupdate/fleet.json"

ROLE=""
ENABLE_SERVICE=false
CERT_SOURCE=false
DEPLOY_AFTER=false
NON_INTERACTIVE=false
NETWORK_MODE=""
NETWORK_INTERFACE=""
CHANGES=()
WARNINGS=()

say() { printf '%s\n' "$*"; }
fail() { say "ERROR: $*" >&2; exit 1; }
record() { CHANGES+=("$*"); }
warn() { WARNINGS+=("$*"); say "WARNING: $*" >&2; }

usage() {
    cat <<'EOF'
Usage: sudo ./install.sh [options]

Options:
  --role A|B|worker
  --enable-service
  --cert-source
  --deploy-fleet
  --non-interactive
  --help
EOF
}

require_named_sudo_user() {
    if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
        fail "Run this installer from a normal administrator account using sudo."
    fi

    if [[ -z "${SUDO_USER:-}" || "$SUDO_USER" == "root" ]]; then
        cat >&2 <<'EOF'
===============================================================================
DIRECT ROOT EXECUTION REFUSED
===============================================================================

NekoNet AutoUpdate must be launched by a named administrator using sudo.

Example:

    sudo ./install.sh

Direct root execution is not permitted.
EOF
        exit 100
    fi

    id "$SUDO_USER" >/dev/null 2>&1 ||
        fail "The sudo user '$SUDO_USER' does not exist."
}

parse_arguments() {
    while (($#)); do
        case "$1" in
            --role)
                [[ $# -ge 2 ]] || fail "Missing value for --role."
                ROLE="$2"
                shift 2
                ;;
            --enable-service)
                ENABLE_SERVICE=true
                shift
                ;;
            --cert-source)
                CERT_SOURCE=true
                shift
                ;;
            --deploy-fleet)
                DEPLOY_AFTER=true
                shift
                ;;
            --non-interactive)
                NON_INTERACTIVE=true
                shift
                ;;
            --help|-h)
                usage
                exit 0
                ;;
            *)
                fail "Unknown argument: $1"
                ;;
        esac
    done
}

acquire_lock() {
    exec 9>"$LOCK_FILE"
    flock -n 9 ||
        fail "Another installation, repair, or upgrade is already running."
}

setup_logging() {
    install -d -m 750 "$LOG_DIR"
    touch "$LOG_FILE"
    chmod 640 "$LOG_FILE"
    exec > >(tee -a "$LOG_FILE") 2>&1
    say "[$(date -Is)] Installer started by $SUDO_USER."
}

preflight() {
    say "Running production preflight checks..."

    [[ -r /etc/os-release ]] || fail "Unable to identify the operating system."
    # shellcheck disable=SC1091
    . /etc/os-release

    [[ "${ID:-}" == "ubuntu" ]] ||
        fail "This release supports Ubuntu only."

    for command_name in apt-get systemctl python3 flock sudo ip df dpkg; do
        command -v "$command_name" >/dev/null ||
            fail "Required command is missing: $command_name"
    done

    if dpkg --audit | grep -q .; then
        fail "dpkg reports an incomplete or broken package state."
    fi

    free_kb="$(df -Pk / | awk 'NR == 2 {print $4}')"
    ((free_kb >= 1048576)) ||
        fail "At least 1 GiB of free space is required."

    if ! timedatectl show -p NTPSynchronized --value 2>/dev/null |
        grep -qx yes; then
        warn "The system clock is not reported as synchronized."
    fi
}

detect_private_network() {
    if command -v wg >/dev/null 2>&1 &&
        ip -o link show type wireguard 2>/dev/null | grep -q .; then
        NETWORK_MODE="private"
        NETWORK_INTERFACE="$(
            ip -o link show type wireguard |
                awk -F': ' 'NR == 1 {print $2}'
        )"
        return 0
    fi

    for interface in tailscale0 zt0 tun0; do
        if ip link show "$interface" >/dev/null 2>&1; then
            NETWORK_MODE="private"
            NETWORK_INTERFACE="$interface"
            return 0
        fi
    done

    return 1
}

private_confirmations() {
    local answer

    cat <<'EOF'
===============================================================================
PRIVATE NETWORK — STEP 1 OF 3
===============================================================================

A private VPN or encrypted mesh is the recommended deployment model.
It reduces exposure, but it does not eliminate operational or security risks.

1) Continue
2) Return to network selection
EOF

    read -r -p "Selection: " answer
    [[ "$answer" == "1" ]] || return 1

    cat <<'EOF'
===============================================================================
PRIVATE NETWORK — STEP 2 OF 3
===============================================================================

You remain responsible for your VPN, firewall, SSH access, backups,
monitoring, configuration, systems, data, and infrastructure.

NekoNet and its developers accept no responsibility for loss, downtime,
security incidents, misconfiguration, or damage.

1) Continue
2) Return to network selection
EOF

    read -r -p "Selection: " answer
    [[ "$answer" == "1" ]] || return 1

    cat <<'EOF'
===============================================================================
PRIVATE NETWORK — STEP 3 OF 3
===============================================================================

The software is provided AS IS, without warranty or support.

Type exactly:

    INSTALL PRIVATE

Type BACK to return to network selection.
Anything else safely cancels installation.
EOF

    read -r -p "> " answer

    [[ "$answer" == "BACK" ]] && return 1
    [[ "$answer" == "INSTALL PRIVATE" ]] || exit 0
}

public_confirmations() {
    local answer

    cat <<'EOF'
===============================================================================
PUBLIC NETWORK — STEP 1 OF 3
===============================================================================

A public deployment is not recommended.

WireGuard, Tailscale, ZeroTier, Headscale, or another trusted private
VPN or encrypted mesh is strongly recommended.

1) Return and use a private network (Recommended)
2) Continue with public networking
EOF

    read -r -p "Selection: " answer
    [[ "$answer" == "2" ]] || return 1

    cat <<'EOF'
===============================================================================
PUBLIC NETWORK — STEP 2 OF 3
===============================================================================

A public deployment may expose your infrastructure to:

- Internet-wide scanning
- SSH attacks and brute-force attempts
- Denial-of-service attacks
- Credential compromise
- Unauthorized access
- Firewall, DNS, routing, or certificate errors
- Data loss, downtime, or infrastructure damage

You are solely responsible for managing these risks.

NekoNet and its developers accept no responsibility for any resulting
loss, incident, outage, damage, or consequence.

1) Return and use a private network (Recommended)
2) Continue and accept the risk
EOF

    read -r -p "Selection: " answer
    [[ "$answer" == "2" ]] || return 1

    cat <<'EOF'
===============================================================================
PUBLIC NETWORK — STEP 3 OF 3
===============================================================================

This is the final warning.

You are responsible for securing every exposed server, service, credential,
backup, and item of data. The software is provided AS IS, without warranty
or support.

Type exactly:

    INSTALL PUBLIC

Type BACK to return to network selection.
Anything else safely cancels installation.
EOF

    read -r -p "> " answer

    [[ "$answer" == "BACK" ]] && return 1
    [[ "$answer" == "INSTALL PUBLIC" ]] || exit 0
}

choose_network() {
    if detect_private_network; then
        say "Detected private network interface: $NETWORK_INTERFACE"
        private_confirmations
        return
    fi

    while true; do
        cat <<'EOF'

No WireGuard or recognized private VPN interface was detected.

1) Private network or VPN
2) Public network
3) Cancel
EOF

        read -r -p "Selection: " choice

        case "$choice" in
            1)
                NETWORK_MODE="private"
                private_confirmations && return
                ;;
            2)
                NETWORK_MODE="public"
                public_confirmations && return
                ;;
            3)
                exit 0
                ;;
            *)
                say "Invalid selection."
                ;;
        esac
    done
}

select_role() {
    [[ -n "$ROLE" ]] && return

    cat <<'EOF'

Select this server's role:

1) Coordinator A
2) Coordinator B
3) Fleet Server
4) Princess Certificate Source
EOF

    read -r -p "Selection: " choice

    case "$choice" in
        1)
            ROLE="A"
            ;;
        2)
            ROLE="B"
            ;;
        3)
            ROLE="worker"
            ;;
        4)
            ROLE="worker"
            CERT_SOURCE=true
            ;;
        *)
            fail "Invalid role selection."
            ;;
    esac
}

validate_role() {
    case "$ROLE" in
        A|B|worker)
            ;;
        *)
            fail "Invalid role: $ROLE"
            ;;
    esac

    if [[ "$CERT_SOURCE" == true && "$ROLE" != "worker" ]]; then
        fail "The certificate source must be a fleet server, not a coordinator."
    fi

    if [[ "$CERT_SOURCE" == true ]]; then
        hostname_value="$(hostname -f 2>/dev/null || hostname)"

        if [[ "$hostname_value" != "princess.kori.cat" ]]; then
            warn "Certificate source hostname is '$hostname_value'; expected princess.kori.cat."
        fi

        if ! ip -o addr show | grep -qw "10.10.0.2"; then
            warn "Certificate source does not currently show IP 10.10.0.2."
        fi
    fi
}

existing_install_menu() {
    [[ -d /opt/nekonet-autoupdate ||
        -d /etc/nekonet-autoupdate ]] || return

    [[ "$NON_INTERACTIVE" == true ]] && return

    cat <<'EOF'

Existing installation detected.

1) Verify and repair this server
2) Upgrade this server
3) Reconfigure and repair
4) Update fleet list only
5) Repair and deploy the fleet
6) Exit
EOF

    read -r -p "Selection: " choice

    case "$choice" in
        1|2)
            ;;
        3)
            ROLE=""
            ;;
        4)
            fleet_wizard
            exit 0
            ;;
        5)
            DEPLOY_AFTER=true
            ;;
        6)
            exit 0
            ;;
        *)
            fail "Invalid selection."
            ;;
    esac
}

backup_existing() {
    timestamp="$(date +%Y%m%d-%H%M%S)"
    backup_directory="$BACKUP_ROOT/$timestamp"

    install -d -m 700 "$backup_directory"

    for path in \
        /etc/nekonet-autoupdate \
        /etc/nekonet-autoupdate.env \
        /etc/sudoers.d/nekonet \
        /opt/nekonet-autoupdate; do

        if [[ -e "$path" ]]; then
            cp -a "$path" "$backup_directory/"
        fi
    done

    record "Backup created: $backup_directory"
}

ensure_packages() {
    export DEBIAN_FRONTEND=noninteractive

    apt-get update
    apt-get install -y \
        python3 \
        python3-venv \
        python3-pip \
        openssh-client \
        curl \
        ca-certificates \
        sudo \
        openssl \
        jq

    record "Required packages verified"
}

ensure_service_account() {
    if ! id nekonet >/dev/null 2>&1; then
        useradd \
            --create-home \
            --shell /bin/bash \
            --user-group \
            nekonet

        record "Created service account: nekonet"
    fi

    passwd -l nekonet >/dev/null 2>&1 || true

    install \
        -d \
        -m 700 \
        -o nekonet \
        -g nekonet \
        /home/nekonet/.ssh

    touch /home/nekonet/.ssh/authorized_keys
    chown nekonet:nekonet /home/nekonet/.ssh/authorized_keys
    chmod 600 /home/nekonet/.ssh/authorized_keys

    install \
        -d \
        -m 700 \
        -o nekonet \
        -g nekonet \
        /var/lib/nekonet-autoupdate \
        /var/lib/nekonet-autoupdate/.ssh

    record "Verified nekonet account and SSH permissions"
}

install_worker_and_sudo() {
    install \
        -m 750 \
        -o root \
        -g root \
        "$PROJECT_ROOT/scripts/nekonet-worker" \
        /usr/local/sbin/nekonet-worker

    cat >/etc/sudoers.d/nekonet <<'EOF'
Defaults:nekonet !requiretty
nekonet ALL=(root) NOPASSWD: /usr/local/sbin/nekonet-worker *
EOF

    chmod 440 /etc/sudoers.d/nekonet
    visudo -cf /etc/sudoers.d/nekonet >/dev/null

    record "Installed restricted worker and sudo policy"
}

install_application_atomically() {
    stage="/opt/nekonet-autoupdate.new"
    previous="/opt/nekonet-autoupdate.previous"

    rm -rf "$stage"
    install -d -m 755 "$stage"
    cp -a "$PROJECT_ROOT/." "$stage/"

    python3 -m venv "$stage/.venv"
    "$stage/.venv/bin/pip" install --upgrade pip
    "$stage/.venv/bin/pip" install "$stage"
    "$stage/.venv/bin/python" -c "import nekonet_autoupdate"

    rm -rf "$previous"

    if [[ -d /opt/nekonet-autoupdate ]]; then
        mv /opt/nekonet-autoupdate "$previous"
    fi

    mv "$stage" /opt/nekonet-autoupdate

    record "Installed application atomically"
}

merge_environment() {
    if [[ ! -f /etc/nekonet-autoupdate.env ]]; then
        install \
            -m 600 \
            "$PROJECT_ROOT/config/sample.env" \
            /etc/nekonet-autoupdate.env

        record "Created environment configuration"
    else
        while IFS= read -r line; do
            [[ "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]] || continue

            key="${line%%=*}"

            if ! grep -q "^${key}=" /etc/nekonet-autoupdate.env; then
                printf '%s\n' "$line" >>/etc/nekonet-autoupdate.env
            fi
        done <"$PROJECT_ROOT/config/sample.env"

        chmod 600 /etc/nekonet-autoupdate.env
        record "Merged new environment keys without replacing existing values"
    fi

    sed -i \
        "s/^NEKONET_ROLE=.*/NEKONET_ROLE=$ROLE/" \
        /etc/nekonet-autoupdate.env
}

fleet_wizard() {
    install -d -m 700 /etc/nekonet-autoupdate

    if [[ ! -f "$FLEET_FILE" ]]; then
        install \
            -m 600 \
            "$PROJECT_ROOT/config/fleet.json" \
            "$FLEET_FILE"
    fi

    chmod 600 "$FLEET_FILE"

    [[ "$NON_INTERACTIVE" == true ]] && return

    read -r -p \
        "Would you like to review or update the fleet IP list now? [y/N]: " \
        answer

    [[ "$answer" =~ ^[Yy]$ ]] || return

    python3 "$PROJECT_ROOT/scripts/fleet-wizard.py" "$FLEET_FILE"
    record "Fleet configuration reviewed"
}

configure_role() {
    install -d -m 700 /etc/nekonet-autoupdate
    merge_environment

    if [[ "$ROLE" == "A" ]]; then
        sed -i \
            -e 's/^NEKONET_COORDINATOR_NAME=.*/NEKONET_COORDINATOR_NAME=falfa.kori.cat/' \
            -e 's/^NEKONET_COORDINATOR_IP=.*/NEKONET_COORDINATOR_IP=10.10.0.8/' \
            -e 's/^NEKONET_PEER_IP=.*/NEKONET_PEER_IP=10.10.0.7/' \
            -e 's/^NEKONET_API_BIND=.*/NEKONET_API_BIND=10.10.0.8/' \
            /etc/nekonet-autoupdate.env
    elif [[ "$ROLE" == "B" ]]; then
        sed -i \
            -e 's/^NEKONET_COORDINATOR_NAME=.*/NEKONET_COORDINATOR_NAME=laika.kori.cat/' \
            -e 's/^NEKONET_COORDINATOR_IP=.*/NEKONET_COORDINATOR_IP=10.10.0.7/' \
            -e 's/^NEKONET_PEER_IP=.*/NEKONET_PEER_IP=10.10.0.8/' \
            -e 's/^NEKONET_API_BIND=.*/NEKONET_API_BIND=10.10.0.7/' \
            /etc/nekonet-autoupdate.env
    fi
}

install_systemd_units() {
    if [[ "$ROLE" == "worker" ]]; then
        systemctl disable --now \
            nekonet-autoupdate.service \
            nekonet-autoupdate.timer \
            nekonet-cert-sync.timer \
            2>/dev/null || true

        record "Configured fleet-server role"
        return
    fi

    install \
        -m 644 \
        "$PROJECT_ROOT"/systemd/* \
        /etc/systemd/system/

    install \
        -m 750 \
        "$PROJECT_ROOT/scripts/sync-certificates.sh" \
        /usr/local/sbin/nekonet-sync-certificates

    systemctl daemon-reload

    systemd-analyze verify \
        /etc/systemd/system/nekonet-autoupdate*.service \
        /etc/systemd/system/nekonet-autoupdate*.timer \
        /etc/systemd/system/nekonet-cert-sync*.service \
        /etc/systemd/system/nekonet-cert-sync*.timer

    if [[ "$ENABLE_SERVICE" == true ]]; then
        systemctl enable --now \
            nekonet-autoupdate.service \
            nekonet-autoupdate.timer \
            nekonet-cert-sync.timer
    fi

    record "Installed coordinator systemd units"
}

configure_certificate_source() {
    [[ "$CERT_SOURCE" == true ]] || return

    apt-get install -y certbot
    systemctl enable --now certbot.timer
    systemctl is-active --quiet certbot.timer ||
        fail "certbot.timer did not start."

    record "Configured Princess as the Certbot source"
}

verify_installation() {
    id nekonet >/dev/null ||
        fail "The nekonet account was not created."

    passwd -S nekonet |
        awk '{print $2}' |
        grep -Eq 'L|LK' ||
        fail "The nekonet password is not locked."

    [[ "$(stat -c %a /home/nekonet/.ssh)" == "700" ]] ||
        fail "The nekonet SSH directory has incorrect permissions."

    [[ -x /usr/local/sbin/nekonet-worker ]] ||
        fail "The worker is missing."

    visudo -cf /etc/sudoers.d/nekonet >/dev/null ||
        fail "The sudo policy is invalid."

    [[ -x /opt/nekonet-autoupdate/.venv/bin/nekonet-autoupdate ]] ||
        fail "The application command is missing."

    [[ -r "$FLEET_FILE" ]] ||
        fail "The fleet configuration is missing."

    if [[ "$ROLE" != "worker" && "$ENABLE_SERVICE" == true ]]; then
        systemctl is-active --quiet nekonet-autoupdate.service ||
            fail "The coordinator service is not active."
    fi

    record "Post-install verification passed"
}

maybe_deploy_fleet() {
    [[ "$ROLE" == "A" ]] || return

    if [[ "$DEPLOY_AFTER" != true &&
        "$NON_INTERACTIVE" != true ]]; then

        read -r -p \
            "Would you like to deploy or repair all configured servers now? [y/N]: " \
            answer

        if [[ "$answer" =~ ^[Yy]$ ]]; then
            DEPLOY_AFTER=true
        fi
    fi

    [[ "$DEPLOY_AFTER" == true ]] || return

    "$PROJECT_ROOT/deploy-fleet.sh" --skip-local-a
}

print_summary() {
    say
    say "==============================================================================="
    say "INSTALLATION SUMMARY"
    say "==============================================================================="
    say "Administrator : $SUDO_USER"
    say "Role          : $ROLE"
    say "Network mode  : $NETWORK_MODE${NETWORK_INTERFACE:+ ($NETWORK_INTERFACE)}"

    for item in "${CHANGES[@]}"; do
        say "  OK   $item"
    done

    for item in "${WARNINGS[@]}"; do
        say "  WARN $item"
    done

    say "Log           : $LOG_FILE"
    say "Installation completed successfully."
}

main() {
    parse_arguments "$@"
    require_named_sudo_user
    acquire_lock
    setup_logging
    preflight
    existing_install_menu

    if [[ "$NON_INTERACTIVE" != true ]]; then
        choose_network
    else
        NETWORK_MODE="${NETWORK_MODE:-private}"
    fi

    select_role
    validate_role
    backup_existing
    ensure_packages
    ensure_service_account
    install_worker_and_sudo
    install_application_atomically
    fleet_wizard
    configure_role
    install_systemd_units
    configure_certificate_source
    verify_installation
    maybe_deploy_fleet
    print_summary
}

main "$@"
