"""
Модуль для вывода USDT на внешние кошельки
Поддерживает TRC-20, BSC, TON
"""
from decimal import Decimal
from typing import Dict
import requests
from web3 import Web3
from .const import (
    WITHDRAW_PRIVATE_KEY_TRC20,
    WITHDRAW_PRIVATE_KEY_BSC,
    WITHDRAW_TON_MNEMONIC,
    USDT_TRC20_CONTRACT,
    USDT_TOKEN_ADDRESS,
    USDT_TON_CONTRACT,
    BSC_RPC_URL,
    TRONGRID_API_URL,
)


def send_usdt_trc20(to_address: str, amount: Decimal) -> Dict:
    """
    Отправка USDT TRC-20 на адрес
    """
    try:
        from tronpy import Tron
        from tronpy.keys import PrivateKey
        
        if not WITHDRAW_PRIVATE_KEY_TRC20:
            return {"success": False, "error": "TRC-20 withdrawal not configured"}
        
        # Подключаемся к TRON mainnet
        client = Tron()
        
        # Загружаем приватный ключ
        priv_key = PrivateKey(bytes.fromhex(WITHDRAW_PRIVATE_KEY_TRC20))
        
        # Получаем контракт USDT
        contract = client.get_contract(USDT_TRC20_CONTRACT)
        
        # Конвертируем сумму (USDT TRC-20 имеет 6 decimals)
        amount_sun = int(amount * Decimal(10**6))
        
        # Отправляем транзакцию
        txn = (
            contract.functions.transfer(to_address, amount_sun)
            .with_owner(priv_key.public_key.to_base58check_address())
            .fee_limit(50_000_000)  # 50 TRX fee limit
            .build()
            .sign(priv_key)
        )
        
        result = txn.broadcast()
        tx_id = result.get('txid', '')
        
        return {
            "success": True,
            "tx_id": tx_id,
            "explorer_url": f"https://tronscan.org/#/transaction/{tx_id}"
        }
        
    except Exception as e:
        print(f"❌ TRC-20 withdrawal error: {str(e)}")
        return {"success": False, "error": str(e)}


def send_usdt_bsc(to_address: str, amount: Decimal) -> Dict:
    """
    Отправка USDT BEP-20 (BSC) на адрес
    """
    try:
        if not WITHDRAW_PRIVATE_KEY_BSC:
            return {"success": False, "error": "BSC withdrawal not configured"}
        
        # Подключаемся к BSC
        w3 = Web3(Web3.HTTPProvider(BSC_RPC_URL))
        
        if not w3.is_connected():
            return {"success": False, "error": "Cannot connect to BSC"}
        
        # Загружаем приватный ключ
        account = w3.eth.account.from_key(WITHDRAW_PRIVATE_KEY_BSC)
        
        # ERC-20 ABI для transfer
        erc20_abi = [
            {
                "constant": False,
                "inputs": [
                    {"name": "_to", "type": "address"},
                    {"name": "_value", "type": "uint256"}
                ],
                "name": "transfer",
                "outputs": [{"name": "", "type": "bool"}],
                "type": "function"
            }
        ]
        
        # Получаем контракт USDT
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(USDT_TOKEN_ADDRESS),
            abi=erc20_abi
        )
        
        # Конвертируем сумму (USDT BEP-20 имеет 18 decimals)
        amount_wei = int(amount * Decimal(10**18))
        
        # Подготавливаем транзакцию
        nonce = w3.eth.get_transaction_count(account.address)
        
        transaction = contract.functions.transfer(
            Web3.to_checksum_address(to_address),
            amount_wei
        ).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': 100000,
            'gasPrice': w3.eth.gas_price,
        })
        
        # Подписываем и отправляем
        signed_txn = w3.eth.account.sign_transaction(transaction, WITHDRAW_PRIVATE_KEY_BSC)
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        tx_id = tx_hash.hex()
        
        return {
            "success": True,
            "tx_id": tx_id,
            "explorer_url": f"https://bscscan.com/tx/{tx_id}"
        }
        
    except Exception as e:
        print(f"❌ BSC withdrawal error: {str(e)}")
        return {"success": False, "error": str(e)}


