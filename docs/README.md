## Документация widepiper (docs/)

Это входная точка для технической документации проекта.

### Обзор файлов

- **Общее понимание проекта**
  - `UNDERSTANDING_THE_APP.md` — обзор доменной логики: блоки, ставки, депозиты, фоновые процессы.
  - `LAUNCH_ROADMAP.md` — детальный разбор механики (диаграммы, ссылки на файлы и строки кода).

- **Запуск и деплой**
  - `DEPLOY_TG_MA8KA.md` — прод-деплой на `tg.ma8ka.com` с Docker.
  - `DEPLOY_TG_MA8KA_NO_DOCKER.md` — прод-деплой без Docker (no-docker сценарий).
  - `TESTNET_LAUNCH.md` — полный план для тестового запуска на тестнетах (TRON/BSC/TON) с чек-листом.
  - `HOW_I_LAUCNCH_IT_March.md` — что именно делалось для запуска на `tg.ma8ka.com` в марте (история шагов: что/зачем/результат).

- **Безопасность и передача проекта**
  - `SECURITY_SETUP.md` — чек-лист по безопасности и настройке окружения.
  - `TRANSFER_CHECKLIST.md` — что нужно сделать новому владельцу (env, домен, SSL, БД).
  - `CLEANUP_SUMMARY.md`, `CLEANUP_COMPLETE.txt` — что было вычищено перед передачей.

> Исторические файлы (`*_SUMMARY`, инструкции на русском и т.п.) оставлены в корне ради истории; для актуальной информации смотри файлы выше.

---

### Документация по фичам

- **Ставки и блоки**
  - Основной документ: `LAUNCH_ROADMAP.md`, разделы 2–4.
  - Ключевой код:
    - `webapp/core/models.py` — модели `Block`, `Bet`.
    - `webapp/core/blocks.py` — `get_current_or_create_open_block()` (строки 8–22).
    - `webapp/core/api_views.py` — `create_bet()` (примерно строки 160–240).
    - `bet_manager/__main__.py` — `determine_winning_and_loosing_bets()`, `process_winning_bets()`, `main()`.

- **Депозиты**
  - Основной документ: `LAUNCH_ROADMAP.md`, раздел 5.
  - Ключевой код:
    - `webapp/core/deposit_monitor.py` — `DepositMonitor.run()`, `credit_deposit()`, `auto_credit_confirmed_deposits()`.
    - `webapp/core/management/commands/monitor_deposits.py` — команда `monitor_deposits`.
    - `webapp/core/models.py` — `DepositTransaction`.

- **Вывод средств**
  - Документация: `LAUNCH_ROADMAP.md`, раздел 6.
  - Ключевой код:
    - `webapp/core/api_views.py` — `withdraw()` (примерно строки 650–750).
    - `webapp/core/withdrawal.py` — `send_usdt_trc20`, `send_usdt_bsc`, `send_usdt_ton`.

- **Игры и `game_earn`**
  - Документация: `LAUNCH_ROADMAP.md`, раздел 7.
  - Ключевой код:
    - `webapp/core/api_views.py` — `game_earn()` (примерно строки 1070–1125).
    - `webapp/core/static/scripts/flappy-bird.js` — логика игры и вызов `/api/v1/games/earn/`.

- **Telegram Mini App**
  - Обзор: `UNDERSTANDING_THE_APP.md`, разделы Components и Request flow.
  - Ключевой код:
    - `telegram_bot/handlers.py` — `start_command`, `app_command`, `standart_webapp_response()`.
    - `.env` → `WEBAPP_URL` — URL, который открывается из Mini App.

---

### Как читать ссылки на код

Во всех доках мы придерживаемся формата:

- **Файл:** `webapp/core/api_views.py`
- **Функция:** `create_bet()`
- **Строки:** «примерно 160–240» (чтобы не ломать ссылки при мелких правках).

Когда нужно увидеть конкретную реализацию:

1. Открой файл по указанному пути.
2. Найди функцию/класс по имени.
3. Используй номера строк как ориентир (могут немного сдвигаться).

