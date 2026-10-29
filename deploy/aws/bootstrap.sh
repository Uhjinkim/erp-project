#!/usr/bin/env bash
# Run as root on the existing Ubuntu ARM64 host; never accesses the application DB.
set -euo pipefail
root_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
test "$(id -u)" = 0
test "$(uname -m)" = aarch64
id erp >/dev/null
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq nginx curl ca-certificates unzip python3
install -d -m 0755 /etc/erp /usr/local/lib/erp
install -m 0644 "$root_dir/runtime.json.example" /etc/erp/runtime.json
install -m 0755 "$root_dir/asm_exec.py" /usr/local/lib/erp/asm_exec.py
install -m 0755 "$root_dir/erp-release.py" /usr/local/bin/erp-release
install -d -m 0755 -o erp -g erp /srv/erp /srv/erp/releases
install -d -m 0700 -o erp -g erp /home/erp/.config/systemd/user
install -m 0644 -o erp -g erp "$root_dir/erp.service" /home/erp/.config/systemd/user/erp.service
loginctl enable-linger erp
install -d -m 0700 -o erp -g erp /home/erp/.config/erp
curl -fsSL https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem -o /home/erp/.config/erp/rds-global-bundle.pem
chmod 0444 /home/erp/.config/erp/rds-global-bundle.pem
temporary=$(mktemp -d)
trap 'rm -rf "$temporary"' EXIT
if ! command -v aws >/dev/null; then
  curl -fsSL https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip -o "$temporary/awscli.zip"
  unzip -q "$temporary/awscli.zip" -d "$temporary"
  "$temporary/aws/install"
fi
curl -fsSL https://artifacts.awcp.global.on.aws/3.1.1/aarch64-unknown-linux-gnu/aws-workload-credentials-provider -o "$temporary/provider"
echo "8b09dc4e58b84379f580a9ae179940bcb3de0338421f638a43376bf73380ffb6  $temporary/provider" | sha256sum -c -
install -m 0755 "$temporary/provider" /usr/local/bin/aws-workload-credentials-provider
cat > /etc/erp/secrets-provider.toml <<'EOF'
[logging]
log_level = "WARN"
log_to_file = false
[capabilities.secrets_manager]
enabled = true
http_port = 2773
region = "ap-northeast-2"
[capabilities.secrets_manager.security]
ssrf_env_variables = ["AWS_TOKEN"]
EOF
cat > /etc/systemd/system/erp-secrets.service <<'EOF'
[Unit]
Description=ERP AWS Workload Credentials Provider
After=network-online.target
Wants=network-online.target
[Service]
User=erp
Group=erp
RuntimeDirectory=erp-secrets
RuntimeDirectoryMode=0700
WorkingDirectory=/run/erp-secrets
Environment=AWS_REGION=ap-northeast-2
Environment=AWS_TOKEN=file:///run/erp-secrets/token
ExecStartPre=/bin/sh -c 'umask 077; /usr/bin/python3 -c "import secrets; print(secrets.token_urlsafe(32))" > /run/erp-secrets/token'
ExecStart=/usr/local/bin/aws-workload-credentials-provider sm start --config /etc/erp/secrets-provider.toml
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now erp-secrets
erp_uid=$(id -u erp)
runuser -u erp -- env XDG_RUNTIME_DIR="/run/user/$erp_uid" DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$erp_uid/bus" systemctl --user daemon-reload
runuser -u erp -- env XDG_RUNTIME_DIR="/run/user/$erp_uid" DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$erp_uid/bus" systemctl --user enable erp
snap start --enable amazon-ssm-agent
if ! snap list certbot >/dev/null 2>&1; then snap install --classic certbot; fi
install -d -m 0755 /var/lib/letsencrypt
# The initial listener serves only ACME challenges. No ERP data is served over HTTP.
if [ ! -f /etc/nginx/sites-available/erp ]; then
  cat > /etc/nginx/sites-available/erp <<'EOF'
server {
    listen 80 default_server;
    server_name _;
    access_log off;
    location ^~ /.well-known/acme-challenge/ { root /var/lib/letsencrypt; }
    location / { return 404; }
}
EOF
  rm -f /etc/nginx/sites-enabled/default
  ln -sfn /etc/nginx/sites-available/erp /etc/nginx/sites-enabled/erp
fi
nginx -t
systemctl enable --now nginx
systemctl reload nginx
echo "Host prepared; issue/test IP certificate before enabling the HTTPS site."
