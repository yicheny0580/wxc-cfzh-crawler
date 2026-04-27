#!/usr/bin/env bash
set -euo pipefail

compose_file="${WXC_LOCAL_COMPOSE_FILE:-docker-compose.local.yml}"
compose=(docker compose -f "$compose_file")

service_running() {
  local service="$1"
  "${compose[@]}" ps --status running --services "$service" | grep -qx "$service"
}

if service_running scheduler; then
  exec "${compose[@]}" exec -T scheduler "$@"
fi

if service_running web; then
  exec "${compose[@]}" exec -T web "$@"
fi

exec "${compose[@]}" run --rm --no-deps admin "$@"
