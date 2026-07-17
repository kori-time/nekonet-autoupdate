#!/usr/bin/env bash
set -Eeuo pipefail

# NekoNet AutoUpdate installer
#
# Roles:
#   A       Primary coordinator
#   B       Secondary coordinator
#   worker  Regular fleet server
#
# Certbot is installed only when --cert-source is used. In the current
# architecture, that option should only be used on princess.kori.cat.

ROLE="worker"
ENABLE_SERVICE=false
CERT_SOURCE=false

show_help() {
    cat <<'EOF'
Usage:
  sudo ./install.sh [options]

Options:
  --role A|B|worker   Set the server role. Default: worker
  --enable-service   Enable coordinator services after installation
  --cert-source      Install Certbot and enable certbot.timer
  --help             Show this help message
EOF
}

# Read command-line options.
while (($# > 0)); do
    case "$1" in
        --role)
            [[ $# -ge 2 ]] || {
                echo "Missing value for --role" >&2
                exit 2
            }

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

        --help|-h)
            show_help
            exit 0
            ;;

        *)
            echo "Unknown option: $1" >&2
            show_help >&2
            exit 2
            ;;
    esac
done

# Validate the requested role.
case "$ROLE" in
    A|B|worker)
        ;;
    *)
        echo "Invalid role: $ROLE" >&2
        exit 2
        ;;
esac

# The installer needs root permissions for packages, users, sudoers, and systemd.
if [[ $EUID -ne 0 ]]; then
    echo "Run this installer with sudo." >&2
    exit 1
fi

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export DEBIAN_FRONTEND=noninteractive

echo "[1/8] Installing required packages..."
apt-get update
apt-get install -y     python3     python3-venv     python3-pip     openssh-client     curl     ca-certificates     sudo     openssl

echo "[2/8] Creating the dedicated nekonet service account..."
if ! id nekonet >/dev/null 2>&1; then
    useradd         --create-home         --shell /bin/bash         --user-group         nekonet
fi

# Disable password authentication for the service account.
passwd -l nekonet >/dev/null 2>&1 || true

# Create SSH and state directories.
install -d -m 700 -o nekonet -g nekonet /home/nekonet/.ssh
install -d -m 700 -o nekonet -g nekonet /var/lib/nekonet-autoupdate
install -d -m 700 -o nekonet -g nekonet /var/lib/nekonet-autoupdate/.ssh

echo "[3/8] Installing the restricted privileged worker..."
install     -m 750     "$PROJECT_ROOT/scripts/nekonet-worker"     /usr/local/sbin/nekonet-worker

# Allow the nekonet account to run only the approved worker.
cat >/etc/sudoers.d/nekonet <<'EOF'
nekonet ALL=(root) NOPASSWD: /usr/local/sbin/nekonet-worker *
EOF

chmod 440 /etc/sudoers.d/nekonet
visudo -cf /etc/sudoers.d/nekonet

if [[ "$CERT_SOURCE" == true ]]; then
    echo "[4/8] Installing Certbot on the certificate source..."

    apt-get install -y certbot
    systemctl enable --now certbot.timer
else
    echo "[4/8] Certbot installation skipped."
fi

echo "[5/8] Installing NekoNet AutoUpdate..."
rm -rf /opt/nekonet-autoupdate.new
install -d -m 755 /opt/nekonet-autoupdate.new

cp -a "$PROJECT_ROOT/." /opt/nekonet-autoupdate.new/

python3 -m venv /opt/nekonet-autoupdate.new/.venv

/opt/nekonet-autoupdate.new/.venv/bin/pip install --upgrade pip
/opt/nekonet-autoupdate.new/.venv/bin/pip install /opt/nekonet-autoupdate.new

rm -rf /opt/nekonet-autoupdate
mv /opt/nekonet-autoupdate.new /opt/nekonet-autoupdate

echo "[6/8] Installing fleet configuration..."
install -d -m 700 /etc/nekonet-autoupdate

install     -m 600     "$PROJECT_ROOT/config/fleet.json"     /etc/nekonet-autoupdate/fleet.json

if [[ "$ROLE" == "worker" ]]; then
    echo "[7/8] Worker role selected; coordinator services will not be enabled."

    # A regular fleet server should not run coordinator services.
    systemctl disable --now nekonet-autoupdate.service 2>/dev/null || true
    systemctl disable --now nekonet-autoupdate.timer 2>/dev/null || true
    systemctl disable --now nekonet-cert-sync.timer 2>/dev/null || true
else
    echo "[7/8] Installing coordinator services..."

    install         -m 644         "$PROJECT_ROOT/systemd/nekonet-autoupdate.service"         "$PROJECT_ROOT/systemd/nekonet-autoupdate-run.service"         "$PROJECT_ROOT/systemd/nekonet-autoupdate.timer"         "$PROJECT_ROOT/systemd/nekonet-cert-sync.service"         "$PROJECT_ROOT/systemd/nekonet-cert-sync.timer"         /etc/systemd/system/

    install         -m 750         "$PROJECT_ROOT/scripts/sync-certificates.sh"         /usr/local/sbin/nekonet-sync-certificates

    if [[ ! -f /etc/nekonet-autoupdate.env ]]; then
        cp "$PROJECT_ROOT/config/sample.env" /etc/nekonet-autoupdate.env
        chmod 600 /etc/nekonet-autoupdate.env
    fi

    # Set the coordinator role.
    sed -i         "s/^NEKONET_ROLE=.*/NEKONET_ROLE=$ROLE/"         /etc/nekonet-autoupdate.env

    if [[ "$ROLE" == "A" ]]; then
        # Primary coordinator configuration.
        sed -i             -e 's/^NEKONET_COORDINATOR_NAME=.*/NEKONET_COORDINATOR_NAME=falfa.kori.cat/'             -e 's/^NEKONET_COORDINATOR_IP=.*/NEKONET_COORDINATOR_IP=10.10.0.8/'             -e 's/^NEKONET_PEER_IP=.*/NEKONET_PEER_IP=10.10.0.7/'             -e 's/^NEKONET_API_BIND=.*/NEKONET_API_BIND=10.10.0.8/'             /etc/nekonet-autoupdate.env
    else
        # Secondary coordinator configuration.
        sed -i             -e 's/^NEKONET_COORDINATOR_NAME=.*/NEKONET_COORDINATOR_NAME=laika.kori.cat/'             -e 's/^NEKONET_COORDINATOR_IP=.*/NEKONET_COORDINATOR_IP=10.10.0.7/'             -e 's/^NEKONET_PEER_IP=.*/NEKONET_PEER_IP=10.10.0.8/'             -e 's/^NEKONET_API_BIND=.*/NEKONET_API_BIND=10.10.0.7/'             /etc/nekonet-autoupdate.env
    fi

    systemctl daemon-reload

    if [[ "$ENABLE_SERVICE" == true ]]; then
        systemctl enable --now             nekonet-autoupdate.service             nekonet-autoupdate.timer             nekonet-cert-sync.timer
    fi
fi

echo "[8/8] Installation complete."
echo "Installed role: $ROLE"
