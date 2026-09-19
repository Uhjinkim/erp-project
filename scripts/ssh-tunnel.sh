#!/bin/sh

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPOSITORY_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
ENV_FILE=${1:-"$REPOSITORY_DIR/.env"}

if [ ! -f "$ENV_FILE" ]; then
    echo "Environment file not found: $ENV_FILE" >&2
    echo "Copy .env.example to .env and fill in the SSH connection values." >&2
    exit 1
fi

SSH_PORT=22
SSH_IDENTITY_FILE=
SSH_TUNNEL_BIND_HOST=127.0.0.1
DB_TUNNEL_LOCAL_PORT=5432
DB_TUNNEL_REMOTE_HOST=127.0.0.1
DB_TUNNEL_REMOTE_PORT=5432
REDIS_TUNNEL_LOCAL_PORT=6379
REDIS_TUNNEL_REMOTE_HOST=127.0.0.1
REDIS_TUNNEL_REMOTE_PORT=6379

while IFS= read -r line || [ -n "$line" ]; do
    line=$(printf '%s' "$line" | tr -d '\r')

    case "$line" in
        "" | \#*) continue ;;
        export\ *) line=${line#export } ;;
    esac

    case "$line" in
        *=*) ;;
        *) continue ;;
    esac

    key=${line%%=*}
    value=${line#*=}

    case "$value" in
        \"*\") value=${value#\"}; value=${value%\"} ;;
        \'*\') value=${value#\'}; value=${value%\'} ;;
    esac

    case "$key" in
        DB_PORT|DB_REMOTE_HOST|DB_REMOTE_PORT|REDIS_PORT|REDIS_REMOTE_HOST|REDIS_REMOTE_PORT)
            echo "$key was renamed to a tunnel-specific variable. Update $ENV_FILE from .env.example." >&2
            exit 1
            ;;
        SSH_HOST) SSH_HOST=$value ;;
        SSH_USER) SSH_USER=$value ;;
        SSH_PORT) SSH_PORT=$value ;;
        SSH_IDENTITY_FILE) SSH_IDENTITY_FILE=$value ;;
        SSH_TUNNEL_BIND_HOST) SSH_TUNNEL_BIND_HOST=$value ;;
        DB_TUNNEL_LOCAL_PORT) DB_TUNNEL_LOCAL_PORT=$value ;;
        DB_TUNNEL_REMOTE_HOST) DB_TUNNEL_REMOTE_HOST=$value ;;
        DB_TUNNEL_REMOTE_PORT) DB_TUNNEL_REMOTE_PORT=$value ;;
        REDIS_TUNNEL_LOCAL_PORT) REDIS_TUNNEL_LOCAL_PORT=$value ;;
        REDIS_TUNNEL_REMOTE_HOST) REDIS_TUNNEL_REMOTE_HOST=$value ;;
        REDIS_TUNNEL_REMOTE_PORT) REDIS_TUNNEL_REMOTE_PORT=$value ;;
    esac
done < "$ENV_FILE"

if [ -z "${SSH_HOST:-}" ] || [ -z "${SSH_USER:-}" ]; then
    echo "SSH_HOST and SSH_USER must be set in $ENV_FILE." >&2
    exit 1
fi

check_port() {
    name=$1
    value=$2

    case "$value" in
        "" | *[!0-9]*)
            echo "$name must be a number between 1 and 65535." >&2
            exit 1
            ;;
    esac

    if [ "$value" -lt 1 ] || [ "$value" -gt 65535 ]; then
        echo "$name must be a number between 1 and 65535." >&2
        exit 1
    fi
}

check_port SSH_PORT "$SSH_PORT"
check_port DB_TUNNEL_LOCAL_PORT "$DB_TUNNEL_LOCAL_PORT"
check_port DB_TUNNEL_REMOTE_PORT "$DB_TUNNEL_REMOTE_PORT"
check_port REDIS_TUNNEL_LOCAL_PORT "$REDIS_TUNNEL_LOCAL_PORT"
check_port REDIS_TUNNEL_REMOTE_PORT "$REDIS_TUNNEL_REMOTE_PORT"

if ! command -v ssh >/dev/null 2>&1; then
    echo "OpenSSH client not found. Install ssh and try again." >&2
    exit 1
fi

set -- ssh \
    -N \
    -o ExitOnForwardFailure=yes \
    -o ServerAliveInterval=60 \
    -o ServerAliveCountMax=3 \
    -p "$SSH_PORT"

if [ -n "$SSH_IDENTITY_FILE" ]; then
    set -- "$@" -i "$SSH_IDENTITY_FILE"
fi

set -- "$@" \
    -L "$SSH_TUNNEL_BIND_HOST:$DB_TUNNEL_LOCAL_PORT:$DB_TUNNEL_REMOTE_HOST:$DB_TUNNEL_REMOTE_PORT" \
    -L "$SSH_TUNNEL_BIND_HOST:$REDIS_TUNNEL_LOCAL_PORT:$REDIS_TUNNEL_REMOTE_HOST:$REDIS_TUNNEL_REMOTE_PORT" \
    "$SSH_USER@$SSH_HOST"

echo "Opening PostgreSQL tunnel on $SSH_TUNNEL_BIND_HOST:$DB_TUNNEL_LOCAL_PORT"
echo "Opening Redis tunnel on $SSH_TUNNEL_BIND_HOST:$REDIS_TUNNEL_LOCAL_PORT"
echo "Keep this terminal open. Press Ctrl+C to close the tunnels."

exec "$@"
