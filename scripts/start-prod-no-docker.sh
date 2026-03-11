#!/usr/bin/env sh
# Production standup without Docker for tg.ma8ka.com
# Requires: poetry, .env, and (for HTTPS) nginx + certbot on the host

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Load .env
if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi

export ENVIRONMENT=production
export WEBAPP_URL="${WEBAPP_URL:-https://tg.ma8ka.com/}"

# Directories (same layout as Docker)
mkdir -p db staticfiles
touch bet_manager.log next_block_sync.txt
[ -f db/db.sqlite3 ] || touch db/db.sqlite3
chmod -R a+rw db bet_manager.log next_block_sync.txt 2>/dev/null || true

# Symlinks so Django (from webapp/) uses repo-level db and static
[ -L webapp/db ] || ln -sfn ../db webapp/db
[ -L webapp/static ] || ln -sfn ../staticfiles webapp/static

# Django migrate and collectstatic (run from webapp so BASE_DIR is webapp/)
cd webapp
poetry run python manage.py migrate --no-input
poetry run python manage.py collectstatic --no-input
cd "$ROOT"

# PIDs dir for background processes
PIDDIR="$ROOT/.pids"
mkdir -p "$PIDDIR"

_start() {
  name="$1"
  shift
  log="$ROOT/logs"
  mkdir -p "$log"
  nohup "$@" >> "$log/${name}.log" 2>&1 &
  echo $! > "$PIDDIR/${name}.pid"
  echo "Started $name (PID $(cat "$PIDDIR/${name}.pid"))"
}

# Start app (gunicorn on 127.0.0.1:8000 so nginx can proxy)
export PORT=8000
_start webapp env ENVIRONMENT=production sh -c 'cd webapp && poetry run gunicorn -c gunicorn.conf.py -b 127.0.0.1:8000 webapp.wsgi'

# Start telegram bot
_start telegram_bot env WEBAPP_URL="$WEBAPP_URL" ENVIRONMENT=production poetry run python -m telegram_bot

# Start bet manager
_start bet_manager env ENVIRONMENT=production poetry run python -m bet_manager

# Start deposit monitor (Django command; needs PYTHONPATH so webapp is importable from repo root)
_start deposit_monitor env ENVIRONMENT=production PYTHONPATH="$ROOT" poetry run python webapp/manage.py monitor_deposits --interval 60

echo ""
echo "Widepiper (no Docker) is up. Processes:"
echo "  webapp:  http://127.0.0.1:8000"
echo "  logs:    $ROOT/logs/"
echo "  PIDs:    $PIDDIR/"
echo ""
echo "To stop: ./scripts/stop-prod-no-docker.sh"
echo "To serve tg.ma8ka.com with HTTPS, use nginx + certbot (see DEPLOY_TG_MA8KA_NO_DOCKER.md)."
