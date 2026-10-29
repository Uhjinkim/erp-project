#!/bin/sh

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPOSITORY_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
ENV_FILE="$REPOSITORY_DIR/.env"
ENV_FILE_SET=0
DIAGNOSTIC=0
while [ "$#" -gt 0 ]; do
    case "$1" in
        --diagnostic) DIAGNOSTIC=1 ;;
        -*) echo "Usage: $0 [ENV_FILE] [--diagnostic]" >&2; exit 1 ;;
        *)
            if [ "$ENV_FILE_SET" -eq 1 ]; then
                echo "Only one environment file may be supplied." >&2
                exit 1
            fi
            ENV_FILE=$1
            ENV_FILE_SET=1
            ;;
    esac
    shift
done

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

# %h is expanded inside ProxyCommand, so accept only a hostname/SSH alias here.
case "$SSH_HOST" in
    -* | *[!a-zA-Z0-9_.-]*)
        echo "SSH_HOST must be a hostname or SSH alias, without a URL scheme or shell characters." >&2
        exit 1
        ;;
esac

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

if ! command -v cloudflared >/dev/null 2>&1; then
    echo "cloudflared not found. Install it and add it to PATH before opening the SSH tunnel." >&2
    exit 1
fi

set -- ssh \
    -N \
    -o "ProxyCommand=cloudflared access ssh --hostname %h" \
    -o ExitOnForwardFailure=yes \
    -o ServerAliveInterval=60 \
    -o ServerAliveCountMax=3 \
    -p "$SSH_PORT"

if [ "$DIAGNOSTIC" -eq 1 ]; then
    # mktemp creates a private directory; logs contain connection metadata, not passwords.
    DIAGNOSTIC_DIR=$(mktemp -d "${TMPDIR:-/tmp}/erp-ssh-diagnostic.XXXXXX")
    DIAGNOSTIC_LOG="$DIAGNOSTIC_DIR/ssh.log"
    printf 'SSH diagnostic started at %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" > "$DIAGNOSTIC_LOG"
    set -- "$@" -vv -E "$DIAGNOSTIC_LOG"
    echo "SSH diagnostic log: $DIAGNOSTIC_LOG"
fi

if [ -n "$SSH_IDENTITY_FILE" ]; then
    set -- "$@" -i "$SSH_IDENTITY_FILE"
fi

set -- "$@" \
    -L "$SSH_TUNNEL_BIND_HOST:$DB_TUNNEL_LOCAL_PORT:$DB_TUNNEL_REMOTE_HOST:$DB_TUNNEL_REMOTE_PORT" \
    -L "$SSH_TUNNEL_BIND_HOST:$REDIS_TUNNEL_LOCAL_PORT:$REDIS_TUNNEL_REMOTE_HOST:$REDIS_TUNNEL_REMOTE_PORT" \
    "$SSH_USER@$SSH_HOST"

echo "Opening PostgreSQL tunnel on $SSH_TUNNEL_BIND_HOST:$DB_TUNNEL_LOCAL_PORT"
echo "Opening Redis tunnel on $SSH_TUNNEL_BIND_HOST:$REDIS_TUNNEL_LOCAL_PORT"
echo "Complete Cloudflare Access browser sign-in if prompted, then SSH authentication."
echo "Keep this terminal open. Press Ctrl+C to close the tunnels."

exec "$@"
