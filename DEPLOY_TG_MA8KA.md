# Деплой на tg.ma8ka.com и HTTPS (Let's Encrypt)

Домен **tg.ma8ka.com** уже прописан в настройках проекта. Перед запуском убедитесь, что DNS A-запись для `tg.ma8ka.com` указывает на IP вашего сервера.

## 1. Подготовка

```bash
cp .env.example .env
# Заполните .env (TELEGRAM_BOT_TOKEN, SECRET_KEY, WEBAPP_URL=https://tg.ma8ka.com, ключи API и кошельки)
```

## 2. Первый запуск (без HTTPS)

Конфиг nginx по умолчанию слушает только порт 80 (для выдачи сертификатов). Запустите проект:

```bash
./scripts/start-prod.sh
```

Проверьте, что контейнеры поднялись: `docker compose -f docker-compose.prod.yml ps`

## 3. Получение сертификатов Let's Encrypt

На том же сервере выполните:

```bash
./scripts/setup-ssl.sh
```

При успехе certbot создаст сертификаты в volume `certbot_certs`.

## 4. Включение HTTPS

Подмените конфиг nginx на вариант с SSL и перезапустите:

```bash
cp proxy/nginx/conf_prod/nginx.conf.with-ssl proxy/nginx/conf_prod/nginx.conf
./scripts/start-prod.sh
```

После этого сайт будет доступен по **https://tg.ma8ka.com**.

## 5. Продление сертификатов

Let's Encrypt выдаёт сертификаты на 3 месяца. Продление:

```bash
./scripts/renew-ssl.sh
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

Или настройте cron, например: `0 3 1 * * /path/to/widepiper/scripts/renew-ssl.sh`
