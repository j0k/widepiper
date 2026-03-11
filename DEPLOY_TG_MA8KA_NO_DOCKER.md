# Деплой на tg.ma8ka.com без Docker

Перед запуском убедитесь, что DNS A-запись для `tg.ma8ka.com` указывает на IP сервера.

## 1. Зависимости на сервере

- Python 3.10+
- [Poetry](https://python-poetry.org/)
- Nginx (для HTTPS и прокси)
- Certbot (для Let's Encrypt)

Установка зависимостей проекта (один раз):

```bash
cd /path/to/widepiper
poetry install
```

## 2. Конфигурация

```bash
cp .env.example .env
# Заполните .env: TELEGRAM_BOT_TOKEN, SECRET_KEY, WEBAPP_URL=https://tg.ma8ka.com, API-ключи, кошельки
```

## 3. Запуск приложения (без Nginx/HTTPS)

```bash
./scripts/start-prod-no-docker.sh
```

Будут запущены в фоне:

- **webapp** — Gunicorn на `127.0.0.1:8000`
- **telegram_bot** — бот Telegram
- **bet_manager** — менеджер ставок
- **deposit_monitor** — мониторинг депозитов

Логи: `./logs/`. Остановка: `./scripts/stop-prod-no-docker.sh`.

Проверка локально: `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/` (ожидается 200 или 302).

## 4. Nginx и статика

Создайте каталог для certbot (если будете использовать Let's Encrypt):

```bash
sudo mkdir -p /var/www/certbot
```

Скопируйте конфиг Nginx и подставьте путь к репозиторию:

```bash
sudo cp proxy/nginx/conf_prod/nginx-no-docker.conf /etc/nginx/sites-available/widepiper
# Замените в файле /var/www/widepiper на полный путь к репо, например /home/user/space/widepiper
sudo sed -i "s|/var/www/widepiper|$(pwd)|g" /etc/nginx/sites-available/widepiper
sudo ln -sf /etc/nginx/sites-available/widepiper /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

Сайт будет доступен по **http://tg.ma8ka.com**.

## 5. HTTPS (Let's Encrypt)

Получите сертификат (Nginx уже должен быть настроен и слушать 80 порт):

```bash
sudo certbot certonly --webroot -w /var/www/certbot -d tg.ma8ka.com
```

Подключите SSL-конфиг:

```bash
REPO="$(pwd)"
sudo cp proxy/nginx/conf_prod/nginx-no-docker-ssl.conf /etc/nginx/sites-available/widepiper-ssl
sudo sed -i "s|/var/www/widepiper|$REPO|g" /etc/nginx/sites-available/widepiper-ssl
sudo rm -f /etc/nginx/sites-enabled/widepiper
sudo ln -sf /etc/nginx/sites-available/widepiper-ssl /etc/nginx/sites-enabled/widepiper
sudo nginx -t && sudo systemctl reload nginx
```

После этого сайт доступен по **https://tg.ma8ka.com**.

## 6. Продление сертификата

```bash
sudo certbot renew
sudo systemctl reload nginx
```

Или настройте cron: `0 3 1 * * certbot renew && systemctl reload nginx`

## 7. Запуск через systemd (опционально)

Чтобы приложение поднималось после перезагрузки, можно завести юниты для каждого процесса (webapp, telegram_bot, bet_manager, deposit_monitor), вызывающие те же команды, что и в `scripts/start-prod-no-docker.sh`, с загрузкой `.env` и рабочим каталогом в корне репозитория.
