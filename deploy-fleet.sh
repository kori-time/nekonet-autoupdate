#!/usr/bin/env bash
set -Eeuo pipefail
[[ $EUID -eq 0 ]]||{ echo 'Run on Server A with sudo';exit 1;}
D="$(cd "$(dirname "$0")"&&pwd)"; F="${FLEET_FILE:-$D/config/fleet.json}"; BOOTSTRAP_USER="${BOOTSTRAP_USER:?Set BOOTSTRAP_USER}"; PORT="${SSH_PORT:-2222}"; KEY="${SSH_KEY:?Set SSH_KEY}"; B=10.10.0.7
SSH=(ssh -i "$KEY" -p "$PORT" -o StrictHostKeyChecking=accept-new)
deploy(){ n="$1";ip="$2";role="$3";extra="${4:-}";echo "Deploying $n"; tar -C "$D" --exclude=.git -czf - .|"${SSH[@]}" "$BOOTSTRAP_USER@$ip" 'rm -rf /tmp/nekonet-deploy;mkdir /tmp/nekonet-deploy;tar -xzf - -C /tmp/nekonet-deploy'; "${SSH[@]}" "$BOOTSTRAP_USER@$ip" "cd /tmp/nekonet-deploy && sudo ./install.sh --role $role --enable-service $extra";}
cd "$D"; ./install.sh --role A --enable-service
deploy laika.kori.cat "$B" B
while IFS='|' read -r n ip c;do deploy "$n" "$ip" worker "$c";done < <(python3 - "$F" <<'PYLIST'
import json,sys
for s in json.load(open(sys.argv[1]))['servers']:
 if s.get('enabled',True) and s['ip'] not in ('10.10.0.8','10.10.0.7'): print(f"{s['name']}|{s['ip']}|{'--cert-source' if s['ip']=='10.10.0.2' else ''}")
PYLIST
)
