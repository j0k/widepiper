"""
Логгер транзакций в текстовый файл
"""
import os
from datetime import datetime
from pathlib import Path


# Путь к файлу логов
LOG_DIR = Path("/var/www/liquidity-master/logs")
LOG_FILE = LOG_DIR / "transactions.log"

# Для Docker
DOCKER_LOG_DIR = Path("/app/logs")
DOCKER_LOG_FILE = DOCKER_LOG_DIR / "transactions.log"


def get_log_file():
    """Получить путь к файлу логов"""
    # Пробуем Docker путь
    if DOCKER_LOG_DIR.exists() or str(DOCKER_LOG_DIR).startswith("/app"):
        try:
            DOCKER_LOG_DIR.mkdir(parents=True, exist_ok=True)
            return DOCKER_LOG_FILE
        except:
            pass

    # Пробуем обычный путь
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        return LOG_FILE
    except:
        pass

    # Fallback - текущая директория
    return Path("transactions.log")


def log_transaction(message: str):
    """Записать сообщение в лог"""
    try:
        log_file = get_log_file()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception as e:
        print(f"Ошибка записи в лог: {e}")


def log_wallet_added(username: str, user_id: int, wallet_address: str, old_address: str = None, wallet_type: str = "BSC/ETH"):
    """Лог добавления кошелька"""
    log_file = get_log_file()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n")
            f.write(f"{'='*70}\n")
            f.write(f"[{timestamp}] КОШЕЛЕК ДОБАВЛЕН\n")
            f.write(f"{'='*70}\n")
            f.write(f"  Пользователь: {username} (ID: {user_id})\n")
            f.write(f"  Новый адрес:  {wallet_address}\n")
            f.write(f"  Старый адрес: {old_address or 'не было'}\n")
            f.write(f"  Тип:          {wallet_type}\n")
            f.write(f"{'='*70}\n")
            f.write(f"\n")
    except Exception as e:
        print(f"Ошибка записи в лог: {e}")


def log_deposit_detected(tx_hash: str, network: str, amount, from_address: str, to_address: str, confirmations: int):
    """Лог обнаружения новой транзакции"""
    log_file = get_log_file()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n")
            f.write(f"{'='*70}\n")
            f.write(f"[{timestamp}] НОВАЯ ТРАНЗАКЦИЯ ОБНАРУЖЕНА\n")
            f.write(f"{'='*70}\n")
            f.write(f"  TX Hash:      {tx_hash}\n")
            f.write(f"  Сеть:         {network}\n")
            f.write(f"  Сумма:        {amount} USDT\n")
            f.write(f"  От кого:      {from_address}\n")
            f.write(f"  Куда (наш):   {to_address}\n")
            f.write(f"  Подтвержд.:   {confirmations}\n")
            f.write(f"  Статус:       PENDING\n")
            f.write(f"{'='*70}\n")
            f.write(f"\n")
    except Exception as e:
        print(f"Ошибка записи в лог: {e}")


def log_deposit_confirmed(tx_hash: str, network: str, amount, confirmations: int, required: int):
    """Лог подтверждения транзакции"""
    log_file = get_log_file()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n")
            f.write(f"{'='*70}\n")
            f.write(f"[{timestamp}] ТРАНЗАКЦИЯ ПОДТВЕРЖДЕНА\n")
            f.write(f"{'='*70}\n")
            f.write(f"  TX Hash:      {tx_hash}\n")
            f.write(f"  Сеть:         {network}\n")
            f.write(f"  Сумма:        {amount} USDT\n")
            f.write(f"  Подтвержд.:   {confirmations}/{required}\n")
            f.write(f"  Статус:       CONFIRMED\n")
            f.write(f"{'='*70}\n")
            f.write(f"\n")
    except Exception as e:
        print(f"Ошибка записи в лог: {e}")


def log_user_found(tx_hash: str, network: str, from_address: str, username: str, user_id: int, amount):
    """Лог нахождения пользователя"""
    log_file = get_log_file()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n")
            f.write(f"{'='*70}\n")
            f.write(f"[{timestamp}] ПОЛЬЗОВАТЕЛЬ НАЙДЕН\n")
            f.write(f"{'='*70}\n")
            f.write(f"  TX Hash:      {tx_hash}\n")
            f.write(f"  Сеть:         {network}\n")
            f.write(f"  Кошелек:      {from_address}\n")
            f.write(f"  Пользователь: {username} (ID: {user_id})\n")
            f.write(f"  Зачисляем:    {amount} USDT\n")
            f.write(f"{'='*70}\n")
            f.write(f"\n")
    except Exception as e:
        print(f"Ошибка записи в лог: {e}")


def log_user_not_found(tx_hash: str, network: str, from_address: str, amount):
    """Лог когда пользователь не найден"""
    log_file = get_log_file()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    wallet_field = "TON wallet" if network == 'TON' else "crypto_wallet_address"

    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n")
            f.write(f"{'='*70}\n")
            f.write(f"[{timestamp}] ПОЛЬЗОВАТЕЛЬ НЕ НАЙДЕН\n")
            f.write(f"{'='*70}\n")
            f.write(f"  TX Hash:      {tx_hash}\n")
            f.write(f"  Сеть:         {network}\n")
            f.write(f"  Сумма:        {amount} USDT\n")
            f.write(f"  От кого:      {from_address}\n")
            f.write(f"  Статус:       НЕ ЗАЧИСЛЕНО\n")
            f.write(f"  Причина:      Не найден пользователь с таким {wallet_field}\n")
            f.write(f"{'='*70}\n")
            f.write(f"\n")
    except Exception as e:
        print(f"Ошибка записи в лог: {e}")


def log_balance_credited(tx_hash: str, network: str, username: str, user_id: int, from_address: str, amount, old_balance, new_balance):
    """Лог зачисления на баланс"""
    log_file = get_log_file()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n")
            f.write(f"{'='*70}\n")
            f.write(f"[{timestamp}] БАЛАНС ПОПОЛНЕН\n")
            f.write(f"{'='*70}\n")
            f.write(f"  TX Hash:      {tx_hash}\n")
            f.write(f"  Сеть:         {network}\n")
            f.write(f"  Пользователь: {username} (ID: {user_id})\n")
            f.write(f"  Кошелек:      {from_address}\n")
            f.write(f"  Сумма:        +{amount} USDT\n")
            f.write(f"  Баланс БЫЛ:   {old_balance} USDT\n")
            f.write(f"  Баланс СТАЛ:  {new_balance} USDT\n")
            f.write(f"  Статус:       CREDITED\n")
            f.write(f"{'='*70}\n")
            f.write(f"\n")
    except Exception as e:
        print(f"Ошибка записи в лог: {e}")


def log_monitor_start():
    """Лог начала проверки"""
    log_file = get_log_file()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n")
            f.write(f"[{timestamp}] ========== ПРОВЕРКА ДЕПОЗИТОВ НАЧАТА ==========\n")
    except Exception as e:
        print(f"Ошибка записи в лог: {e}")


def log_monitor_network(network: str, address: str, found_count: int):
    """Лог проверки сети"""
    log_file = get_log_file()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {network}: адрес {address}, найдено {found_count} транзакций\n")
    except Exception as e:
        print(f"Ошибка записи в лог: {e}")


def log_monitor_end(total_count: int):
    """Лог окончания проверки"""
    log_file = get_log_file()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] ИТОГО: {total_count} транзакций\n")
            f.write(f"[{timestamp}] ========== ПРОВЕРКА ЗАВЕРШЕНА ==========\n")
            f.write(f"\n")
    except Exception as e:
        print(f"Ошибка записи в лог: {e}")
