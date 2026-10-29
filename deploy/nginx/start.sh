#!/bin/sh
set -eu
# Accept one DNS hostname only; do not permit nginx directive injection.
case "${ERP_DOMAIN:-}" in
  ""|*[!a-zA-Z0-9.-]*|.*|*..*|*.) echo "ERP_DOMAIN must be a DNS hostname" >&2; exit 1 ;;
esac
envsubst '${ERP_DOMAIN}' < /etc/nginx/erp.conf.template > /tmp/nginx.conf
exec nginx -c /tmp/nginx.conf -g 'daemon off;'
