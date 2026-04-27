#!/usr/bin/env bash
set -euo pipefail

if [[ -f .env.deploy ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env.deploy
  set +a
fi

host="${WXC_DEPLOY_HOST:-}"
deploy_path="${WXC_DEPLOY_PATH:-/opt/wxc-cfzh}"
ssh_opts="${WXC_DEPLOY_SSH_OPTS:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    host=*|--host=*) host="${1#*=}"; shift ;;
    path=*|--path=*) deploy_path="${1#*=}"; shift ;;
    --) shift; break ;;
    *) break ;;
  esac
done

if [[ -z "$host" ]]; then
  echo "Missing WXC_DEPLOY_HOST. Copy .env.deploy.example to .env.deploy." >&2
  exit 2
fi
if [[ $# -eq 0 ]]; then
  echo "Missing remote command." >&2
  exit 2
fi

printf -v quoted_path '%q' "$deploy_path"
remote_command="cd $quoted_path &&"
for token in "$@"; do
  printf -v quoted_token '%q' "$token"
  remote_command+=" $quoted_token"
done

# shellcheck disable=SC2086
exec ssh $ssh_opts "$host" "$remote_command"
