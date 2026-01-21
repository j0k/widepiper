#!/usr/bin/env python
"""Скрипт для добавления USDT баланса пользователю"""
import os
import sys
import django

# Настройка Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'webapp'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webapp.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import UserProfile
from decimal import Decimal

# Параметры
EMAIL = "user@example.com"  # Замените на email пользователя
USERNAME = "username"  # Или username пользователя
AMOUNT_TO_ADD = Decimal("1000.00")  # Сумма для добавления

def main():
    # Ищем пользователя по email или username
    user = None
    try:
        user = User.objects.get(email=EMAIL)
        print(f"Найден пользователь по email: {user.username} ({user.email})")
    except User.DoesNotExist:
        try:
            user = User.objects.get(username=USERNAME)
            print(f"Найден пользователь по username: {user.username} ({user.email})")
        except User.DoesNotExist:
            print(f"Пользователь с email={EMAIL} или username={USERNAME} не найден!")
            print("\nСуществующие пользователи:")
            for u in User.objects.all():
                print(f"  - {u.username} ({u.email})")
            return

    # Получаем или создаём профиль
    profile, created = UserProfile.objects.get_or_create(user=user)
    
    old_balance = profile.usdt_balance
    profile.usdt_balance += AMOUNT_TO_ADD
    profile.save()
    
    print(f"\n✅ Баланс обновлён!")
    print(f"   Было: {old_balance} USDT")
    print(f"   Добавлено: {AMOUNT_TO_ADD} USDT")
    print(f"   Стало: {profile.usdt_balance} USDT")

if __name__ == "__main__":
    main()