def send_usdt_ton(to_address: str, amount: Decimal) -> Dict:
    """
    Отправка USDT Jetton (TON) на адрес через pytoniq
    """
    import asyncio
    
    async def _send_ton_async():
        try:
            if not WITHDRAW_TON_MNEMONIC:
                return {"success": False, "error": "TON withdrawal not configured"}
            
            from pytoniq import LiteBalancer, WalletV4R2, begin_cell
            from pytoniq_core import Address
            
            # Валидация адреса получателя
            try:
                recipient_address = Address(to_address)
            except Exception as e:
                return {"success": False, "error": f"Invalid TON address: {str(e)}"}
            
            # Восстанавливаем кошелек из мнемоники
            mnemonics = WITHDRAW_TON_MNEMONIC.strip('"').split()
            
            if len(mnemonics) not in [12, 24]:
                return {"success": False, "error": "Invalid mnemonic phrase length"}
            
            # Подключаемся к TON
            provider = LiteBalancer.from_mainnet_config(trust_level=2)
            await provider.start_up()
            
            try:
                # Создаем кошелек
                wallet = await WalletV4R2.from_mnemonic(provider=provider, mnemonics=mnemonics)
                wallet_address = wallet.address
                
                print(f"💼 Wallet address: {wallet_address.to_str()}")
                
                # Проверяем баланс
                balance = await wallet.get_balance()
                print(f"💰 Wallet balance: {balance / 10**9} TON")
                
                if balance < int(0.1 * 10**9):
                    return {
                        "success": False,
                        "error": f"Insufficient TON balance. Current: {balance / 10**9} TON, need at least 0.1 TON"
                    }
                
                # Конвертируем сумму (USDT TON имеет 6 decimals)
                amount_jetton = int(amount * Decimal(10**6))
                
                # Получаем адрес Jetton Master
                jetton_master_address = Address(USDT_TON_CONTRACT)
                
                # Получаем адрес Jetton wallet
                jetton_wallet_address = await get_jetton_wallet_address(
                    provider,
                    jetton_master_address,
                    wallet_address
                )
                
                if not jetton_wallet_address:
                    return {"success": False, "error": "Failed to get Jetton wallet address"}
                
                print(f"🎫 Jetton wallet: {jetton_wallet_address.to_str()}")
                
                # Создаем Jetton transfer payload (TEP-74)
                forward_payload = begin_cell().end_cell()
                
                transfer_body = (
                    begin_cell()
                    .store_uint(0xf8a7ea5, 32)      # op: transfer
                    .store_uint(0, 64)               # query_id
                    .store_coins(amount_jetton)      # amount
                    .store_address(recipient_address) # destination
                    .store_address(wallet_address)   # response_destination
                    .store_bit(0)                    # custom_payload (null)
                    .store_coins(1)                  # forward_ton_amount
                    .store_bit(0)                    # forward_payload (left bit = 0, no ref)
                    .end_cell()
                )
                
                # Отправляем транзакцию
                # 0.05 TON на gas fees
                await wallet.transfer(
                    destination=jetton_wallet_address,
                    amount=int(0.05 * 10**9),
                    body=transfer_body
                )
                
                print(f"✅ TON Jetton withdrawal sent!")
                print(f"   Amount: {amount} USDT")
                print(f"   To: {to_address}")
                
                return {
                    "success": True,
                    "tx_id": "pending",  # Transaction hash будет доступен после подтверждения
                    "explorer_url": f"https://tonscan.org/address/{wallet_address.to_str()}",
                    "message": f"Successfully sent {amount} USDT. Check wallet for confirmation."
                }
                
            finally:
                await provider.close_all()
                
        except Exception as e:
            print(f"❌ TON withdrawal error: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    # Запускаем асинхронную функцию
    try:
        return asyncio.run(_send_ton_async())
    except Exception as e:
        print(f"❌ TON withdrawal asyncio error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


async def get_jetton_wallet_address(provider, jetton_master_address, owner_address):
    """
    Получает адрес Jetton wallet для конкретного владельца
    """
    try:
        from pytoniq import begin_cell
        
        # Создаем payload с адресом владельца
        owner_address_cell = begin_cell().store_address(owner_address).end_cell()
        
        # Вызываем get_wallet_address на Jetton Master контракте
        result = await provider.run_get_method(
            address=jetton_master_address,
            method="get_wallet_address",
            stack=[owner_address_cell.begin_parse()]
        )
        
        if result and len(result) > 0:
            # Результат - это адрес Jetton wallet
            jetton_wallet_address = result[0].load_address()
            return jetton_wallet_address
        
        return None
        
    except Exception as e:
        print(f"❌ Error getting Jetton wallet address: {str(e)}")
        return None


async def get_jetton_wallet_address_pytonlib(client, jetton_master_address, owner_address):
    """
    Получает адрес Jetton wallet для конкретного владельца через pytonlib
    """
    try:
        from tvm_valuetypes import serialize_tvm_stack
        from tvm_valuetypes.cell import begin_cell
        
        # Создаем payload с адресом владельца
        owner_address_cell = begin_cell().store_address(owner_address).end_cell()
        
        # Вызываем get_wallet_address на Jetton Master контракте
        stack = serialize_tvm_stack([['tvm.Slice', owner_address_cell.to_boc()]])
        
        result = await client.raw_run_method(
            address=jetton_master_address,
            method='get_wallet_address',
            stack_data=stack
        )
        
        if result.get('@type') == 'smc.runResult' and result.get('exit_code') == 0:
            # Парсим результат
            stack_result = result.get('stack', [])
            if stack_result and len(stack_result) > 0:
                jetton_wallet_addr = stack_result[0][1]['bytes']
                
                # Декодируем адрес из base64
                import base64
                from tvm_valuetypes.cell import Cell
                
                addr_cell = Cell.one_from_boc(base64.b64decode(jetton_wallet_addr))
                jetton_wallet_address = addr_cell.begin_parse().load_address()
                
                return jetton_wallet_address
        
        print(f"❌ Failed to get Jetton wallet: {result}")
        return None
        
    except Exception as e:
        print(f"❌ Error getting Jetton wallet address: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
