#!/usr/bin/env sh
# Stop all no-Docker production processes started by start-prod-no-docker.sh

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PIDDIR="$ROOT/.pids"

for name in webapp telegram_bot bet_manager deposit_monitor; do
  pidfile="$PIDDIR/${name}.pid"
  if [ -f "$pidfile" ]; then
    pid=$(cat "$pidfile")
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      echo "Stopped $name (PID $pid)"
    fi
    rm -f "$pidfile"
  fi
done
