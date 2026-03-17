#!/usr/bin/env bash
# SciMarkdown MCP Server launcher (NixOS compatible)
DIR="$(cd "$(dirname "$0")" && pwd)"
export LD_LIBRARY_PATH=/nix/store/ihpdbhy4rfxaixiamyb588zfc3vj19al-gcc-15.2.0-lib/lib
exec "$DIR/.venv/bin/python" -m scimarkdown.mcp "$@"
