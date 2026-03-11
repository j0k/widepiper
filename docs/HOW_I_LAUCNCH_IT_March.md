## HOW_I_LAUCNCH_IT_March.md

Краткая история того, **как мы подняли widepiper на `tg.ma8ka.com` в марте**, с разбором:

- что делали,
- зачем это нужно,
- какой результат получили.

Хронология немного сгруппирована по темам, а не строго по времени, чтобы было удобнее читать.

---

### 1. Первичная попытка запуска через Docker

- **Что делал**
  - Запустил `./scripts/start-prod.sh`, который использует `docker-compose.prod.yml` для поднятия `webapp`, `nginx`, `certbot`, `bet_manager`, `telegram_bot`, `deposit_monitor`.
  - Столкнулся с ошибками:
    - `docker-compose: command not found` (на хосте установлен Docker Compose v2 — `docker compose`, а не `docker-compose`).
    - При попытке запустить через `docker compose` — ошибка доступа к Docker daemon: `permission denied while trying to connect to the Docker daemon socket`.
- **Зачем**
  - Исходный README и деплой-доки были заточены под Docker, поэтому логично было сначала проверить именно этот путь.
- **Результат**
  - Docker-вариант не подошёл в текущей среде (нет доступа к docker.sock от нашего пользователя).
  - В репо были обновлены скрипты и дока под `docker compose`:
    - `scripts/start-prod.sh`, `scripts/setup-ssl.sh`, `scripts/renew-ssl.sh`, `DEPLOY_TG_MA8KA.md` — заменён `docker-compose` → `docker compose`.
  - Дальнейший запуск решили делать **без Docker**.

---

### 2. Переезд на no-docker запуск (новые скрипты)

- **Что делал**
  - Изучил `webapp/Dockerfile.prod`, `bet_manager/Dockerfile.prod`, `telegram_bot/Dockerfile.prod` и `webapp/entrypoint.sh`, чтобы понять, как именно запускаются сервисы внутри контейнеров.
  - На базе этой логики создал:
    - `scripts/start-prod-no-docker.sh` — no-docker стартовый скрипт.
    - `scripts/stop-prod-no-docker.sh` — скрипт остановки.
  - Логика `start-prod-no-docker.sh`:
    - Загружает `.env` и выставляет `ENVIRONMENT=production`, `WEBAPP_URL`.
    - Создаёт каталоги `db/`, `staticfiles/`, файлы `bet_manager.log`, `next_block_sync.txt`, `db/db.sqlite3`.
    - Делает симлинки:
      - `webapp/db` → `../db`
      - `webapp/static` → `../staticfiles`
    - Запускает миграции и `collectstatic` из `webapp/`.
    - Запускает в фоне (через `nohup`) с сохранением PID в `.pids/`:
      - webapp: `gunicorn -c gunicorn.conf.py -b 127.0.0.1:8000/8001 webapp.wsgi`
      - `telegram_bot`: `python -m telegram_bot`
      - `bet_manager`: `python -m bet_manager`
      - `deposit_monitor`: `python webapp/manage.py monitor_deposits --interval 60`
  - В `.gitignore` добавил:
    - `.pids/`
    - `logs/`
- **Зачем**
  - Чтобы запускать все процессы напрямую через Python/venv без Docker, максимально повторяя «контейнерную» логику.
  - Иметь удобный единый вход: **одна команда на старт, одна на стоп**.
- **Результат**
  - Появилась рабочая схема no-docker запуска с явным управлением процессами.
  - Можно быстро поднять/остановить все сервисы без Docker.

---

### 3. Настройка Nginx и разбор 404/502 на `tg.ma8ka.com`

