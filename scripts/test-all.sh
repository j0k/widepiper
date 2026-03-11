#!/usr/bin/env sh
# Run all tests: Django unit tests, HTTP smoke tests, module imports.
# For HTTP tests, set BASE_URL (default http://127.0.0.1:8001) or leave app stopped to skip.

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

[ -f .env ] && set -a && . ./.env && set +a
export ENVIRONMENT=production

PY="${ROOT}/.venv/bin/python"
FAILED=0

_run() {
  if "$@"; then
    echo "  OK: $*"
  else
    echo "  FAIL: $*"
    FAILED=1
  fi
}

echo "=== 1. Django tests (core) ==="
_run cd webapp && "$PY" manage.py test core --verbosity=1
cd "$ROOT"

echo ""
echo "=== 2. Module imports (Django app, telegram_bot, bet_manager) ==="
_run sh -c "cd ${ROOT}/webapp && ${PY} manage.py shell -c 'from core.models import UserProfile; print(\"  webapp.core OK\")'"
_run "$PY" -c "from telegram_bot import handlers; print('  telegram_bot OK')"
_run "$PY" -c "import bet_manager; print('  bet_manager OK')"

echo ""
BASE_URL="${BASE_URL:-http://127.0.0.1:8001}"
echo "=== 3. HTTP smoke tests (BASE_URL=$BASE_URL) ==="
if curl -s --connect-timeout 2 -o /dev/null -w "%{http_code}" "${BASE_URL}/" | grep -qE '200|302'; then
  for path in "/" "/api/v1/get_time?ct=0" "/swagger/" "/api/v1/deposit/addresses/"; do
    code=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}${path}")
    case "$path" in
      "/") ok="200|302";;
      "/api/v1/get_time"*) ok="200";;
      "/swagger/") ok="200|302";;
      "/api/v1/deposit/addresses/") ok="200|401|403|405";;
      *) ok="200";;
    esac
    if echo "$code" | grep -qE "$ok"; then
      echo "  OK: GET $path => $code"
    else
      echo "  FAIL: GET $path => $code"; FAILED=1
    fi
  done
else
  echo "  Skip (no server at $BASE_URL). Start app first or set BASE_URL=..."
fi

echo ""
if [ "$FAILED" = 1 ]; then
  echo "=== Some checks failed ==="
  exit 1
fi
echo "=== All checks passed ==="
