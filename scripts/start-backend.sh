#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "${project_root}/.venv/bin/python" -m uvicorn avalo_backend.main:app \
  --app-dir "${project_root}/backend" \
  --host 127.0.0.1 \
  --port 8095 \
  --reload

