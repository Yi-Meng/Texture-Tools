#!/bin/bash

set -euo pipefail

CLI_ONLY=0
if [[ "${1:-}" == "--cli-only" ]]; then
  CLI_ONLY=1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DIST_DIR="$PROJECT_ROOT/dist"
BUILD_DIR="$PROJECT_ROOT/build"
SPEC_DIR="$PROJECT_ROOT/spec"

cd "$PROJECT_ROOT"

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "Python 3 is required but was not found."
  exit 1
fi

"$PYTHON_BIN" -m pip install -r requirements.txt

rm -rf "$BUILD_DIR" "$SPEC_DIR"

COMMON_ARGS=(
  --noconfirm
  --clean
  --distpath "$DIST_DIR"
  --workpath "$BUILD_DIR"
  --specpath "$SPEC_DIR"
)

if [[ "$CLI_ONLY" -eq 0 ]]; then
  "$PYTHON_BIN" -m PyInstaller \
    "${COMMON_ARGS[@]}" \
    --name "TexturesTool" \
    --windowed \
    texture_resize_gui.py
fi

"$PYTHON_BIN" -m PyInstaller \
  "${COMMON_ARGS[@]}" \
  --name "TexturesToolCLI" \
  --console \
  texture_resize_tool.py

echo
echo "Build complete."
echo "Artifacts:"
if [[ "$CLI_ONLY" -eq 0 ]]; then
  echo "  GUI: $DIST_DIR/TexturesTool.app"
fi
echo "  CLI: $DIST_DIR/TexturesToolCLI"
