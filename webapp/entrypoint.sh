#!/usr/bin/env sh

# Если передана команда (например, monitor_deposits), выполняем её
if [ $# -gt 0 ]; then
    echo "Running custom command: $@"
    exec poetry run "$@"
fi

# Иначе запускаем стандартный режим
if [ "$ENVIRONMENT" = "production" ]; then
    echo "Running in production mode"
    exec poetry run gunicorn -c gunicorn.conf.py webapp.wsgi
elif [ "$ENVIRONMENT" = "development" ]; then
    echo "Running in development mode"
    exec poetry run python manage.py runserver 0.0.0.0:8000
else
    echo "ENVIRONMENT variable is not set"
fi