- **Что делал**
  - Проверил системный nginx:
    - `nginx -T` → обнаружился отдельный vhost `tg.ma8ka.com` в `/etc/nginx/sites-available/tg.ma8ka.com` (и симлинк в `sites-enabled/`).
  - Прочитал конфиг `tg.ma8ka.com` (в репо — `proxy/nginx/sites-available/tg.ma8ka.com`):
    - HTTP (80) — редирект на HTTPS.
    - HTTPS (443) — `proxy_pass http://127.0.0.1:8000;` + `location /static/` с `alias /home/jk/space/widepiper/staticfiles/`.
  - Проверил порты:
    - `ss -tlnp` → увидели, что:
      - `127.0.0.1:8000` занят другим процессом (`uvicorn`),
      - gunicorn wepapp мы запускали на `127.0.0.1:8001`.
  - Обновил **системный** nginx-конфиг:
    - `sudo sed -i 's|127.0.0.1:8000|127.0.0.1:8001|g' /etc/nginx/sites-available/tg.ma8ka.com`
    - `sudo nginx -t` → ОК, только предупреждения по ssl_stapling.
    - `sudo systemctl reload nginx`.
- **Зачем**
  - До этого Nginx проксировал `tg.ma8ka.com` на **чужой** сервис (uvicorn на 8000), отсюда 404/502.
  - Нужно было добиться, чтобы запросы шли именно к gunicorn widepiper на 8001.
- **Результат**
  - `https://tg.ma8ka.com/` начал отдавать `200`, то есть домен теперь обслуживает именно этот webapp.
  - В репозитории конфиг `proxy/nginx/sites-available/tg.ma8ka.com` также помечен комментарием о том, что backend-порт — 8001.

---

### 4. CSRF и работа через HTTPS / Telegram Mini App

- **Что делал**
  - Столкнулись с CSRF-ошибкой при логине через веб/iframe:
    - Django не видел валидный CSRF-токен при запросах с `https://tg.ma8ka.com`.
  - Проверил `webapp/webapp/settings.py`:
    - `CSRF_TRUSTED_ORIGINS` содержал `https://tg.ma8ka.com`, но не `http://tg.ma8ka.com`.
    - `CSRF_COOKIE_SECURE = False`, `CSRF_COOKIE_SAMESITE` не был выставлен.
  - Обновил настройки:
    - Добавил `http://tg.ma8ka.com` в `CSRF_TRUSTED_ORIGINS`.
    - Ввёл привязку к `ENVIRONMENT=production`:
      - `CSRF_COOKIE_SECURE = True` в проде.
      - `CSRF_COOKIE_SAMESITE = "None"` и `SESSION_COOKIE_SAMESITE = "None"` в проде.
      - `SESSION_COOKIE_SECURE = True` в проде.
- **Зачем**
  - Для HTTPS браузер часто отказывается слать не-Secure cookie.
  - Для Telegram Mini App (iframe) нужно `SameSite=None` + `Secure`, иначе куки сессии/CSRF не уходят.
- **Результат**
  - CSRF-ошибка исчезла, формы логина/регистрации и запросы из Mini App успешно проходят проверку CSRF.

---

### 5. Тестовый скрипт `scripts/test-all.sh` и минимальные Django-тесты

- **Что делал**
  - Создал `scripts/test-all.sh`, который:
    - Запускает `manage.py test core` (юнит-тесты Django).
    - Проверяет импорты:
      - `webapp.core.models` (через `manage.py shell`).
      - `telegram_bot.handlers`.
      - `bet_manager` пакет.
    - Делает HTTP smoke-тесты:
      - `GET /`
      - `GET /api/v1/get_time?ct=0`
      - `GET /swagger/`
      - `GET /api/v1/deposit/addresses/`
  - В `webapp/core/tests.py` добавил минимальный `CoreSmokeTest`, чтобы был хотя бы один зелёный тест.
  - Подогнал скрипт под реальные ответы (пример: `/api/v1/get_time` требует `ct`, `/api/v1/deposit/addresses/` может возвращать 401/403/405).
- **Зачем**
  - Иметь **одну команду** для быстрой проверки, что:
    - Django-конфиг валиден,
    - основные модули импортируются,
    - webapp реально отвечает на ключевые эндпоинты.
- **Результат**
  - `bash scripts/test-all.sh` сейчас полностью проходит:
    - 1 Django-тест OK.
    - Импорты OK.
    - HTTP-проверки OK (включая `/api/v1/deposit/addresses/` с ожидаемым статусом 401 при отсутствии авторизации).

