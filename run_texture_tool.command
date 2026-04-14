#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
"$SCRIPT_DIR/launchers/run_texture_tool.command" "$@"
