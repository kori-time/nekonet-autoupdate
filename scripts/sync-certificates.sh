#!/usr/bin/env bash
set -Eeuo pipefail
source /etc/nekonet-autoupdate.env
[[ -n "${NEKONET_CERT_NAME:-}" ]] || exit 0
SSH=(ssh -i "$NEKONET_SSH_KEY" -p "$NEKONET_SSH_PORT" -o BatchMode=yes -o StrictHostKeyChecking=accept-new)
if ! "${SSH[@]}" "$NEKONET_SSH_USER@$NEKONET_CERT_SOURCE_IP" sudo /usr/local/sbin/nekonet-worker cert-status "$NEKONET_CERT_NAME" >/dev/null 2>&1; then
 read -ra domains <<<"$NEKONET_CERT_DOMAINS"; "${SSH[@]}" "$NEKONET_SSH_USER@$NEKONET_CERT_SOURCE_IP" sudo /usr/local/sbin/nekonet-worker cert-create "$NEKONET_CERT_NAME" "$NEKONET_CERT_EMAIL" "$NEKONET_CERT_WEBROOT" "${domains[@]}"
fi
for ip in "$NEKONET_SERVER_A_IP" "$NEKONET_SERVER_B_IP";do
 "${SSH[@]}" "$NEKONET_SSH_USER@$ip" "mkdir -p /var/lib/nekonet-autoupdate/cert-stage/$NEKONET_CERT_NAME"
 "${SSH[@]}" "$NEKONET_SSH_USER@$NEKONET_CERT_SOURCE_IP" sudo /usr/local/sbin/nekonet-worker cert-export "$NEKONET_CERT_NAME" | "${SSH[@]}" "$NEKONET_SSH_USER@$ip" "tar -xf - -C /var/lib/nekonet-autoupdate/cert-stage/$NEKONET_CERT_NAME"
 "${SSH[@]}" "$NEKONET_SSH_USER@$ip" sudo /usr/local/sbin/nekonet-worker cert-install "$NEKONET_CERT_NAME"
done
