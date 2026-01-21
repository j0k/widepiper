from moralis import evm_api
from web3 import Web3
from eth_account import Account
import time
import requests
from .pancakeswap_const import (
    PANCAKESWAP_ROUTER_ADDRESS,
    PANCAKESWAP_ROUTER_ABI,
    BSC_DMT_ABI,
    BSC_USDT_ABI,
)
from .const import MORALIS_API_KEY

api_key = MORALIS_API_KEY

def get_token_priceBCS(address):  # Get all token with lp prices from BSC by contracts
    # TEMPORARY: Use mock prices for testing since API is unavailable
    # TODO: Replace with real price API when available
    from webapp.core.const import MATTER_TOKEN_ADDRESS, IDEA_TOKEN_ADDRESS
    
    if address.lower() == MATTER_TOKEN_ADDRESS.lower():
        return 1.0  # Mock MATTER price: $1
    elif address.lower() == IDEA_TOKEN_ADDRESS.lower():
        return 1.5  # Mock IDEA price: $1.5 (50% higher)
    
    # Fallback to API call
    url = f"https://api.dev.dex.guru/v1/chain/56/tokens/{address}/market"

    headers = {
        "accept": "application/json",
        "api-key": "N_NIlBUEXWXl7yjKZm-i0BagiuBotkSQC4CjXxfJK8c",
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        data = response.json()
        
        # Try different possible keys for price
        price_keys = ["price_usd", "price", "usd_price", "priceUSD"]
        for key in price_keys:
            if key in data and data[key] is not None:
                return float(data[key])
        
        # If no price found, log the response structure for debugging
        print(f"Warning: No price found in response for token {address}. Response keys: {list(data.keys())}")
        return 1.0  # Return default instead of 0 to avoid division by zero
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching price for token {address}: {e}")
        return 1.0  # Return default instead of 0
    except (KeyError, ValueError, TypeError) as e:
        print(f"Error parsing price for token {address}: {e}")
        return 1.0  # Return default instead of 0

def get_token_priceETH(address): # Get all token with lp prices from ETH by contracts
    params = {
      "chain": "eth",
      "include": "percent_change",
      "address": address,
    } # TODO: Add check for untradable token

    result = evm_api.token.get_token_price(
      api_key=api_key,
      params=params,
    )

    return float(result["usdPriceFormatted"])

def create_liquidity_poolBSC(creator_private_key, first_token_address, first_token_amount, second_token_address, second_token_amount): # For pair DMT/USDT 
    pancakeswap_router_address = PANCAKESWAP_ROUTER_ADDRESS 
    pancakeswap_router_abi = PANCAKESWAP_ROUTER_ABI
    bsc_urls = ["https://bsc-dataseed.binance.org/", "https://bsc-dataseed1.binance.org/", "https://bsc-dataseed2.binance.org/",
                "https://bsc-dataseed3.binance.org/",
                "https://bsc-dataseed4.binance.org/", "https://bsc-dataseed1.defibit.io/", "https://bsc-dataseed2.defibit.io/",
                "https://bsc-dataseed3.defibit.io/", "https://bsc-dataseed4.defibit.io/", "https://bsc-dataseed1.ninicoin.io/",
                "https://bsc-dataseed2.ninicoin.io/", "https://bsc-dataseed3.ninicoin.io/", "https://bsc-dataseed4.ninicoin.io/"]
    for url in bsc_urls:
        bsc_url = url
        web3 = Web3(Web3.HTTPProvider(bsc_url))
        if web3.is_connected():
            break



    creator_address = Account.from_key(creator_private_key).address
    router_contract = web3.eth.contract(address=pancakeswap_router_address, abi=pancakeswap_router_abi)

    first_token_amount = web3.to_wei(first_token_amount, "ether")
    second_token_amount = web3.to_wei(second_token_amount, "ether") 

    first_token_contract = web3.eth.contract(address=first_token_address, abi=BSC_DMT_ABI)
    second_token_contract = web3.eth.contract(address=second_token_address, abi=BSC_USDT_ABI)


    first_tx_estimate_gas = first_token_contract.functions.approve(pancakeswap_router_address, first_token_amount).estimate_gas({
        "from": creator_address,
    })

    tx_first = first_token_contract.functions.approve(pancakeswap_router_address, first_token_amount).build_transaction({
        'chainId': 56, 
        'gas': first_tx_estimate_gas,
        'gasPrice': web3.eth.gas_price,
        'nonce': web3.eth.get_transaction_count(creator_address),
    })

    signed_tx_first = web3.eth.account.sign_transaction(tx_first, creator_private_key)
    web3.eth.send_raw_transaction(signed_tx_first.raw_transaction)


    second_tx_estimate_gas = second_token_contract.functions.approve(pancakeswap_router_address, second_token_amount).estimate_gas({
        "from": creator_address,
    })

    tx_second = second_token_contract.functions.approve(pancakeswap_router_address, second_token_amount).build_transaction({
        'chainId': 56,
        'gas': second_tx_estimate_gas,
        'gasPrice': web3.eth.gas_price,
        'nonce': web3.eth.get_transaction_count(creator_address) + 1,
    })

    signed_tx_second = web3.eth.account.sign_transaction(tx_second, creator_private_key)
    web3.eth.send_raw_transaction(signed_tx_second.raw_transaction)

    add_liquidity_tx_estimated_gas = router_contract.functions.addLiquidity(
        first_token_address,
        second_token_address,
        first_token_amount,
        second_token_amount,
        0,
        0,
        creator_address,
        int(time.time()) + 10000
    ).estimate_gas({
        "from": creator_address,
    }) # TODO: Check gas price

    add_liquidity_tx = router_contract.functions.addLiquidity(
        first_token_address,
        second_token_address,
        first_token_amount,
        second_token_amount,
        0,
        0,
        creator_address,
        int(time.time()) + 10000
    ).build_transaction({
        'chainId': 56,
        'gas': add_liquidity_tx_estimated_gas,
        'gasPrice': web3.eth.gas_price,
        'nonce': web3.eth.get_transaction_count(creator_address) + 2,
    })

    signed_add_liquidity_txn = web3.eth.account.sign_transaction(add_liquidity_tx, creator_private_key)
    txn_hash = web3.eth.send_raw_transaction(signed_add_liquidity_txn.raw_transaction)

    print(f"Hash: {web3.to_hex(txn_hash)}") 

def add_liquidity(sender_private_key, first_token_address, first_token_amount, second_token_address, second_token_amount): # For pair DMT/USDT
    pancakeswap_router_address = PANCAKESWAP_ROUTER_ADDRESS 
    pancakeswap_router_abi = PANCAKESWAP_ROUTER_ABI
    bsc_urls = ["https://bsc-dataseed.binance.org/", "https://bsc-dataseed1.binance.org/", "https://bsc-dataseed2.binance.org/",
                "https://bsc-dataseed3.binance.org/",
                "https://bsc-dataseed4.binance.org/", "https://bsc-dataseed1.defibit.io/", "https://bsc-dataseed2.defibit.io/",
                "https://bsc-dataseed3.defibit.io/", "https://bsc-dataseed4.defibit.io/", "https://bsc-dataseed1.ninicoin.io/",
                "https://bsc-dataseed2.ninicoin.io/", "https://bsc-dataseed3.ninicoin.io/", "https://bsc-dataseed4.ninicoin.io/"]
    for url in bsc_urls:
        bsc_url = url
        web3 = Web3(Web3.HTTPProvider(bsc_url))
        if web3.is_connected():
            break

    sender_address = Account.from_key(sender_private_key).address
    router_contract = web3.eth.contract(address=pancakeswap_router_address, abi=pancakeswap_router_abi)

    first_token_amount = web3.to_wei(first_token_amount, "ether")
    second_token_amount = web3.to_wei(second_token_amount, "ether") 

    first_token_contract = web3.eth.contract(address=first_token_address, abi=BSC_DMT_ABI)
    second_token_contract = web3.eth.contract(address=second_token_address, abi=BSC_USDT_ABI)

    first_tx_estimate_gas = first_token_contract.functions.approve(pancakeswap_router_address, first_token_amount).estimate_gas({
        "from": sender_address,
    })

    tx_first = first_token_contract.functions.approve(pancakeswap_router_address, first_token_amount).build_transaction({
        'chainId': 56, 
        'gas': first_tx_estimate_gas,
        'gasPrice': web3.eth.gas_price,
        'nonce': web3.eth.get_transaction_count(sender_address),
    })

    signed_tx_first = web3.eth.account.sign_transaction(tx_first, sender_private_key)
    web3.eth.send_raw_transaction(signed_tx_first.raw_transaction)


    second_tx_estimate_gas = second_token_contract.functions.approve(pancakeswap_router_address, second_token_amount).estimate_gas({
        "from": sender_address,
    })

    tx_second = second_token_contract.functions.approve(pancakeswap_router_address, second_token_amount).build_transaction({
        'chainId': 56,
        'gas': second_tx_estimate_gas,
        'gasPrice': web3.eth.gas_price,
        'nonce': web3.eth.get_transaction_count(sender_address) + 1,
    })

    signed_tx_second = web3.eth.account.sign_transaction(tx_second, sender_private_key)
    web3.eth.send_raw_transaction(signed_tx_second.raw_transaction)
    
    transaction = router_contract.functions.addLiquidity(
        first_token_address,
        second_token_address,
        first_token_amount, 
        second_token_amount,
        0,
        0,
        sender_address,
        int(time.time()) + 10000
    ).build_transaction({
        'from': sender_address,
        'chainId': 56,
        'gas': 3000000,
        'gasPrice': web3.eth.gas_price,
        'nonce': web3.eth.get_transaction_count(sender_address) + 2,
    })

    signed_txn = web3.eth.account.sign_transaction(transaction, sender_private_key)
    txn_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
    
    print(f"Hash: {web3.to_hex(txn_hash)}")

def get_gas_price_in_usdt():
    bsc_urls = ["https://bsc-dataseed.binance.org/", "https://bsc-dataseed1.binance.org/", "https://bsc-dataseed2.binance.org/",
                "https://bsc-dataseed3.binance.org/",
                "https://bsc-dataseed4.binance.org/", "https://bsc-dataseed1.defibit.io/", "https://bsc-dataseed2.defibit.io/",
                "https://bsc-dataseed3.defibit.io/", "https://bsc-dataseed4.defibit.io/", "https://bsc-dataseed1.ninicoin.io/",
                "https://bsc-dataseed2.ninicoin.io/", "https://bsc-dataseed3.ninicoin.io/", "https://bsc-dataseed4.ninicoin.io/"]
    for url in bsc_urls:
        bsc_url = url
        web3 = Web3(Web3.HTTPProvider(bsc_url))
        if web3.is_connected():
            break

    gas_price_wei = web3.eth.gas_price
    gas_price_gwei = gas_price_wei / 1e9
    gas_price_bnb = (gas_price_gwei / 1e9) * 35000
    return float(gas_price_bnb)
