# Widepiper (Liquidity)

Веб‑приложение для **ставок на ценовое соотношение токенов IDEA/MATTER** на BSC с веб‑интерфейсом, Telegram Mini App, депозитами и выводами USDT в нескольких сетях.

**Демо:** [https://tg.ma8ka.com](https://tg.ma8ka.com)

---

## Содержание

- [О проекте](#о-проекте)
- [Функционал](#функционал)
- [Стек и зависимости](#стек-и-зависимости)
- [Структура репозитория](#структура-репозитория)
- [Быстрый старт](#быстрый-старт)
- [Запуск через Docker](#запуск-через-docker)
- [Переменные окружения](#переменные-окружения)
- [Скрипты](#скрипты)
- [API](#api)
- [Тестирование](#тестирование)
- [Документация](#документация)

---

## О проекте

Widepiper (в коде и старых доках — **Liquidity**) — это:

- **Ставки на ratio IDEA/MATTER**  
  Пользователи делают ставки на то, как изменится соотношение цен двух токенов на BSC к концу «блока» (временного окна ~10 минут). Победители определяются по близости прогноза к фактическому ratio; выигрыш начисляется на внутренний баланс (USDT).

- **Единый веб‑интерфейс**  
  Доступ и через браузер, и через **Telegram Mini App**: один и тот же Django‑бэкенд, разный вход (сайт или кнопка в боте).

- **Депозиты и выводы**  
  Приём USDT по сетям TRC‑20 (TRON), BEP‑20 (BSC), TON; вывод на указанный пользователем адрес. Всё через фоновый мониторинг и кошельки приложения.

- **Фоновые процессы**  
  Отдельные процессы: **bet_manager** (расчёт блоков и победителей), **deposit_monitor** (сканирование входящих переводов и зачисление на баланс).

Подробная механика — в [UNDERSTANDING_THE_APP.md](UNDERSTANDING_THE_APP.md) и [LAUNCH_ROADMAP.md](LAUNCH_ROADMAP.md).

---

## Функционал

| Область | Описание | Где искать в коде / доке |
|--------|----------|---------------------------|
| **Регистрация и авторизация** | Логин/логаут, сессии, привязка кошельков (BSC, TON) | [webapp/core/views.py](webapp/core/views.py), [webapp/core/api_views.py](webapp/core/api_views.py); [docs/README.md](docs/README.md) |
| **Ставки (bets)** | Создание/удаление ставки, расчёт bet_ratio, списание с внутреннего баланса | [webapp/core/api_views.py](webapp/core/api_views.py) (`create_bet`, `remove_bet`), [webapp/core/blocks.py](webapp/core/blocks.py); [LAUNCH_ROADMAP.md](LAUNCH_ROADMAP.md) §3–4 |
| **Блоки и определение победителей** | Цикл каждые 10 мин: заморозка блока, расчёт победителей, начисление выигрыша | [bet_manager/__main__.py](bet_manager/__main__.py); [LAUNCH_ROADMAP.md](LAUNCH_ROADMAP.md) §2, §4 |
| **Депозиты** | Мониторинг TRC20/BSC/TON, подтверждения, зачисление на `usdt_balance` | [webapp/core/deposit_monitor.py](webapp/core/deposit_monitor.py), [webapp/core/management/commands/monitor_deposits.py](webapp/core/management/commands/monitor_deposits.py); [LAUNCH_ROADMAP.md](LAUNCH_ROADMAP.md) §5 |
| **Вывод (withdraw)** | Отправка USDT на адрес пользователя (TRC20/BSC/TON) | [webapp/core/api_views.py](webapp/core/api_views.py) (`withdraw`), [webapp/core/withdrawal.py](webapp/core/withdrawal.py); [LAUNCH_ROADMAP.md](LAUNCH_ROADMAP.md) §6 |
| **Игры (Flappy Bird)** | Мини‑игра, начисление до 10 USDT за сессию на баланс | [webapp/core/api_views.py](webapp/core/api_views.py) (`game_earn`), [webapp/core/static/scripts/flappy-bird.js](webapp/core/static/scripts/flappy-bird.js); [LAUNCH_ROADMAP.md](LAUNCH_ROADMAP.md) §7 |
| **WalletConnect** | Подключение внешнего кошелька для веб‑интерфейса | [webapp/core/api_views.py](webapp/core/api_views.py) (wallet/*), [webapp/core/static/scripts/walletconnect.js](webapp/core/static/scripts/walletconnect.js) |
| **Telegram бот** | Кнопка «Приложение» и открытие Mini App по `WEBAPP_URL` | [telegram_bot/handlers.py](telegram_bot/handlers.py); [UNDERSTANDING_THE_APP.md](UNDERSTANDING_THE_APP.md) |

---

## Стек и зависимости

- **Backend:** Django 5.x, Django REST Framework, Gunicorn (прод)
- **БД:** SQLite (файл в `webapp/db/` или симлинк из корня `db/`)
- **Блокчейны / API:** BSC (Web3, Moralis, BscScan), TRON (TronGrid), TON (pytoniq, pytonlib)
- **Фронт:** HTML/JS/CSS, Swagger/ReDoc для API
- **Инфра:** Nginx (reverse proxy, SSL), опционально Docker / Docker Compose

Зависимости задаются в [pyproject.toml](pyproject.toml) (Poetry); для быстрого запуска без Poetry можно использовать собранное окружение `.venv`.

---

## Структура репозитория

```text
widepiper/
├── webapp/                          # Django-проект (основной backend и фронт)
│   ├── webapp/                      # Настройки проекта (settings, urls, wsgi)
│   ├── core/                        # Основное приложение
│   │   ├── models.py                # UserProfile, Bet, Block, Transaction, DepositTransaction
│   │   ├── views.py                 # Страницы: логин, ставки, профиль, вывод и т.д.
│   │   ├── api_views.py             # REST API: ставки, профиль, депозиты, вывод, игры, wallet
│   │   ├── urls.py                  # Маршруты страниц и API
│   │   ├── blocks.py                # Логика блоков (get_current_or_create_open_block)
│   │   ├── deposit_monitor.py      # Класс мониторинга депозитов (TRC20/BSC/TON)
│   │   ├── withdrawal.py            # Отправка USDT (TRC20/BSC/TON)
│   │   ├── dex/                     # DEX (PancakeSwap): цены, ликвидность
│   │   ├── wallet/                  # Кошельки BSC/TON, балансы, отправка токенов
│   │   ├── templates/               # HTML-шаблоны
│   │   └── static/                  # JS, CSS (WalletConnect, игры, часы)
│   └── manage.py
│
├── telegram_bot/                    # Telegram-бот (только открытие Mini App)
│   ├── handlers.py                  # /start, /app, кнопка меню → WEBAPP_URL
│   └── __main__.py                  # Точка входа
│
├── bet_manager/                      # Фоновый процесс: блоки и начисление выигрышей
│   └── __main__.py                  # Цикл каждые 10 мин, вызов core.models/blocks/wallet
│
├── proxy/nginx/                     # Конфиги Nginx
│   ├── conf_prod/                   # Прод (Docker и no-docker)
│   └── sites-available/             # Пример vhost для tg.ma8ka.com
│
├── scripts/                          # Скрипты запуска, деплоя и проверок
│   ├── start-prod-no-docker.sh      # Запуск всего стека без Docker
│   ├── stop-prod-no-docker.sh      # Остановка no-docker процессов
│   ├── start-prod.sh                # Запуск прод через Docker Compose
│   ├── setup-ssl.sh                # Certbot (Let's Encrypt)
│   ├── renew-ssl.sh                # Продление сертификатов
│   ├── test-all.sh                 # Django-тесты + импорты + HTTP smoke
│   └── ...
│
├── docs/                             # Документация
│   ├── README.md                    # Индекс документации и ссылки на код по фичам
│   └── HOW_I_LAUCNCH_IT_March.md   # История запуска на tg.ma8ka.com
│
├── .env.example                     # Шаблон переменных окружения (прод)
├── .env.testnet.example             # Шаблон для тестнета
├── pyproject.toml / poetry.lock     # Зависимости (Poetry)
├── docker-compose.prod.yml          # Прод с nginx и certbot
├── docker-compose.dev.yml           # Разработка
└── README.md                        # Этот файл
```

Краткая «карта» по фичам и файлам — в [docs/README.md](docs/README.md).

---

## Быстрый старт

### Требования

- Python 3.10+
- Установленные зависимости (через Poetry: `poetry install`, либо уже собранный `.venv`)
- Заполненный [.env](.env.example) (скопировать из `.env.example`)

### Запуск без Docker (рекомендуется для одного сервера)

1. **Настроить окружение**

   ```bash
   cp .env.example .env
   # Отредактировать .env: SECRET_KEY, WEBAPP_URL, TELEGRAM_BOT_TOKEN, кошельки, API-ключи
   ```

2. **Запустить все сервисы**

   ```bash
   bash scripts/start-prod-no-docker.sh
   ```

   Скрипт создаёт каталоги `db/`, `staticfiles/`, применяет миграции и collectstatic, запускает в фоне:

   - **Webapp** (Gunicorn) на `127.0.0.1:8001`
   - **Telegram-бот**
   - **Bet manager** (цикл каждые 10 мин)
   - **Deposit monitor** (проверка депозитов каждые 60 сек)

3. **Проверить**

   ```bash
   curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8001/
   # Ожидается 200 или 302
   ```

4. **Остановить**

   ```bash
   bash scripts/stop-prod-no-docker.sh
   ```

Подробнее: [DEPLOY_TG_MA8KA_NO_DOCKER.md](DEPLOY_TG_MA8KA_NO_DOCKER.md).

---

## Запуск через Docker

- **Прод (с nginx и certbot):** [DEPLOY_TG_MA8KA.md](DEPLOY_TG_MA8KA.md)  
  Команды: `./scripts/start-prod.sh`, `./scripts/setup-ssl.sh`, `./scripts/renew-ssl.sh`

- **Разработка:**  
  `./scripts/start-dev.sh`  
  Создание суперпользователя:  
  `docker compose -f ./docker-compose.dev.yml exec webapp poetry run python manage.py createsuperuser`

---

## Переменные окружения

Все настройки берутся из файла **`.env`** в корне проекта. Шаблоны:

- **[.env.example](.env.example)** — прод: секреты, домен, кошельки, API (Moralis, Infura, BscScan, TON, WalletConnect), адреса токенов и роутеров, депозитные адреса и ключи вывода.
- **[.env.testnet.example](.env.testnet.example)** — тестнет: депозитные адреса и ключи для TRON/BSC/TON testnet.

Минимально важные переменные:

| Переменная | Назначение |
|------------|------------|
| `SECRET_KEY` | Django secret key |
| `WEBAPP_URL` | URL приложения (например `https://tg.ma8ka.com/`) |
| `TELEGRAM_BOT_TOKEN` | Токен бота от @BotFather |
| `MATTER_TOKEN_ADDRESS`, `IDEA_TOKEN_ADDRESS` | Адреса токенов на BSC |
| `APP_WALLET`, `APP_WALLET_PRIVATE_KEY` | Кошелёк приложения (BSC) |
| `DEPOSIT_ADDRESS_*`, `*_PRIVATE_KEY` | Адреса и ключи для приёма депозитов (TRC20/BSC/TON) |
| `MORALIS_API_KEY`, `BSC_API_KEY`, `INFURA_API_KEY`, `BSC_RPC_URL` | Цены и RPC |
| Ключи вывода (TRON/BSC/TON) | Для отправки USDT при withdraw |

Подробности и безопасность: [SECURITY_SETUP.md](SECURITY_SETUP.md).

---

## Скрипты

| Скрипт | Назначение |
|--------|------------|
| [scripts/start-prod-no-docker.sh](scripts/start-prod-no-docker.sh) | Запуск стека без Docker (webapp, bot, bet_manager, deposit_monitor) |
| [scripts/stop-prod-no-docker.sh](scripts/stop-prod-no-docker.sh) | Остановка процессов, запущенных start-prod-no-docker |
| [scripts/start-prod.sh](scripts/start-prod.sh) | Запуск прод через Docker Compose |
| [scripts/setup-ssl.sh](scripts/setup-ssl.sh) | Получение сертификатов Let's Encrypt (certbot) |
| [scripts/renew-ssl.sh](scripts/renew-ssl.sh) | Продление сертификатов |
| [scripts/start-dev.sh](scripts/start-dev.sh) | Запуск dev-окружения (Docker) |
| [scripts/test-all.sh](scripts/test-all.sh) | Django-тесты, проверка импортов, HTTP smoke по `BASE_URL` |
| [run-webapp.sh](run-webapp.sh) | Локальный запуск только webapp (для разработки) |

---

## API

REST API версии **v1** описан в коде и доступен через Swagger/ReDoc при запущенном приложении:

- **Swagger UI:** `/swagger/`
- **ReDoc:** `/redoc/`

Основные группы эндпоинтов (маршруты в [webapp/core/urls.py](webapp/core/urls.py)):

- **Время и блоки:** `GET /api/v1/get_time`, `GET /api/v1/get_next_bet_sync_time`, `GET /api/v1/block/timer/`
- **Авторизация:** `POST /api/v1/login/`, `POST /api/v1/logout/`, `POST /api/v1/register/`
- **Ставки:** `GET /api/v1/bets/`, `POST /api/v1/bet/create/`, `POST /api/v1/bet/remove/`
- **Профиль и кошельки:** `GET /api/v1/profile/`, `POST /api/v1/profile/save_wallet/`, `POST /api/v1/profile/save_ton_wallet/`
- **Вывод:** `POST /api/v1/withdraw/`
- **Депозиты:** `GET /api/v1/deposit/addresses/`, `GET /api/v1/deposit/history/`, `GET /api/v1/deposit/pending/`
- **WalletConnect:** `POST /api/v1/wallet/auth_challenge/`, `POST /api/v1/wallet/connect/`, и др.
- **Игры:** `POST /api/v1/games/earn/`

---

## Тестирование

- **Локальные проверки (Django + импорты + HTTP):**  
  ```bash
  bash scripts/test-all.sh
  ```  
  Опционально: `BASE_URL=https://tg.ma8ka.com bash scripts/test-all.sh` для проверки живого сайта.

- **Тестнет:** полный план и чек-лист — в [TESTNET_LAUNCH.md](TESTNET_LAUNCH.md) (кошельки, краны, настройка `.env`, сценарии депозитов/ставок/вывода/игр/Mini App).

---

## Документация

| Документ | Содержание |
|----------|------------|
| [UNDERSTANDING_THE_APP.md](UNDERSTANDING_THE_APP.md) | Обзор приложения: блоки, ставки, депозиты, компоненты, где искать код |
| [LAUNCH_ROADMAP.md](LAUNCH_ROADMAP.md) | Детальная механика с диаграммами и ссылками на файлы/строки |
| [docs/README.md](docs/README.md) | Индекс всей документации и привязка фич к коду |
| [DEPLOY_TG_MA8KA.md](DEPLOY_TG_MA8KA.md) | Прод-деплой на tg.ma8ka.com с Docker и SSL |
| [DEPLOY_TG_MA8KA_NO_DOCKER.md](DEPLOY_TG_MA8KA_NO_DOCKER.md) | Прод-деплой без Docker |
| [TESTNET_LAUNCH.md](TESTNET_LAUNCH.md) | Запуск на тестнете (TRON/BSC/TON), чек-лист |
| [docs/HOW_I_LAUCNCH_IT_March.md](docs/HOW_I_LAUCNCH_IT_March.md) | Что делали для запуска на tg.ma8ka.com (шаги, результат) |
| [SECURITY_SETUP.md](SECURITY_SETUP.md) | Безопасность и настройка окружения |
| [TRANSFER_CHECKLIST.md](TRANSFER_CHECKLIST.md) | Чек-лист для нового владельца проекта |
| [ИНСТРУКЦИЯ_ДЛЯ_НОВОГО_ВЛАДЕЛЬЦА.md](ИНСТРУКЦИЯ_ДЛЯ_НОВОГО_ВЛАДЕЛЬЦА.md) | Инструкция для нового владельца (историческая) |

---

*Репозиторий: [github.com/j0k/widepiper](https://github.com/j0k/widepiper).*
