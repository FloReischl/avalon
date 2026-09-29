#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

fuser -k 8095/tcp 2>/dev/null || true
sleep 0.2

reload_args=(--reload)
if [[ "${AVALON_TAURI_MANAGED:-0}" == "1" ]]; then
  reload_args=()
fi

exec "${project_root}/.venv/bin/python" -m uvicorn app.main:app \
  --app-dir "${project_root}/backend" \
  --host 127.0.0.1 \
  --port 8095 \
  "${reload_args[@]}"

