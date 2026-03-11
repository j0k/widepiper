# How to understand this app (Widepiper / Liquidity)

## What it is

A **crypto prediction / betting web app** tied to a **Telegram bot**:

- Users bet on the **IDEA/MATTER token price ratio** on BSC (Binance Smart Chain).
- Time is split into **blocks** (~10 minutes). Each block: users place bets → block **freezes** → winners/losers are decided by the final ratio → payouts in MATTER.
- Users can **deposit** USDT (TRC-20, BEP-20, TON, Bybit) and **withdraw**.
- The app is reachable from the **web** and as a **Telegram Mini App** (same Django app, different entry: browser vs Telegram iframe).

Repo name in code/docs is sometimes **liquidity**; domain we use is **tg.ma8ka.com**.

---

## Main concepts

| Concept | Where | Meaning |
|--------|--------|--------|
| **Block** | `core.models.Block`, `core/blocks.py` | A time window (OPEN → FREEZED → CLOSED). One “round” of betting. |
| **Bet** | `core.models.Bet` | User’s prediction: size, percent, and **bet_ratio** (IDEA/MATTER at bet time). Winner = whose ratio is closest to the **final** ratio when the block freezes. |
| **MATTER / IDEA** | BSC tokens | Token addresses in `.env` and `core/const.py`. Prices from DEX (PancakeSwap); ratio drives who wins. |
| **UserProfile** | `core.models.UserProfile` | Per-user: BSC wallet, TON wallet, **usdt_balance** (in-app balance from deposits). |
| **Deposit** | `core.models.DepositTransaction`, `core/deposit_monitor.py` | On-chain deposit (TRC20/BSC/TON/Bybit) → detected by **deposit_monitor** → credited to `UserProfile.usdt_balance`. |
| **Transaction** | `core.models.Transaction` | Internal withdrawal/deposit record linked to a Block and optionally a Bet. |

---

## Components (what runs)

| Component | Role | Where to look |
|-----------|------|----------------|
| **Webapp** | Django: HTML pages + REST API. Auth, bets, profile, deposits/withdrawals, WalletConnect, games. | `webapp/` — `core/views.py`, `core/api_views.py`, `core/urls.py`, `core/models.py` |
| **Telegram bot** | Sets the “App” menu button to open the webapp URL; `/start` and `/app` open the Mini App. No game logic. | `telegram_bot/` — `handlers.py`, `__main__.py` |
| **Bet manager** | Background loop (~every 10 min): get current open **Block** → freeze it (save IDEA price) → get active **Bets** → determine winners/losers (by ratio) → send MATTER to winners, mark bets inactive. | `bet_manager/__main__.py`, uses `core.models`, `core/blocks`, `core/wallet`, `core/dex` |
| **Deposit monitor** | Background loop: scan TRC20/BSC/TON (and optionally Bybit) for incoming transfers to app deposit addresses → create/update **DepositTransaction** → when confirmed, credit **UserProfile.usdt_balance**. | `webapp/core/management/commands/monitor_deposits.py`, `core/deposit_monitor.py` |

So: **webapp** = UI + API + DB; **telegram_bot** = entry from Telegram; **bet_manager** = settles blocks and pays MATTER; **deposit_monitor** = turns on-chain deposits into in-app balance.

---

## Request flow (high level)

1. **User opens app**  
   - Web: go to `https://tg.ma8ka.com`.  
   - Telegram: open bot → menu or “Приложение” → Mini App loads same URL.

2. **Auth**  
   - Web: login/signup in `core/views` (login, register).  
   - API / Mini App: session or WalletConnect; API routes in `core/api_views.py` and wallet endpoints in `core/urls.py`.

3. **Betting**  
   - User creates a bet (size, percent) → stored on current open **Block** (`core/blocks.get_current_or_create_open_block`).  
   - **Bet manager** runs on a timer: freezes block, computes IDEA/MATTER ratio, picks winners, sends MATTER, marks bets inactive.

4. **Money**  
   - **In**: User sends USDT (or other) to addresses from “Deposit” → **deposit_monitor** sees it → confirms → credits `UserProfile.usdt_balance`.  
   - **Out**: User requests withdrawal → app sends from its wallets (TRC20/BSC/TON) via `core/wallet` and related logic.

---

## Where to look for what

- **“Where is the bet / block logic?”**  
  `webapp/core/blocks.py`, `webapp/core/models.py` (Bet, Block), `bet_manager/__main__.py`.

- **“Where are pages and API routes?”**  
  `webapp/core/urls.py`, `webapp/core/views.py`, `webapp/core/api_views.py`.

- **“Where do deposits get credited?”**  
  `webapp/core/deposit_monitor.py`, `webapp/core/management/commands/monitor_deposits.py`, and API for deposit addresses/history in `api_views.py`.

- **“Where is Telegram?”**  
  `telegram_bot/handlers.py` (only sets menu + “Open app” link to `WEBAPP_URL`).

- **“Where are token prices and payouts?”**  
  `webapp/core/dex/dex.py` (DEX prices, liquidity), `webapp/core/wallet/wallet.py` (send tokens, balances). Consts: `webapp/core/const.py` and `.env`.

- **“Where is config?”**  
  `webapp/webapp/settings.py`, `.env` (and `.env.example`).

---

## Quick map of the repo

```
webapp/                    # Django app
  webapp/                  # Project settings, urls, wsgi
  core/                    # Main app: models, views, api_views, urls, forms
    blocks.py              # Open block creation
    deposit_monitor.py     # Deposit detection and credit
    dex/                   # DEX (e.g. PancakeSwap) price/liquidity
    wallet/                # BSC/TON wallets, send, balances
    templates/             # HTML (login, bet, profile, …)
    static/                # JS/CSS (e.g. walletconnect, games)
  manage.py
telegram_bot/              # Telegram bot (menu + link to webapp)
bet_manager/               # Background: freeze blocks, settle bets, pay MATTER
proxy/nginx/               # Nginx configs (prod, no-docker, tg.ma8ka.com)
scripts/                   # start-prod*, test-all, setup-ssl, …
```

Use this file as the “map”; then open the listed files to see the actual logic.
