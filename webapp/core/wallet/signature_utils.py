import hashlib
import secrets
from eth_account.messages import encode_defunct
from eth_account import Account
from web3 import Web3
import time


def generate_auth_message(wallet_address, timestamp=None):
    """
    Generate a message for wallet authentication
    """
    if timestamp is None:
        timestamp = int(time.time())
    
    message = f"Welcome to Liquidity!\n\nPlease sign this message to authenticate your wallet.\n\nWallet: {wallet_address}\nTimestamp: {timestamp}"
    return message, timestamp


def verify_signature(wallet_address, signature, message):
    """
    Verify that the signature was created by the wallet owner
    """
    try:
        # Encode the message
        message_hash = encode_defunct(text=message)
        
        # Recover the address from the signature
        recovered_address = Account.recover_message(message_hash, signature=signature)
        
        # Compare addresses (case insensitive)
        return recovered_address.lower() == wallet_address.lower()
    except Exception as e:
        print(f"Signature verification error: {e}")
        return False


def generate_nonce():
    """
    Generate a random nonce for additional security
    """
    return secrets.token_hex(32)


def create_wallet_auth_challenge(wallet_address):
    """
    Create a challenge for wallet authentication
    """
    nonce = generate_nonce()
    timestamp = int(time.time())
    
    message = f"Liquidity Authentication\n\nWallet: {wallet_address}\nNonce: {nonce}\nTimestamp: {timestamp}"
    
    return {
        'message': message,
        'nonce': nonce,
        'timestamp': timestamp,
        'wallet_address': wallet_address
    }


def verify_wallet_auth_challenge(wallet_address, signature, challenge_data):
    """
    Verify wallet authentication challenge
    """
    try:
        # Check if the challenge is not too old (5 minutes)
        current_time = int(time.time())
        if current_time - challenge_data['timestamp'] > 300:
            return False, "Challenge expired"
        
        # Verify signature
        if not verify_signature(wallet_address, signature, challenge_data['message']):
            return False, "Invalid signature"
        
        return True, "Success"
    except Exception as e:
        return False, f"Verification error: {str(e)}"


def is_valid_ethereum_address(address):
    """
    Check if the address is a valid Ethereum address
    """
    try:
        return Web3.is_address(address)
    except:
        return False


def normalize_address(address):
    """
    Normalize Ethereum address to checksum format
    """
    try:
        return Web3.to_checksum_address(address)
    except:
        return address.lower()
