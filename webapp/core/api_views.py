import base64
import datetime as dt
from decimal import Decimal

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.request import Request
from django.contrib import auth, messages
from django.contrib.auth import authenticate
from drf_yasg.utils import swagger_auto_schema
from django.views.decorators.csrf import csrf_exempt

from .wallet.wallet import send_tokensBSC
from .blocks import get_current_or_create_open_block
from .wallet.wallet import (
    generate_ethereum_wallet,
    get_idea_balance,
    get_matter_balance,
    get_idea_info,
    get_matter_info,
    get_bnb_info,
    get_usdt_info,
    get_usdt_balance,
)
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    MakeBetSerializer,
    SellSerializer,
    TransactionSerializer,
    RemoveBetSerializer,
    WalletConnectSerializer,
    WalletAuthSerializer,
)
from .models import Block, UserProfile, Transaction, Bet, DepositTransaction
from django.contrib.auth.models import User
from .dex.dex import get_gas_price_in_usdt
from .wallet.signature_utils import (
    generate_auth_message,
    verify_signature,
    create_wallet_auth_challenge,
    verify_wallet_auth_challenge,
    is_valid_ethereum_address,
    normalize_address,
)
from .const import (
    APP_WALLET,
    APP_WALLET_PRIVATE_KEY,
    MATTER_TOKEN_ADDRESS,
    IDEA_TOKEN_ADDRESS,
    USDT_TOKEN_ADDRESS,
    DEPOSIT_ADDRESS_TRC20,
    DEPOSIT_ADDRESS_BSC,
    DEPOSIT_ADDRESS_TON,
    DEPOSIT_ADDRESS_BYBIT,
)
from .transaction_logger import log_wallet_added


