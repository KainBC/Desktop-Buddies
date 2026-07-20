#!/usr/bin/env bash
#
# Desktop Buddies launcher.
#
#   ./run.sh relay          start the WebSocket relay (leave running)
#   ./run.sh client         start a desktop client against the local relay
#   ./run.sh setup          install Python dependencies
#
# Env overrides:
#   BUDDIES_URL   client -> relay URL          (default ws://localhost:8765)
#   BUDDIES_HOST  relay bind address           (default 0.0.0.0)
#   PYTHON        python interpreter to use     (default python3)
#
# Notes:
#   - Uses python3, not python (Homebrew/macOS python3 is 3.11+).
#   - BUDDIES_NO_HOTKEY=1 is forced for clients on macOS to avoid the pynput
#     global-hotkey SIGTRAP crash; chat still works by clicking your sprite.
set -euo pipefail

cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"
BUDDIES_URL="${BUDDIES_URL:-ws://localhost:8765}"
BUDDIES_HOST="${BUDDIES_HOST:-0.0.0.0}"

usage() {
  sed -n '3,15p' "$0"
  exit "${1:-0}"
}

cmd="${1:-}"
case "$cmd" in
  setup)
    exec "$PYTHON" -m pip install -r requirements.txt
    ;;
  relay)
    echo "Starting relay on ws://$BUDDIES_HOST:8765 (Ctrl-C to stop)"
    exec env BUDDIES_HOST="$BUDDIES_HOST" "$PYTHON" -m relay
    ;;
  client)
    no_hotkey="${BUDDIES_NO_HOTKEY:-}"
    if [ -z "$no_hotkey" ] && [ "$(uname -s)" = "Darwin" ]; then
      no_hotkey=1   # avoid the macOS pynput hotkey crash by default
    fi
    echo "Starting client -> $BUDDIES_URL (hotkey disabled: ${no_hotkey:-0})"
    exec env BUDDIES_URL="$BUDDIES_URL" BUDDIES_NO_HOTKEY="${no_hotkey:-0}" \
      "$PYTHON" -m Src
    ;;
  ""|-h|--help|help)
    usage 0
    ;;
  *)
    echo "Unknown command: $cmd" >&2
    usage 1
    ;;
esac
