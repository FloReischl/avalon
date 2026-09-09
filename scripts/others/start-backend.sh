#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

reload_args=(--reload)
if [[ "${AVALO_TAURI_MANAGED:-0}" == "1" ]]; then
  reload_args=()
fi

exec "${project_root}/.venv/bin/python" -m uvicorn app.main:app \
  --app-dir "~/dev/avalo/backend" \
  --host 127.0.0.1 \
  --port 8095 \
  "${reload_args[@]}"

