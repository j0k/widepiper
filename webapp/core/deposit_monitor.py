"""
Мониторинг депозитных транзакций из разных блокчейнов
"""
import requests
from decimal import Decimal
from datetime import datetime
from typing import List, Dict, Optional
from django.utils import timezone

from .models import DepositTransaction, UserProfile, User
from .transaction_logger import (
    log_deposit_detected,
    log_deposit_confirmed,
    log_user_found,
    log_user_not_found,
    log_balance_credited,
    log_monitor_start,
    log_monitor_network,
    log_monitor_end,
)
from .const import (
    DEPOSIT_ADDRESS_TRC20,
    DEPOSIT_ADDRESS_BSC,
    DEPOSIT_ADDRESS_TON,
    BSC_API_KEY,
)


class DepositMonitor:
    """Мониторинг депозитов в разных сетях"""
    
    REQUIRED_CONFIRMATIONS = {
        'TRC20': 19,  # TRON требует 19 подтверждений
        'BSC': 15,    # BSC требует 15 подтверждений
        'TON': 1,     # TON обычно 1 подтверждение
    }
    
    LAST_BLOCK_FILE = '/tmp/bsc_last_block.txt'  # Файл для хранения последнего проверенного блока
    
    def __init__(self):
        self.trc20_address = DEPOSIT_ADDRESS_TRC20
        self.bsc_address = DEPOSIT_ADDRESS_BSC
        self.ton_address = DEPOSIT_ADDRESS_TON
        self.bsc_api_key = BSC_API_KEY
    
    def get_last_checked_block(self) -> int:
        """Получить номер последнего проверенного блока"""
        try:
            with open(self.LAST_BLOCK_FILE, 'r') as f:
                return int(f.read().strip())
        except (FileNotFoundError, ValueError):
            return 0
    
    def save_last_checked_block(self, block_number: int):
        """Сохранить номер последнего проверенного блока"""
        try:
            with open(self.LAST_BLOCK_FILE, 'w') as f:
                f.write(str(block_number))
        except Exception as e:
            print(f"Ошибка при сохранении номера блока: {e}")

    def check_trc20_deposits(self) -> List[Dict]:
        """Проверка депозитов USDT TRC-20 через TronGrid API"""
        if not self.trc20_address or self.trc20_address == "TQXBB3DXYbgc8fdgs982ldskV9mSPQ69Bdtmb":
            print("TRC20 адрес не настроен")
            return []
        
        try:
            # TronGrid API для получения TRC-20 транзакций
            url = f"https://api.trongrid.io/v1/accounts/{self.trc20_address}/transactions/trc20"
            params = {
                "limit": 50,
                "only_confirmed": "true",  # Должна быть строка, а не булево значение
                "contract_address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"  # USDT TRC-20
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            deposits = []
            if data.get("data"):
                for tx in data["data"]:
                    # Проверяем, что это входящая транзакция
                    if tx.get("to") == self.trc20_address:
                        deposits.append({
                            'tx_hash': tx.get('transaction_id'),
                            'from_address': tx.get('from'),
                            'to_address': tx.get('to'),
                            'amount': Decimal(tx.get('value', 0)) / Decimal(10**6),  # USDT имеет 6 decimals
                            'timestamp': tx.get('block_timestamp'),
                            'confirmations': tx.get('confirmed', 0),
                            'network': 'TRC20'
                        })
            
            return deposits
            
        except Exception as e:
            print(f"Ошибка при проверке TRC20 депозитов: {e}")
            return []

    def check_bsc_deposits(self) -> List[Dict]:
        """Проверка депозитов USDT BSC через Web3 (RPC)"""
        if not self.bsc_address or self.bsc_address == "0x0000000000000000000000000000000000000000":
            print("BSC адрес не настроен")
            return []
        
        try:
            from web3 import Web3
            from .const import BSC_RPC_URL, USDT_TOKEN_ADDRESS
            
            # Подключаемся к BSC через Ankr RPC (бесплатный и без лимитов)
            rpc_url = BSC_RPC_URL or "https://rpc.ankr.com/bsc"
            w3 = Web3(Web3.HTTPProvider(rpc_url))
            
            if not w3.is_connected():
                print("Не удалось подключиться к BSC RPC")
                return []
            
            # ERC-20 Transfer event signature
            # Transfer(address indexed from, address indexed to, uint256 value)
            transfer_topic = w3.keccak(text='Transfer(address,address,uint256)').hex()
            
            # Получаем последний проверенный блок и текущий блок
            latest_block = w3.eth.block_number
            last_checked = self.get_last_checked_block()
            
            # Если это первый запуск, проверяем последние 5 блоков (~15 секунд на BSC)
            if last_checked == 0:
                from_block = max(0, latest_block - 5)
                print(f"Первый запуск BSC мониторинга, проверка последних {latest_block - from_block} блоков")
            else:
                # Проверяем только новые блоки с последней проверки
                from_block = last_checked + 1
                print(f"Проверка BSC блоков с {from_block} по {latest_block} ({latest_block - from_block + 1} блоков)")
            
            # Если нет новых блоков, пропускаем
            if from_block > latest_block:
                print("Нет новых BSC блоков для проверки")
                return []
            
            # Фильтр для входящих USDT транзакций
            logs = w3.eth.get_logs({
                'fromBlock': from_block,
                'toBlock': 'latest',
                'address': Web3.to_checksum_address(USDT_TOKEN_ADDRESS),
                'topics': [
                    transfer_topic,
                    None,  # from (any)
                    '0x' + self.bsc_address[2:].lower().zfill(64)  # to (наш адрес)
                ]
            })
            
            deposits = []
            for log in logs:
                tx_hash = log['transactionHash'].hex()
                from_address = '0x' + log['topics'][1].hex()[-40:]
                to_address = '0x' + log['topics'][2].hex()[-40:]
                amount = int(log['data'], 16)
                
                # Получаем информацию о блоке
                block = w3.eth.get_block(log['blockNumber'])
                
                deposits.append({
                    'tx_hash': tx_hash,
                    'from_address': Web3.to_checksum_address(from_address),
                    'to_address': Web3.to_checksum_address(to_address),
                    'amount': Decimal(amount) / Decimal(10**18),  # USDT BEP-20 has 18 decimals
                    'timestamp': block['timestamp'],
                    'confirmations': latest_block - log['blockNumber'],
                    'network': 'BSC'
                })
            
            # Сохраняем номер последнего проверенного блока
            self.save_last_checked_block(latest_block)
            
            return deposits
            
        except Exception as e:
            print(f"Ошибка при проверке BSC депозитов: {e}")
            return []

    def check_ton_deposits(self) -> List[Dict]:
        """Проверка депозитов USDT TON через TONCenter API v3"""
        if not self.ton_address or self.ton_address == "UQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAGF":
            print("TON адрес не настроен")
            return []
        
        try:
            from .const import USDT_TON_CONTRACT
            
            # Используем TonAPI v3 для получения Jetton переводов
            # TonAPI - более надежный для работы с Jetton (токенами на TON)
            url = "https://tonapi.io/v2/accounts/{address}/jettons/{jetton_address}/history"
            url = url.format(
                address=self.ton_address,
                jetton_address=USDT_TON_CONTRACT
            )
            
            params = {
                "limit": 20,
                "start_date": int((datetime.now().timestamp() - 86400))  # Последние 24 часа
            }
            
            response = requests.get(url, params=params, timeout=15)
            
            # Если TonAPI не работает, пробуем резервный метод через TONCenter
            if response.status_code != 200:
                print(f"TonAPI недоступен (код {response.status_code}), используем резервный метод")
                return self._check_ton_deposits_fallback()
            
            data = response.json()
            deposits = []
            
            print(f"🔍 TON API Response: found {len(data.get('events', []))} events")
            
            # TonAPI v2 возвращает список событий (events)
            if data.get("events"):
                for event in data["events"]:
                    # Проверяем что это Jetton Transfer
                    actions = event.get("actions", [])
                    for action in actions:
                        if action.get("type") != "JettonTransfer":
                            continue
                        
                        jetton_transfer = action.get("JettonTransfer", {})
                        
                        # Проверяем что получатель - это наш адрес
                        # API возвращает в формате hex (0:xxx), нужно конвертировать
                        recipient_hex = jetton_transfer.get("recipient", {}).get("address", "")
                        
                        print(f"🎯 Recipient from API: {recipient_hex}")
                        print(f"🏠 Our address (friendly): {self.ton_address}")
                        
                        # Используем pytoniq для правильной конвертации адресов
                        try:
                            from pytoniq_core import Address as TonAddress
                            
                            # Конвертируем recipient из API (hex format) в объект Address
                            recipient_address = TonAddress(recipient_hex)
                            
                            # Конвертируем наш friendly адрес в объект Address
                            our_address = TonAddress(self.ton_address)
                            
                            # Сравниваем адреса напрямую
                            addresses_match = (recipient_address.to_str(1, 1, 1) == our_address.to_str(1, 1, 1))
                            
                            print(f"🔍 Recipient (friendly): {recipient_address.to_str()}")
                            print(f"🏠 Our address (friendly): {our_address.to_str()}")
                            print(f"✓ Match: {addresses_match}")
                            
                            if not addresses_match:
                                print(f"⏭️  Skipping - not our address")
                                continue
                                
                        except Exception as e:
                            print(f"❌ Error comparing addresses: {e}")
                            import traceback
                            traceback.print_exc()
                            continue
                        
                        print(f"✅ Match! This is for us!")
                        
                        # Получаем отправителя
                        sender = jetton_transfer.get("sender", {}).get("address", "")
                        
                        # Получаем сумму (в базовых единицах, для USDT это 6 decimals)
                        amount_str = jetton_transfer.get("amount", "0")
                        amount = Decimal(amount_str) / Decimal(10**6)
                        
                        if amount <= 0:
                            continue
                        
                        # Получаем хеш транзакции
                        tx_hash = event.get("event_id", "")
                        
                        deposits.append({
                            'tx_hash': tx_hash,
                            'from_address': sender,
                            'to_address': self.ton_address,
                            'amount': amount,
                            'timestamp': event.get("timestamp", 0),
                            'confirmations': 1,  # TON обычно требует 1 подтверждение
                            'network': 'TON'
                        })
            
            return deposits
            
        except Exception as e:
            print(f"Ошибка при проверке TON депозитов: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _check_ton_deposits_fallback(self) -> List[Dict]:
        """Резервный метод проверки TON через TONCenter API"""
        try:
            from .const import TON_API_ENDPOINT
            
            # TONCenter getTransactions
            url = f"{TON_API_ENDPOINT}/getTransactions"
            params = {
                "address": self.ton_address,
                "limit": 50,
                "archival": "false"
            }
            
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            deposits = []
            
            if data.get("ok") and data.get("result"):
                for tx in data["result"]:
                    # Проверяем входящие сообщения
                    in_msg = tx.get("in_msg", {})
                    if not in_msg or in_msg.get("source") == "":
                        continue
                    
                    # Получаем value (в nanoTON)
                    value = int(in_msg.get("value", 0))
                    
                    # Для Jetton-переводов ищем внутренние сообщения
                    out_msgs = tx.get("out_msgs", [])
                    
                    # Простой метод: если есть value и это не пустой transfer
                    if value > 0:
                        # Конвертируем в TON (примерно, это упрощенный подход)
                        # Реально для USDT нужно парсить Jetton transfer payload
                        amount = Decimal(value) / Decimal(10**9)  # nanoTON to TON
                        
                        # Фильтруем слишком маленькие транзакции (комиссии)
                        if amount < Decimal("0.01"):
                            continue
                        
                        source = in_msg.get("source", "")
                        tx_hash = tx.get("transaction_id", {}).get("hash", "")
                        
                        if not tx_hash or not source:
                            continue
                        
                        deposits.append({
                            'tx_hash': tx_hash,
                            'from_address': source,
                            'to_address': self.ton_address,
                            'amount': amount,
                            'timestamp': tx.get('utime', 0),
                            'confirmations': 1,
                            'network': 'TON'
                        })
            
            return deposits
            
        except Exception as e:
            print(f"Ошибка в резервном методе TON: {e}")
            return []

    def process_deposit(self, deposit_data: Dict) -> Optional[DepositTransaction]:
        """Обработка найденной транзакции депозита"""
        try:
            tx_hash = deposit_data['tx_hash']
            network = deposit_data['network']

            # Проверяем, не обрабатывали ли уже эту транзакцию
            existing = DepositTransaction.objects.filter(tx_hash=tx_hash).first()
            if existing:
                # Обновляем количество подтверждений
                if existing.status == DepositTransaction.StatusType.PENDING:
                    existing.confirmations = deposit_data.get('confirmations', 0)
                    existing.save()
                return existing

            # Создаем новую запись депозита
            deposit = DepositTransaction.objects.create(
                amount=deposit_data['amount'],
                network=network,
                tx_hash=tx_hash,
                from_address=deposit_data['from_address'],
                to_address=deposit_data['to_address'],
                confirmations=deposit_data.get('confirmations', 0),
                status=DepositTransaction.StatusType.PENDING
            )

            print(f"")
            print(f"{'='*70}")
            print(f"[DEPOSIT] НОВАЯ ТРАНЗАКЦИЯ ОБНАРУЖЕНА")
            print(f"{'='*70}")
            print(f"  TX Hash:      {tx_hash}")
            print(f"  Сеть:         {network}")
            print(f"  Сумма:        {deposit_data['amount']} USDT")
            print(f"  От кого:      {deposit_data['from_address']}")
            print(f"  Куда (наш):   {deposit_data['to_address']}")
            print(f"  Подтвержд.:   {deposit_data.get('confirmations', 0)}")
            print(f"  Статус:       PENDING (ожидает подтверждений)")
            print(f"{'='*70}")
            print(f"")

            # Пишем в файл лога
            log_deposit_detected(
                tx_hash=tx_hash,
                network=network,
                amount=deposit_data['amount'],
                from_address=deposit_data['from_address'],
                to_address=deposit_data['to_address'],
                confirmations=deposit_data.get('confirmations', 0)
            )

            return deposit
            
        except Exception as e:
            print(f"Ошибка при обработке депозита: {e}")
            return None

    def confirm_deposit(self, deposit: DepositTransaction) -> bool:
        """Подтверждение депозита при достижении нужного количества подтверждений"""
        try:
            required_confirmations = self.REQUIRED_CONFIRMATIONS.get(deposit.network, 15)

            if deposit.confirmations >= required_confirmations:
                deposit.status = DepositTransaction.StatusType.CONFIRMED
                deposit.confirmed_at = timezone.now()
                deposit.save()

                print(f"")
                print(f"{'='*70}")
                print(f"[DEPOSIT] ТРАНЗАКЦИЯ ПОДТВЕРЖДЕНА")
                print(f"{'='*70}")
                print(f"  TX Hash:      {deposit.tx_hash}")
                print(f"  Сеть:         {deposit.network}")
                print(f"  Сумма:        {deposit.amount} USDT")
                print(f"  Подтвержд.:   {deposit.confirmations}/{required_confirmations}")
                print(f"  Статус:       CONFIRMED")
                print(f"{'='*70}")
                print(f"")

                # Пишем в файл лога
                log_deposit_confirmed(
                    tx_hash=deposit.tx_hash,
                    network=deposit.network,
                    amount=deposit.amount,
                    confirmations=deposit.confirmations,
                    required=required_confirmations
                )

                return True

            return False
            
        except Exception as e:
            print(f"Ошибка при подтверждении депозита: {e}")
            return False

    def credit_deposit(self, deposit: DepositTransaction, user: User) -> bool:
        """Зачисление депозита на баланс пользователя"""
        try:
            if deposit.status != DepositTransaction.StatusType.CONFIRMED:
                return False

            # Получаем профиль пользователя
            user_profile = UserProfile.objects.get(user=user)

            # Запоминаем старый баланс
            old_balance = user_profile.usdt_balance

            # Зачисляем на баланс
            user_profile.usdt_balance += deposit.amount
            user_profile.save()

            # Обновляем статус депозита
            deposit.user = user
            deposit.status = DepositTransaction.StatusType.CREDITED
            deposit.credited_at = timezone.now()
            deposit.save()

            print(f"")
            print(f"{'='*70}")
            print(f"[DEPOSIT] БАЛАНС ПОПОЛНЕН")
            print(f"{'='*70}")
            print(f"  TX Hash:      {deposit.tx_hash}")
            print(f"  Сеть:         {deposit.network}")
            print(f"  Пользователь: {user.username} (ID: {user.id})")
            print(f"  Кошелек:      {deposit.from_address}")
            print(f"  Сумма:        +{deposit.amount} USDT")
            print(f"  Баланс БЫЛ:   {old_balance} USDT")
            print(f"  Баланс СТАЛ:  {user_profile.usdt_balance} USDT")
            print(f"  Статус:       CREDITED")
            print(f"{'='*70}")
            print(f"")

            # Пишем в файл лога
            log_balance_credited(
                tx_hash=deposit.tx_hash,
                network=deposit.network,
                username=user.username,
                user_id=user.id,
                from_address=deposit.from_address,
                amount=deposit.amount,
                old_balance=old_balance,
                new_balance=user_profile.usdt_balance
            )

            return True
            
        except Exception as e:
            print(f"Ошибка при зачислении депозита: {e}")
            return False

    def run(self):
        """Запуск мониторинга всех сетей"""
        print(f"")
        print(f"[{datetime.now()}] ========== ПРОВЕРКА ДЕПОЗИТОВ ==========")
        log_monitor_start()

        # Проверяем все сети
        all_deposits = []

        print(f"[{datetime.now()}] Проверяю TRC-20... (адрес: {self.trc20_address})")
        trc20_deposits = self.check_trc20_deposits()
        all_deposits.extend(trc20_deposits)
        print(f"[{datetime.now()}] TRC-20: найдено {len(trc20_deposits)} транзакций")
        log_monitor_network("TRC-20", self.trc20_address or "не настроен", len(trc20_deposits))

        print(f"[{datetime.now()}] Проверяю BSC... (адрес: {self.bsc_address})")
        bsc_deposits = self.check_bsc_deposits()
        all_deposits.extend(bsc_deposits)
        print(f"[{datetime.now()}] BSC: найдено {len(bsc_deposits)} транзакций")
        log_monitor_network("BSC", self.bsc_address or "не настроен", len(bsc_deposits))

        print(f"[{datetime.now()}] Проверяю TON... (адрес: {self.ton_address})")
        ton_deposits = self.check_ton_deposits()
        all_deposits.extend(ton_deposits)
        print(f"[{datetime.now()}] TON: найдено {len(ton_deposits)} транзакций")
        log_monitor_network("TON", self.ton_address or "не настроен", len(ton_deposits))

        print(f"[{datetime.now()}] ИТОГО найдено транзакций: {len(all_deposits)}")

        # Обрабатываем каждую транзакцию
        for deposit_data in all_deposits:
            deposit = self.process_deposit(deposit_data)

            if deposit and deposit.status == DepositTransaction.StatusType.PENDING:
                # Проверяем подтверждения
                if self.confirm_deposit(deposit):
                    # После подтверждения автоматически зачисляем
                    self.auto_credit_deposit(deposit)

        print(f"[{datetime.now()}] ========== ПРОВЕРКА ЗАВЕРШЕНА ==========")
        log_monitor_end(len(all_deposits))
    
    def auto_credit_deposit(self, deposit: DepositTransaction) -> bool:
        """
        Автоматическое зачисление депозита на баланс пользователя
        Ищет пользователя по crypto_wallet_address == from_address
        """
        try:
            if deposit.status != DepositTransaction.StatusType.CONFIRMED:
                return False
            
            # Ищем пользователя по адресу отправителя
            # Для TON депозитов ищем по ton_wallet_address, для остальных по crypto_wallet_address
            if deposit.network == 'TON':
                # Конвертируем from_address в friendly формат для сравнения
                from_address_friendly = deposit.from_address
                if ':' in deposit.from_address:
                    try:
                        from pytoniq_core import Address as TonAddress
                        addr_obj = TonAddress(deposit.from_address)
                        # Пробуем оба варианта - bounceable и non-bounceable
                        from_address_friendly_bounce = addr_obj.to_str(is_bounceable=True)
                        from_address_friendly_nonbounce = addr_obj.to_str(is_bounceable=False)
                        
                        print(f"🔄 Конвертация адреса:")
                        print(f"   Hex: {deposit.from_address}")
                        print(f"   Bounceable (EQ): {from_address_friendly_bounce}")
                        print(f"   Non-bounceable (UQ): {from_address_friendly_nonbounce}")
                        
                        from_address_friendly = from_address_friendly_nonbounce
                    except Exception as e:
                        print(f"❌ Ошибка конвертации: {e}")
                        pass
                
                print(f"🔍 Ищем пользователя с TON адресом: {from_address_friendly}")
                user_profile = UserProfile.objects.filter(
                    ton_wallet_address__iexact=from_address_friendly
                ).first()
                
                if not user_profile:
                    # Попробуем найти по другому варианту (bounceable)
                    if ':' in deposit.from_address:
                        try:
                            from pytoniq_core import Address as TonAddress
                            addr_obj = TonAddress(deposit.from_address)
                            from_address_friendly_bounce = addr_obj.to_str(is_bounceable=True)
                            print(f"🔄 Пробуем bounceable вариант: {from_address_friendly_bounce}")
                            user_profile = UserProfile.objects.filter(
                                ton_wallet_address__iexact=from_address_friendly_bounce
                            ).first()
                        except:
                            pass
            else:
                user_profile = UserProfile.objects.filter(
                    crypto_wallet_address__iexact=deposit.from_address
                ).first()
            
            if not user_profile:
                wallet_field = "TON wallet" if deposit.network == 'TON' else "wallet"
                print(f"")
                print(f"{'='*70}")
                print(f"[DEPOSIT] ПОЛЬЗОВАТЕЛЬ НЕ НАЙДЕН")
                print(f"{'='*70}")
                print(f"  TX Hash:      {deposit.tx_hash}")
                print(f"  Сеть:         {deposit.network}")
                print(f"  Сумма:        {deposit.amount} USDT")
                print(f"  От кого:      {deposit.from_address}")
                print(f"  Статус:       НЕ ЗАЧИСЛЕНО")
                print(f"  Причина:      Не найден пользователь с таким {wallet_field}")
                print(f"{'='*70}")
                print(f"")

                # Пишем в файл лога
                log_user_not_found(
                    tx_hash=deposit.tx_hash,
                    network=deposit.network,
                    from_address=deposit.from_address,
                    amount=deposit.amount
                )

                return False

            # Нашли пользователя - логируем
            print(f"")
            print(f"{'='*70}")
            print(f"[DEPOSIT] ПОЛЬЗОВАТЕЛЬ НАЙДЕН")
            print(f"{'='*70}")
            print(f"  TX Hash:      {deposit.tx_hash}")
            print(f"  Сеть:         {deposit.network}")
            print(f"  Кошелек:      {deposit.from_address}")
            print(f"  Пользователь: {user_profile.user.username} (ID: {user_profile.user.id})")
            print(f"  Зачисляем:    {deposit.amount} USDT")
            print(f"{'='*70}")

            # Пишем в файл лога
            log_user_found(
                tx_hash=deposit.tx_hash,
                network=deposit.network,
                from_address=deposit.from_address,
                username=user_profile.user.username,
                user_id=user_profile.user.id,
                amount=deposit.amount
            )

            # Зачисляем на баланс
            return self.credit_deposit(deposit, user_profile.user)
            
        except Exception as e:
            print(f"Ошибка при автоматическом зачислении: {e}")
            return False


def auto_credit_confirmed_deposits():
    """
    Автоматическое зачисление подтвержденных депозитов
    Сопоставление по crypto_wallet_address пользователя (from_address)
    """
    try:
        # Получаем все подтвержденные, но не зачисленные депозиты
        confirmed_deposits = DepositTransaction.objects.filter(
            status=DepositTransaction.StatusType.CONFIRMED,
            user__isnull=True
        )
        
        print(f"🔍 Checking {confirmed_deposits.count()} confirmed deposits for auto-crediting...")
        
        for deposit in confirmed_deposits:
            # Ищем пользователя по адресу отправителя
            # Для TON депозитов ищем по ton_wallet_address
            if deposit.network == 'TON':
                from_address_friendly = deposit.from_address
                if ':' in deposit.from_address:
                    try:
                        from pytoniq_core import Address as TonAddress
                        addr_obj = TonAddress(deposit.from_address)
                        # Пробуем оба варианта - bounceable и non-bounceable
                        from_address_friendly_bounce = addr_obj.to_str(is_bounceable=True)
                        from_address_friendly_nonbounce = addr_obj.to_str(is_bounceable=False)
                        
                        print(f"🔄 [auto_credit] Конвертация:")
                        print(f"   Hex: {deposit.from_address}")
                        print(f"   Bounceable (EQ): {from_address_friendly_bounce}")
                        print(f"   Non-bounceable (UQ): {from_address_friendly_nonbounce}")
                        
                        from_address_friendly = from_address_friendly_nonbounce
                    except Exception as e:
                        print(f"❌ Ошибка конвертации: {e}")
                        pass
                
                print(f"🔍 [auto_credit] Ищем TON: {from_address_friendly}")
                user_profile = UserProfile.objects.filter(
                    ton_wallet_address__iexact=from_address_friendly
                ).first()
                
                if not user_profile:
                    # Попробуем bounceable вариант
                    if ':' in deposit.from_address:
                        try:
                            from pytoniq_core import Address as TonAddress
                            from_address_friendly_bounce = TonAddress(deposit.from_address).to_str(is_bounceable=True)
                            print(f"🔄 [auto_credit] Пробуем EQ: {from_address_friendly_bounce}")
                            user_profile = UserProfile.objects.filter(
                                ton_wallet_address__iexact=from_address_friendly_bounce
                            ).first()
                        except:
                            pass
            else:
                user_profile = UserProfile.objects.filter(
                    crypto_wallet_address__iexact=deposit.from_address
                ).first()
            
            if user_profile:
                monitor = DepositMonitor()
                monitor.credit_deposit(deposit, user_profile.user)
            else:
                print(f"Пользователь не найден для депозита {deposit.tx_hash} от {deposit.from_address}")
    
    except Exception as e:
        print(f"Ошибка при автоматическом зачислении: {e}")

