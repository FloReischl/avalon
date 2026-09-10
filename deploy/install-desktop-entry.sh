#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
AVALO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"

SOURCE="$AVALO_ROOT/data/blueprints/desktop/avalo.desktop"
TARGET_DIR="$HOME/.local/share/applications"
TARGET="$TARGET_DIR/avalo.desktop"

[[ -f "$SOURCE" ]] || {
    echo "❌ Desktop entry template not found: $SOURCE" >&2
    exit 1
}

mkdir -p "$TARGET_DIR"

sed "s|@AVALO_ROOT@|$AVALO_ROOT|g" "$SOURCE" > "$TARGET"

echo "✅ Installed Avalo desktop entry: $TARGET"