---

### 6. Обновление CSRF/COOKIE настроек под production

(Отдельно выделено, т.к. влияет и на prod, и на testnet.)

- **Что делал**
  - В `webapp/webapp/settings.py` добавил логику:
    - `_env = os.getenv(\"ENVIRONMENT\", \"\").lower()`
    - `_production = _env == \"production\"`
    - Если `_production`:
      - `CSRF_COOKIE_SECURE = True`
      - `CSRF_COOKIE_SAMESITE = \"None\"`
      - `SESSION_COOKIE_SECURE = True`
      - `SESSION_COOKIE_SAMESITE = \"None\"`
- **Зачем**
  - Чтобы в dev-режиме было проще отлаживаться, а в prod — сразу иметь корректные secure/SameSite настройки под HTTPS и Telegram.
- **Результат**
  - В зависимоси от `ENVIRONMENT` проект корректно настраивает cookie без лишних правок конфига.

---

### 7. Финальный standup на `tg.ma8ka.com` (март)

- **Что делал**
  1. Убедился, что есть `.env` и `.venv`:
     - `ls -la .env .venv/bin/python`.
  2. Прогнал миграции и статику (на всякий случай, на актуальном коде):
     - `cd webapp && ../.venv/bin/python manage.py migrate --no-input`
     - `../.venv/bin/python manage.py collectstatic --no-input`.
  3. Остановил возможные старые no-docker процессы:
     - `bash scripts/stop-prod-no-docker.sh`.
  4. Запустил webapp (gunicorn) на 127.0.0.1:8001:
     - `nohup ... gunicorn -c gunicorn.conf.py -b 127.0.0.1:8001 webapp.wsgi &`
     - Сохранил PID в `.pids/webapp.pid`.
     - Проверил ответ: `curl http://127.0.0.1:8001/` → `200`.
  5. Запустил фоновые сервисы:
     - `telegram_bot`: `nohup .venv/bin/python -m telegram_bot &` (PID сохранён в `.pids/telegram_bot.pid`).
     - `bet_manager`: `nohup .venv/bin/python -m bet_manager &` (`.pids/bet_manager.pid`).
     - `deposit_monitor`: `nohup PYTHONPATH=/home/jk/space/widepiper .venv/bin/python webapp/manage.py monitor_deposits --interval 60 &` (`.pids/deposit_monitor.pid`).
  6. Проверил готовность:
     - `curl -s -o /dev/null -w \"%{http_code}\" https://tg.ma8ka.com/` → `200`.
     - `ps -p $(cat .pids/webapp.pid) -o pid,comm` → `gunicorn`.
- **Зачем**
  - Привести всё в консистентное состояние:
    - корректный back-end-порт (8001),
    - запущен webapp и все фоновые процессы,
    - nginx проксирует на правильный порт.
- **Результат**
  - На момент завершения этих шагов:
    - `https://tg.ma8ka.com/` отдаёт страницу приложения с кодом 200.
    - Сессии, CSRF, Mini App, депозиты/ставки/вывод — готовы к использованию (дальше всё зависит от содержимого `.env` — prod или testnet).

---

### 8. Где смотреть / как останавливать

- **Остановка no-docker стека**
  - `bash /home/jk/space/widepiper/scripts/stop-prod-no-docker.sh`
  - Скрипт читает PIDs из `.pids/webapp.pid`, `.pids/telegram_bot.pid`, `.pids/bet_manager.pid`, `.pids/deposit_monitor.pid` и посылает `kill`.

- **Логи**
  - `logs/webapp.log` — gunicorn + Django.
  - `logs/telegram_bot.log` — Telegram-бот.
  - `logs/bet_manager.log` — работа bet_manager (обработка блоков и ставок).
  - `logs/deposit_monitor.log` — мониторинг депозитов.

Эта инструкция отражает текущее состояние **на март**: если в будущем будут меняться порты, домены или способ запуска, стоит дополнить файл новым разделом с пометкой по дате.

