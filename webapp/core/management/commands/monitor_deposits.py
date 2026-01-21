"""
Management команда для мониторинга депозитов
Запуск: python manage.py monitor_deposits
"""
from django.core.management.base import BaseCommand
import time
from core.deposit_monitor import DepositMonitor, auto_credit_confirmed_deposits


class Command(BaseCommand):
    help = 'Мониторинг депозитных транзакций из блокчейнов'

    def add_arguments(self, parser):
        parser.add_argument(
            '--once',
            action='store_true',
            help='Запустить проверку один раз вместо бесконечного цикла',
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=60,
            help='Интервал между проверками в секундах (по умолчанию 60)',
        )

    def handle(self, *args, **options):
        monitor = DepositMonitor()
        run_once = options['once']
        interval = options['interval']
        
        self.stdout.write(self.style.SUCCESS('Запуск мониторинга депозитов...'))
        
        if run_once:
            # Одна проверка
            monitor.run()
            auto_credit_confirmed_deposits()
            self.stdout.write(self.style.SUCCESS('Проверка завершена'))
        else:
            # Бесконечный цикл
            self.stdout.write(self.style.SUCCESS(f'Мониторинг запущен с интервалом {interval} секунд'))
            self.stdout.write(self.style.WARNING('Для остановки нажмите Ctrl+C'))
            
            try:
                while True:
                    monitor.run()
                    auto_credit_confirmed_deposits()
                    time.sleep(interval)
            except KeyboardInterrupt:
                self.stdout.write(self.style.WARNING('\nМониторинг остановлен'))

