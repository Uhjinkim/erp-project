#!/usr/bin/env bash
# Validate/build rootless Docker Compose release. Never migrates or starts services.
set -euo pipefail
repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ $# -lt 1 || $# -gt 2 || ( $# -eq 2 && "$2" != --check ) ]]; then
  echo "Usage: $0 /absolute/path/to/compose.env [--check]" >&2
  exit 2
fi
compose_env="$1"
if [[ "$compose_env" != /* || ! -r "$compose_env" ]]; then
  echo "Compose environment file must be an absolute readable path" >&2
  exit 2
fi
command -v docker >/dev/null
compose=(docker compose --env-file "$compose_env" -f "$repo_dir/deploy/compose.production.yml")
# Quiet validation: never render expanded configuration containing credentials.
"${compose[@]}" config --quiet
if [[ "${2:-}" == --check ]]; then
  echo "Compose configuration passed. Container build/runtime were not checked."
  exit 0
fi
if [[ "$(id -u)" == 0 ]]; then
  echo "Run as the deployment user with a rootless Docker daemon, without sudo" >&2
  exit 1
fi
security_options="$(docker info --format '{{json .SecurityOptions}}')"
if [[ "$security_options" != *rootless* ]]; then
  echo "Selected Docker daemon is not rootless; select the rootless context" >&2
  exit 1
fi
"${compose[@]}" build --pull
"${compose[@]}" run --rm --no-deps backend python manage.py check --deploy --fail-level WARNING
"${compose[@]}" run --rm --no-deps --entrypoint /bin/sh nginx -c \
  'envsubst '\''${ERP_DOMAIN}'\'' < /etc/nginx/erp.conf.template > /tmp/nginx.conf && nginx -t -c /tmp/nginx.conf'
echo "Release images built and checked. Database and running services were not changed."
echo "Review docs/guides/ec2-rds-deployment.md before activation."