@swagger_auto_schema(method="post", request_body=LoginSerializer)
@api_view(["POST"])
def login(request: Request) -> Response:
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    username = serializer.validated_data["username"]
    password = serializer.validated_data["password"]
    user = authenticate(request, username=username, password=password)
    basic_token = base64.b64encode(f"{username}:{password}".encode()).decode()

    if user is None:
        return Response(
            {"error": "Invalid username or password."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    auth.login(request, user)
    return Response(
        {
            "message": f"Successfully logged in as {user.username}.",
            "basic_token": f"Basic {basic_token}",
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
def logout(request: Request) -> Response:
    if request.user.is_anonymous:
        return Response(
            {"error": "You are not logged in."}, status=status.HTTP_400_BAD_REQUEST
        )

    auth.logout(request)
    return Response(
        {"message": "You have successfully logged out."}, status=status.HTTP_200_OK
    )


@swagger_auto_schema(method="post", request_body=RegisterSerializer)
@api_view(["POST"])
def register(request: Request) -> Response:
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    user = serializer.save()
    auth.login(request, user)

    user_profile = UserProfile.objects.get(user=user)

    wallet = generate_ethereum_wallet()

    user_profile.crypto_wallet_private_key = wallet["private_key"]
    user_profile.crypto_wallet_address = wallet["address"]

    user_profile.save()

    username = user.username
    password = request.data.get("password1")
    basic_token = base64.b64encode(f"{username}:{password}".encode()).decode()

    return Response(
        {
            "message": "User registered successfully",
            "username": user.username,
            "basic_token": f"Basic {basic_token}",
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def bets(request: Request) -> Response:
    try:
        # Get all bets (active and completed), limit to last 20
        bet_list = Bet.objects.filter(
            user=request.user, deleted_at__isnull=True
        ).order_by("-created_at")[:20]  # Newest first, limit 20
        bet_data = MakeBetSerializer(bet_list, many=True).data

        response_data = {
            "bet_list": bet_data,
        }
        return Response(response_data, status=status.HTTP_200_OK)
    except Exception as e:
        import traceback
        print(f"❌ ERROR in bets API: {str(e)}")
        print(f"❌ Traceback:\n{traceback.format_exc()}")
        return Response(
            {"error": f"Could not fetch bets: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@swagger_auto_schema(method="post", request_body=MakeBetSerializer)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_bet(request: Request) -> Response:
    # Декодируйте токен и получите wallet_address
    auth_token = request.headers.get('Authorization')
    print(f"🔐 Authorization token: {auth_token}")
    
    serializer = MakeBetSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Get user profile for balance checking
    user_profile = UserProfile.objects.get(user=request.user)
    
    # Get wallet address from request or use the one from profile
    wallet_address = serializer.validated_data.get('wallet_address') or user_profile.crypto_wallet_address
    print(f"👛 Wallet address: {wallet_address}")

    bet_size = float(serializer.validated_data["bet_size"])
    
    # Check internal USDT balance (from deposits)
    internal_usdt_balance = float(user_profile.usdt_balance)
    
    if bet_size > internal_usdt_balance:
        return Response(
            {"error": f"Insufficient balance. Your balance: {internal_usdt_balance} USDT, Bet size: {bet_size} USDT"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Get token prices for bet calculation
        matter_info = get_matter_info(wallet_address)
        idea_info = get_idea_info(wallet_address)
        
        matter_price = float(matter_info.get("usd_price", 0) or 0) if matter_info else 0
        idea_price = float(idea_info.get("usd_price", 0) or 0) if idea_info else 0
        
        print(f"📊 Token prices: MATTER=${matter_price}, IDEA=${idea_price}")
        
        # Avoid division by zero
        if matter_price > 0:
            cur_ratio = idea_price / matter_price
        else:
            cur_ratio = 0
            
        bet_ratio = (
            1 + float(serializer.validated_data["bet_percent"]) / 100
        ) * cur_ratio

        bet = serializer.save(
            user=request.user,
            start_matter_price=matter_price,
            start_idea_price=idea_price,
            bet_ratio=bet_ratio if bet_ratio else 0,
        )

        # Deduct bet amount from user's internal USDT balance
        from decimal import Decimal
        user_profile.usdt_balance -= Decimal(str(bet_size))
        user_profile.save()
        
        print(f"✅ Bet created successfully!")
        print(f"   User: {request.user.username}")
        print(f"   Amount: {bet.bet_size} USDT")
        print(f"   New balance: {user_profile.usdt_balance} USDT")

        Transaction.objects.create(
            user=request.user,
            amount=bet.bet_size,
            type=1,
            from_wallet=wallet_address,
            to_wallet=APP_WALLET,
            bet=bet,
            block=get_current_or_create_open_block(),
        )

        return Response(MakeBetSerializer(bet).data, status=status.HTTP_201_CREATED)

    except Exception as e:
        import traceback
        print(f"❌ ERROR in create_bet: {str(e)}")
        print(f"❌ Full traceback:\n{traceback.format_exc()}")
        return Response(
            {"error": f"Failed to load matter and idea price or process bet: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@swagger_auto_schema(method="post", request_body=RemoveBetSerializer)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def remove_bet(request: Request) -> Response:
    user_profile = UserProfile.objects.get(user=request.user)
    wallet_address = user_profile.crypto_wallet_address
    
    bet_id = request.data.get("removed_bet_id")

    if not bet_id or not Bet.objects.filter(id=bet_id).exists():
        return Response(
            {"error": "Invalid bet ID."}, status=status.HTTP_400_BAD_REQUEST
        )

    bet = Bet.objects.get(id=bet_id)
    if bet.user != request.user or bet.deleted_at is not None:
        return Response(
            {"error": "Unauthorized access or bet already deleted."},
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        gas_price = get_gas_price_in_usdt()
        bnb_info = get_bnb_info(wallet_address)
        bnb_balance = float(bnb_info["balance_formatted"] if bnb_info else 0)

        send_tokensBSC(
            APP_WALLET_PRIVATE_KEY,
            wallet_address,
            USDT_TOKEN_ADDRESS,
            float(bet.bet_size),
        )

        bet.soft_delete()

        Transaction.objects.create(
            user=request.user,
            amount=bet.bet_size,
            type=0,
            from_wallet=APP_WALLET,
            to_wallet=wallet_address,
            block=get_current_or_create_open_block(),
        )

        idea_info = get_idea_info(wallet_address)
        matter_info = get_matter_info(wallet_address)
        matter_balance = float(matter_info["balance_formatted"] if matter_info else 0)
        idea_balance = float(idea_info["balance_formatted"] if idea_info else 0)
        bet_list = Bet.objects.filter(
            user=request.user, deleted_at__isnull=True, is_active=True
        ).order_by("created_at")

        return Response(
            {
                "message": "Bet removed successfully.",
                "bet_ratio": bet.bet_ratio,
                "bet_percent": bet.bet_percent,
                "gas_price": gas_price,
                "bet_list": bet_list,
                "user_matter_balance": matter_balance,
                "user_idea_balance": idea_balance,
                "user_bnb_balance": bnb_balance,
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response(
            {"error": f"Error: Webapp balance is low or transaction failed."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def transaction_history(request: Request) -> Response:
    transaction_list = Transaction.objects.filter(user=request.user).order_by(
        "created_at"
    )

    serializer = TransactionSerializer(transaction_list, many=True)

    return Response(serializer.data, status=status.HTTP_200_OK)


@swagger_auto_schema(method="post", request_body=SellSerializer)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def sell(request: Request) -> Response:
    serializer = SellSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    user_profile = UserProfile.objects.get(user=request.user)
    token_name = serializer.validated_data["tokens"]
    wallet_address = serializer.validated_data["wallet_address"]
    amount = float(serializer.validated_data["amount"])

    if token_name == "MATTER":
        token_address = MATTER_TOKEN_ADDRESS
    elif token_name == "IDEA":
        token_address = IDEA_TOKEN_ADDRESS
    else:
        return Response(
            {"error": "Invalid token type."}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        send_tokensBSC(
            user_profile.crypto_wallet_private_key,
            wallet_address,
            token_address,
            amount,
        )

        Transaction.objects.create(
            user=request.user,
            amount=amount,
            type=0,
            from_wallet=user_profile.crypto_wallet_address,
            to_wallet=wallet_address,
            block=get_current_or_create_open_block(),
        )

        return Response(
            {"message": "Tokens sent successfully."}, status=status.HTTP_200_OK
        )

    except Exception as e:
        return Response(
            {"error": "Transaction failed."}, status=status.HTTP_400_BAD_REQUEST
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def profile(request: Request) -> Response:
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        
        # Use internal USDT balance only (from deposits)
        usdt_deposit_balance = float(user_profile.usdt_balance)
        total_balance_in_usdt = usdt_deposit_balance

        # Calculate total winnings from winning bets
        winning_bets = Bet.objects.filter(user=request.user, is_winning=True, deleted_at__isnull=True)
        total_winnings = sum(float(bet.bet_size) for bet in winning_bets)

        data = {
            "user": request.user.username,
            "matter_balance": 0,
            "idea_balance": 0,
            "bnb_price": 0,
            "bnb_balance": 0,
            "matter_balance_in_usdt": 0,
            "idea_balance_in_usdt": 0,
            "bnb_balance_in_usdt": 0,
            "wallet_balance": 0,
            "wallet_balance_in_usdt": 0,
            "usdt_deposit_balance": usdt_deposit_balance,
            "total_balance_in_usdt": total_balance_in_usdt,
            "total_winnings": total_winnings,
            "wallet_address": user_profile.crypto_wallet_address,
            "ton_wallet_address": user_profile.ton_wallet_address,
            "private_key": user_profile.crypto_wallet_private_key,
        }

        return Response(data, status=status.HTTP_200_OK)

    except Exception as e:
        import traceback
        print(f"❌ ERROR in profile API: {str(e)}")
        print(f"❌ Traceback:\n{traceback.format_exc()}")
        return Response(
            {"error": f"Could not fetch profile: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def block_timer(request: Request) -> Response:
    """
    Возвращает оставшееся время до закрытия текущего блока
    """
    try:
        import time
        import os
        
        # Читаем время следующего блока из файла
        # Путь внутри Docker контейнера
        next_block_file = "/app/webapp/next_block_sync.txt"
        
        # Fallback для локальной разработки
        if not os.path.exists(next_block_file):
            next_block_file = "/var/www/liquidity-master/next_block_sync.txt"
        
        if os.path.exists(next_block_file):
            with open(next_block_file, "r") as f:
                next_block_time = int(f.read().strip())
            
            current_time = int(time.time() * 1000)
            time_left_ms = max(0, next_block_time - current_time)
            time_left_seconds = int(time_left_ms / 1000)
            
            return Response({
                "time_left_seconds": time_left_seconds,
                "next_block_timestamp": next_block_time,
                "current_timestamp": current_time
            }, status=status.HTTP_200_OK)
        else:
            # Если файл не существует, возвращаем дефолтное время (10 минут)
            return Response({
                "time_left_seconds": 600,
                "next_block_timestamp": int(time.time() * 1000) + 600000,
                "current_timestamp": int(time.time() * 1000)
            }, status=status.HTTP_200_OK)
            
    except Exception as e:
        import traceback
        print(f"❌ ERROR in block_timer API: {str(e)}")
        print(f"❌ Traceback:\n{traceback.format_exc()}")
        return Response(
            {"error": f"Could not fetch block timer: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def save_wallet_address(request: Request) -> Response:
    """
    Сохраняет адрес кошелька пользователя для автоматического зачисления депозитов
    Body: { "wallet_address": "0x..." или "T..." }
    """
    try:
        wallet_address = request.data.get('wallet_address', '').strip()
        
        if not wallet_address or len(wallet_address) < 10:
            return Response(
                {"error": "Invalid wallet address"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Нормализуем адрес (lowercase для Ethereum/BSC, as-is для Tron)
        if wallet_address.startswith('0x'):
            wallet_address = wallet_address.lower()

        # Проверяем, не привязан ли кошелёк к другому аккаунту
        existing_profile = UserProfile.objects.filter(
            crypto_wallet_address__iexact=wallet_address
        ).exclude(user=request.user).first()

        if existing_profile:
            return Response(
                {"error": "This wallet is already connected to another account"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user_profile = UserProfile.objects.get(user=request.user)
        old_address = user_profile.crypto_wallet_address
        user_profile.crypto_wallet_address = wallet_address
        user_profile.save()

        wallet_type = 'BSC/ETH' if wallet_address.startswith('0x') else 'TRON'

        print(f"")
        print(f"{'='*60}")
        print(f"[WALLET] КОШЕЛЕК ДОБАВЛЕН")
        print(f"{'='*60}")
        print(f"  Пользователь: {request.user.username} (ID: {request.user.id})")
        print(f"  Новый адрес:  {wallet_address}")
        print(f"  Старый адрес: {old_address or 'не было'}")
        print(f"  Тип:          {wallet_type}")
        print(f"{'='*60}")
        print(f"")

        # Пишем в файл лога
        log_wallet_added(
            username=request.user.username,
            user_id=request.user.id,
            wallet_address=wallet_address,
            old_address=old_address,
            wallet_type=wallet_type
        )
        
        return Response({
            "success": True,
            "message": "Wallet address saved successfully",
            "wallet_address": wallet_address
        }, status=status.HTTP_200_OK)
        
    except UserProfile.DoesNotExist:
        return Response(
            {"error": "User profile not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        print(f"❌ Error saving wallet address: {str(e)}")
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def save_ton_wallet_address(request: Request) -> Response:
    """
    Сохраняет TON адрес кошелька пользователя для автоматического зачисления депозитов
    Body: { "ton_wallet_address": "EQ..." или "UQ..." }
    """
    try:
        ton_wallet_address = request.data.get('ton_wallet_address', '').strip()
        
        # Валидация TON адреса
        if not ton_wallet_address:
            return Response(
                {"error": "TON wallet address is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем что адрес начинается с EQ или UQ и имеет правильную длину
        if not (ton_wallet_address.startswith('EQ') or ton_wallet_address.startswith('UQ')):
            return Response(
                {"error": "Invalid TON address format. Address must start with EQ or UQ"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(ton_wallet_address) != 48:
            return Response(
                {"error": f"Invalid TON address length. Expected 48 characters, got {len(ton_wallet_address)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Дополнительная валидация через pytoniq
        try:
            from pytoniq_core import Address as TonAddress
            # Пытаемся создать объект Address - если адрес невалидный, выбросит исключение
            TonAddress(ton_wallet_address)
        except Exception as e:
            return Response(
                {"error": f"Invalid TON address: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Проверяем, не привязан ли кошелёк к другому аккаунту
        existing_profile = UserProfile.objects.filter(
            ton_wallet_address__iexact=ton_wallet_address
        ).exclude(user=request.user).first()

        if existing_profile:
            return Response(
                {"error": "This TON wallet is already connected to another account"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user_profile = UserProfile.objects.get(user=request.user)
        old_address = user_profile.ton_wallet_address
        user_profile.ton_wallet_address = ton_wallet_address
        user_profile.save()

        print(f"")
        print(f"{'='*60}")
        print(f"[WALLET] TON КОШЕЛЕК ДОБАВЛЕН")
        print(f"{'='*60}")
        print(f"  Пользователь: {request.user.username} (ID: {request.user.id})")
        print(f"  Новый адрес:  {ton_wallet_address}")
        print(f"  Старый адрес: {old_address or 'не было'}")
        print(f"  Тип:          TON")
        print(f"{'='*60}")
        print(f"")

        # Пишем в файл лога
        log_wallet_added(
            username=request.user.username,
            user_id=request.user.id,
            wallet_address=ton_wallet_address,
            old_address=old_address,
            wallet_type="TON"
        )
        
        return Response({
            "success": True,
            "message": "TON wallet address saved successfully",
            "ton_wallet_address": ton_wallet_address
        }, status=status.HTTP_200_OK)
        
    except UserProfile.DoesNotExist:
        return Response(
            {"error": "User profile not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        print(f"❌ Error saving TON wallet address: {str(e)}")
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def withdraw(request: Request) -> Response:
    """
    Withdraw USDT from user's internal balance to external wallet
    Body: { "amount": float, "address": str, "network": str }
    """
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        
        # Parse and validate amount
        try:
            amount_raw = request.data.get('amount')
            if not amount_raw:
                return Response(
                    {"error": "Сумма не указана"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            amount = Decimal(str(amount_raw))
        except (ValueError, TypeError, ArithmeticError):
            return Response(
                {"error": "Некорректная сумма"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        address = request.data.get('address', '').strip()
        network = request.data.get('network', 'TRC20').upper()  # TRC20, BSC, TON
        
        # Validation
        if amount <= 0:
            return Response(
                {"error": "Сумма должна быть больше нуля"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not address or len(address) < 10:
            return Response(
                {"error": "Некорректный адрес кошелька"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check balance
        if amount > user_profile.usdt_balance:
            return Response(
                {"error": f"Недостаточно средств. Баланс: {user_profile.usdt_balance} USDT"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Minimum withdrawal amount
        MIN_WITHDRAW = Decimal('0.001')
        if amount < MIN_WITHDRAW:
            return Response(
                {"error": f"Минимальная сумма вывода: {MIN_WITHDRAW} USDT"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Send actual blockchain transaction
        from .withdrawal import send_usdt_trc20, send_usdt_bsc, send_usdt_ton
        
        if network == 'TRC20':
            result = send_usdt_trc20(address, amount)
        elif network == 'BSC':
            result = send_usdt_bsc(address, amount)
        elif network == 'TON':
            result = send_usdt_ton(address, amount)
        else:
            return Response(
                {"error": f"Network {network} not supported"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not result.get('success'):
            return Response(
                {"error": f"Blockchain error: {result.get('error')}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Deduct from user balance after successful transaction
        user_profile.usdt_balance -= amount
        user_profile.save()
        
        tx_id = result.get('tx_id', '')
        explorer_url = result.get('explorer_url', '')
        
        return Response({
            "success": True,
            "message": f"Вывод {amount} USDT успешно отправлен!",
            "tx_id": tx_id,
            "explorer_url": explorer_url,
            "new_balance": float(user_profile.usdt_balance)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        import traceback
        print(f"❌ ERROR in withdraw API: {str(e)}")
        print(f"❌ Traceback:\n{traceback.format_exc()}")
        return Response(
            {"error": f"Ошибка при выводе: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def private_key(request: Request) -> Response:
    user_profile = UserProfile.objects.get(user=request.user)

    data = {
        "username": request.user.username,
        "crypto_wallet_private_key": user_profile.crypto_wallet_private_key,
    }
    return Response(data, status=status.HTTP_200_OK)


@api_view(["GET"])
def token_price_history(request: Request):
    from_timestamp = dt.datetime.fromtimestamp(int(request.query_params["from"]))
    to_timestamp = dt.datetime.fromtimestamp(int(request.query_params["to"]))

    blocks = list(
        Block.objects.filter(
            created_at__gte=from_timestamp, created_at__lte=to_timestamp
        ).order_by("created_at")
    )

    idea_prices = [{str(block.created_at): float(block.idea_price)} for block in blocks]
    data = {
        "idea_prices": idea_prices,
    }
    return Response(data, status=status.HTTP_200_OK)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@csrf_exempt
def wallet_auth_challenge(request: Request) -> Response:
    """
    Generate authentication challenge for wallet connection
    """
    wallet_address = request.data.get('wallet_address')
    
    if not wallet_address:
        return Response(
            {"error": "Wallet address is required."}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not is_valid_ethereum_address(wallet_address):
        return Response(
            {"error": "Invalid wallet address format."}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        challenge = create_wallet_auth_challenge(wallet_address)
        return Response(challenge, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": "Failed to create authentication challenge."}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@swagger_auto_schema(method="post", request_body=WalletAuthSerializer)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@csrf_exempt
def wallet_connect(request: Request) -> Response:
    """
    Connect wallet to current authenticated user
    """
    serializer = WalletAuthSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    wallet_address = serializer.validated_data['wallet_address']
    signature = serializer.validated_data['signature']
    message = serializer.validated_data['message']
    
    try:
        print(f"Wallet connect attempt: {wallet_address}")
        print(f"Signature: {signature}")
        print(f"Message: {message}")
        
        # Verify signature
        signature_valid = verify_signature(wallet_address, signature, message)
        print(f"Signature valid: {signature_valid}")
        
        if not signature_valid:
            return Response(
                {"error": "Invalid signature."}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Do not modify user's stored wallet; just acknowledge connection
        return Response({
            "message": "Wallet connection verified for your session.",
            "user": request.user.username,
            "wallet_address": wallet_address,
            "is_existing_user": True
        }, status=status.HTTP_200_OK)
            
    except Exception as e:
        print(f"Wallet connect error: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response(
            {"error": f"Failed to connect wallet: {str(e)}"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_wallet_address(request: Request) -> Response:
    """
    Update user's wallet address (for existing users)
    """
    serializer = WalletAuthSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    wallet_address = serializer.validated_data['wallet_address']
    signature = serializer.validated_data['signature']
    message = serializer.validated_data['message']
    
    try:
        # Verify signature
        if not verify_signature(wallet_address, signature, message):
            return Response(
                {"error": "Invalid signature."}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Check if wallet is already used by another user
        if UserProfile.objects.filter(crypto_wallet_address=wallet_address).exclude(user=request.user).exists():
            return Response(
                {"error": "This wallet is already connected to another account."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update user profile
        user_profile = UserProfile.objects.get(user=request.user)
         
        return Response({
            "message": "External wallet verified for your session.",
            "wallet_address": wallet_address,
            "original_wallet": user_profile.crypto_wallet_address
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {"error": "Failed to update wallet address."}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def wallet_balance(request: Request) -> Response:
    """
    Get wallet balance for connected wallet
    """
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        
        # Получаем баланс BNB основного кошелька
        wallet_bnb_info = get_bnb_info(user_profile.crypto_wallet_address)
        if wallet_bnb_info:
            wallet_balance = float(wallet_bnb_info["balance_formatted"])
            wallet_price = float(wallet_bnb_info["usd_price"]) if wallet_bnb_info["usd_price"] else 0
            wallet_balance_usdt = round(wallet_balance * wallet_price, 8)
        else:
            wallet_balance = 0
            wallet_balance_usdt = 0
        
        return Response({
            'is_connected': True,
            'balance': wallet_balance,
            'balance_usdt': wallet_balance_usdt,
            'address': user_profile.crypto_wallet_address
        })
        
    except UserProfile.DoesNotExist:
        return Response({
            'is_connected': False,
            'balance': 0,
            'balance_usdt': 0,
            'message': 'User profile not found'
        }, status=404)
    except Exception as e:
        return Response({
            'is_connected': False,
            'balance': 0,
            'balance_usdt': 0,
            'message': f'Error: {str(e)}'
        }, status=500)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def wallet_status(request: Request) -> Response:
    """
    Get current wallet connection status
    """
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        
        data = {
            "is_connected": bool(user_profile.crypto_wallet_address),
            "wallet_address": user_profile.crypto_wallet_address,
            "main_wallet_address": user_profile.crypto_wallet_address,
            "is_external_wallet": user_profile.crypto_wallet_private_key is None
        }
        
        return Response(data, status=status.HTTP_200_OK)
        
    except UserProfile.DoesNotExist:
        return Response(
            {"error": "User profile not found."}, 
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def deposit_addresses(request: Request) -> Response:
    """
    Get deposit addresses for different networks
    """
    try:
        data = {
            "trc20": DEPOSIT_ADDRESS_TRC20,
            "bsc": DEPOSIT_ADDRESS_BSC,
            "ton": DEPOSIT_ADDRESS_TON,
            "bybit": DEPOSIT_ADDRESS_BYBIT if DEPOSIT_ADDRESS_BYBIT else "",
        }
        
        return Response(data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {"error": f"Failed to get deposit addresses: {str(e)}"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def deposit_history(request: Request) -> Response:
    """
    Get deposit history for current user
    """
    try:
        deposits = DepositTransaction.objects.filter(
            user=request.user
        ).order_by('-created_at')[:20]
        
        data = []
        for deposit in deposits:
            data.append({
                "id": str(deposit.id),
                "amount": float(deposit.amount),
                "network": deposit.network,
                "status": deposit.status,
                "tx_hash": deposit.tx_hash,
                "confirmations": deposit.confirmations,
                "created_at": deposit.created_at.isoformat(),
                "confirmed_at": deposit.confirmed_at.isoformat() if deposit.confirmed_at else None,
                "credited_at": deposit.credited_at.isoformat() if deposit.credited_at else None,
            })
        
        return Response(data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {"error": f"Failed to get deposit history: {str(e)}"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def pending_deposits(request: Request) -> Response:
    """
    Get pending deposits waiting for confirmation
    """
    try:
        # Находим неподтвержденные депозиты от адреса пользователя
        user_profile = UserProfile.objects.get(user=request.user)
        
        pending = DepositTransaction.objects.filter(
            from_address__iexact=user_profile.crypto_wallet_address,
            status__in=[DepositTransaction.StatusType.PENDING, DepositTransaction.StatusType.CONFIRMED]
        ).order_by('-created_at')
        
        data = []
        for deposit in pending:
            data.append({
                "id": str(deposit.id),
                "amount": float(deposit.amount),
                "network": deposit.network,
                "status": deposit.status,
                "tx_hash": deposit.tx_hash,
                "confirmations": deposit.confirmations,
                "created_at": deposit.created_at.isoformat(),
            })
        
        return Response(data, status=status.HTTP_200_OK)
        
    except UserProfile.DoesNotExist:
        return Response([], status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Failed to get pending deposits: {str(e)}"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



@api_view(["POST"])
@permission_classes([IsAuthenticated])
def game_earn(request: Request) -> Response:
    """
    Add earnings from games to user's USDT balance
    Body: { "amount": float }
    """
    try:
        amount_raw = request.data.get('amount')
        if not amount_raw:
            return Response(
                {"error": "Amount is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            amount = Decimal(str(amount_raw))
        except (ValueError, TypeError):
            return Response(
                {"error": "Invalid amount"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate amount (max 10 USDT per game session to prevent abuse)
        if amount <= 0 or amount > 10:
            return Response(
                {"error": "Invalid amount. Must be between 0 and 10 USDT"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user_profile = UserProfile.objects.get(user=request.user)
        user_profile.usdt_balance += amount
        user_profile.save()
        
        print(f"🎮 Game earnings: User {request.user.username} earned {amount} USDT. New balance: {user_profile.usdt_balance}")
        
        return Response({
            "success": True,
            "earned": float(amount),
            "new_balance": float(user_profile.usdt_balance)
        }, status=status.HTTP_200_OK)
        
    except UserProfile.DoesNotExist:
        return Response(
            {"error": "User profile not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        import traceback
        print(f"❌ ERROR in game_earn API: {str(e)}")
        print(f"❌ Traceback:\n{traceback.format_exc()}")
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
