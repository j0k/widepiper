#!/usr/bin/env sh
# Запуск только webapp без Docker (для разработки)
# Требует: .venv и SECRET_KEY (в .env или export)

set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "Создайте venv и установите зависимости:"
  echo "  python3 -m venv .venv"
  echo "  .venv/bin/pip install django djangorestframework drf-yasg django-cors-headers requests moralis web3 eth-account base58"
  exit 1
fi

if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi
export SECRET_KEY="${SECRET_KEY:-dev-secret-key-change-in-production}"
export PYTHONPATH=./webapp

.venv/bin/python webapp/manage.py runserver "${1:-0.0.0.0:8000}"
