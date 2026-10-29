#!/usr/bin/env bash
set -euo pipefail
test "$(id -u)" = 0
root_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
python3 - "$root_dir/nginx-ip.conf.template" <<'PY'
import ipaddress
import json
from pathlib import Path
import sys

ip = str(ipaddress.ip_address(json.loads(Path('/etc/erp/runtime.json').read_text())['public_host']))
assert Path('/etc/letsencrypt/live', ip, 'fullchain.pem').exists()
template = Path(sys.argv[1]).read_text()
Path('/etc/nginx/sites-available/erp').write_text(template.replace('${ERP_PUBLIC_IP}', ip))
PY
nginx -t
systemctl reload nginx
install -d -m 0755 /etc/letsencrypt/renewal-hooks/deploy
cat > /etc/letsencrypt/renewal-hooks/deploy/erp-nginx <<'EOF'
#!/bin/sh
set -eu
/usr/sbin/nginx -t
/usr/bin/systemctl reload nginx
EOF
chmod 0755 /etc/letsencrypt/renewal-hooks/deploy/erp-nginx
systemctl is-active snap.certbot.renew.timer
echo 'IP HTTPS and nginx certificate reload hook enabled'
