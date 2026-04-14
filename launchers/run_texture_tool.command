#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "Python 3 is required but was not found."
  read -r -p "Press Enter to close..."
  exit 1
fi

"$PYTHON_BIN" "$PROJECT_ROOT/texture_resize_tool.py" "$@"
EXIT_CODE=$?

if [ "$EXIT_CODE" -ne 0 ]; then
  echo
  echo "Processing failed."
  read -r -p "Press Enter to close..."
fi

exit "$EXIT_CODE"
