#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPOSITORY_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
BACKEND_DIR="$REPOSITORY_DIR/backend"
FRONTEND_DIR="$REPOSITORY_DIR/frontend"
NGINX_TEMPLATE="$REPOSITORY_DIR/nginx/development.conf.template"

NGINX_PORT=${ERP_DEV_NGINX_PORT:-8080}
BACKEND_PORT=${ERP_DEV_BACKEND_PORT:-8000}
FRONTEND_PORT=${ERP_DEV_FRONTEND_PORT:-5173}
CHECK_ONLY=false

if [[ ${1:-} == "--check" ]]; then
    CHECK_ONLY=true
elif [[ $# -gt 0 ]]; then
    echo "Usage: $0 [--check]" >&2
    exit 2
fi

require_command() {
    local command_name=$1
    local installation_hint=$2

    if ! command -v "$command_name" >/dev/null 2>&1; then
        echo "$command_name was not found. $installation_hint" >&2
        exit 1
    fi
}

validate_port() {
    local name=$1
    local value=$2

    if [[ ! $value =~ ^[0-9]+$ ]] || ((value < 1 || value > 65535)); then
        echo "$name must be a number between 1 and 65535." >&2
        exit 1
    fi
}

port_is_listening() {
    local port=$1

    if command -v lsof >/dev/null 2>&1; then
        lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
        return
    fi
    if command -v nc >/dev/null 2>&1; then
        nc -z 127.0.0.1 "$port" >/dev/null 2>&1
        return
    fi
    return 1
}

require_command uv "Install uv before starting the backend."
require_command bun "Install Bun before starting the frontend."
require_command nginx "Install nginx, for example with 'brew install nginx'."

validate_port ERP_DEV_NGINX_PORT "$NGINX_PORT"
validate_port ERP_DEV_BACKEND_PORT "$BACKEND_PORT"
validate_port ERP_DEV_FRONTEND_PORT "$FRONTEND_PORT"

if [[ $NGINX_PORT == "$BACKEND_PORT" || $NGINX_PORT == "$FRONTEND_PORT" || $BACKEND_PORT == "$FRONTEND_PORT" ]]; then
    echo "Nginx, backend, and frontend ports must be different." >&2
    exit 1
fi

for required_path in \
    "$BACKEND_DIR/manage.py" \
    "$FRONTEND_DIR/package.json" \
    "$NGINX_TEMPLATE"; do
    if [[ ! -f $required_path ]]; then
        echo "Required file not found: $required_path" >&2
        exit 1
    fi
done

if [[ ! -f "$BACKEND_DIR/.env.development" ]]; then
    echo "Backend environment file not found: $BACKEND_DIR/.env.development" >&2
    echo "Copy backend/.env.development.example and fill in the development values." >&2
    exit 1
fi

RUNTIME_DIR=$(mktemp -d "${TMPDIR:-/tmp}/erp-nginx-dev.XXXXXX")
NGINX_CONFIG="$RUNTIME_DIR/nginx.conf"

cleanup() {
    local exit_code=$?
    trap - EXIT INT TERM

    for pid in "${NGINX_PID:-}" "${FRONTEND_PID:-}" "${BACKEND_PID:-}"; do
        if [[ -n $pid ]] && kill -0 "$pid" >/dev/null 2>&1; then
            kill "$pid" >/dev/null 2>&1 || true
        fi
    done
    wait "${NGINX_PID:-}" "${FRONTEND_PID:-}" "${BACKEND_PID:-}" 2>/dev/null || true
    rm -rf -- "$RUNTIME_DIR"
    exit "$exit_code"
}

trap cleanup EXIT INT TERM

sed \
    -e "s/__NGINX_PORT__/$NGINX_PORT/g" \
    -e "s/__BACKEND_PORT__/$BACKEND_PORT/g" \
    -e "s/__FRONTEND_PORT__/$FRONTEND_PORT/g" \
    "$NGINX_TEMPLATE" >"$NGINX_CONFIG"

nginx -t -e "$RUNTIME_DIR/startup-error.log" -p "$RUNTIME_DIR/" -c "$NGINX_CONFIG"

if $CHECK_ONLY; then
    echo "Development command and nginx configuration checks passed."
    exit 0
fi

for port in "$NGINX_PORT" "$BACKEND_PORT" "$FRONTEND_PORT"; do
    if port_is_listening "$port"; then
        echo "Port $port is already in use. Stop the existing process or override the ERP_DEV_*_PORT values." >&2
        exit 1
    fi
done

(
    cd "$BACKEND_DIR"
    exec uv run python manage.py runserver "127.0.0.1:$BACKEND_PORT" --noreload
) &
BACKEND_PID=$!

(
    cd "$FRONTEND_DIR"
    exec bun run dev -- --host 127.0.0.1 --port "$FRONTEND_PORT" --strictPort
) &
FRONTEND_PID=$!

nginx \
    -e "$RUNTIME_DIR/startup-error.log" \
    -p "$RUNTIME_DIR/" \
    -c "$NGINX_CONFIG" \
    -g "daemon off;" &
NGINX_PID=$!

echo
echo "ERP development environment is starting:"
echo "  Nginx:   http://localhost:$NGINX_PORT"
echo "  Backend: http://127.0.0.1:$BACKEND_PORT"
echo "  Frontend:http://127.0.0.1:$FRONTEND_PORT"
echo "  Health:  http://localhost:$NGINX_PORT/api/health/"
echo "Press Ctrl+C to stop all three processes."

while kill -0 "$BACKEND_PID" >/dev/null 2>&1 \
    && kill -0 "$FRONTEND_PID" >/dev/null 2>&1 \
    && kill -0 "$NGINX_PID" >/dev/null 2>&1; do
    sleep 1
done

echo "A development process stopped unexpectedly. Shutting down the remaining processes." >&2
exit 1
