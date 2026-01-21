#!/usr/bin/env sh

set -e

touch ./bet_manager.log
touch ./next_block_sync.txt

docker-compose -f docker-compose.dev.yml up -d --build
docker-compose -f docker-compose.dev.yml exec webapp poetry run python manage.py collectstatic --no-input
docker-compose -f docker-compose.dev.yml exec webapp mkdir -p ./db
docker-compose -f docker-compose.dev.yml exec webapp poetry run python manage.py migrate --no-input
