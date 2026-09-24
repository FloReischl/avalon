#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
AVALON_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"

SOURCE="$AVALON_ROOT/data/blueprints/desktop/avalon.desktop"
TARGET_DIR="$HOME/.local/share/applications"
TARGET="$TARGET_DIR/avalon.desktop"

[[ -f "$SOURCE" ]] || {
    echo "❌ Desktop entry template not found: $SOURCE" >&2
    exit 1
}

mkdir -p "$TARGET_DIR"

sed "s|@AVALON_ROOT@|$AVALON_ROOT|g" "$SOURCE" > "$TARGET"

echo "✅ Installed Avalon desktop entry: $TARGET"
