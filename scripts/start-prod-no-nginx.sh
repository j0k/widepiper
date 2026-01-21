#!/usr/bin/env sh

set -e

mkdir -p ./db
mkdir -p ./staticfiles
touch ./bet_manager.log
touch ./next_block_sync.txt
touch ./db/db.sqlite3
chmod a+rw ./bet_manager.log
chmod a+rw ./next_block_sync.txt
chmod -R a+rw ./db

docker compose -f docker-compose.prod-no-nginx.yml up -d --build
docker compose -f docker-compose.prod-no-nginx.yml exec -u 0 webapp poetry run python manage.py collectstatic --no-input
docker compose -f docker-compose.prod-no-nginx.yml exec webapp poetry run python manage.py migrate --no-input
