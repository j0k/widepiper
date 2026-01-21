from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.contrib import auth
from django.contrib.auth import authenticate
from django.contrib import messages

from .wallet.wallet import send_tokensBSC

from .blocks import get_current_or_create_open_block
from .wallet.wallet import (
    generate_ethereum_wallet,
    get_idea_balance,
    get_matter_balance,
    get_idea_info,
    get_matter_info,
    get_bnb_info,
)
from .forms import (
    LoginForm,
    MakeBetForm,
    RegisterForm,
    SellForm,
)
from .models import UserProfile, Transaction, Bet
from .dex.dex import get_gas_price_in_usdt
from .const import (
    APP_WALLET,
    APP_WALLET_PRIVATE_KEY,
    MATTER_TOKEN_ADDRESS,
    IDEA_TOKEN_ADDRESS,
)


def index(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("bet")

    return render(request, "index.html")


def login(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("bet")

    if request.method == "GET":
        form = LoginForm()
        context = {"form": form}
        return render(request, "login.html", context)

    if request.method == "POST":
        form = LoginForm(request.POST)
        if not form.is_valid():
            context = {"form": form}
            return render(request, "login.html", context)

        username = form.cleaned_data["username"]
        password = form.cleaned_data["password"]
        user = authenticate(request, username=username, password=password)

        if user is None:  # Probably redundant
            messages.error(request, "Invalid username or password.")
            context = {"form": form}
            return render(request, "login.html", context)

        auth.login(request, form.get_user())
        messages.success(
            request, f"You have logged in successfully as {user.get_username()}."
        )
        return redirect("bet")

    raise Exception("Recieved unsupported http method")


def logout(request: HttpRequest) -> HttpResponse:
    if request.user.is_anonymous:
        messages.error(request, "You are not logged in.")
        return redirect("/")

    auth.logout(request)
    messages.success(request, "You have successfully logged out.")
    return redirect("/")


def register(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("bet")

    if request.method == "GET":
        context = {"form": RegisterForm()}
        return render(request, "register.html", context)

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if not form.is_valid():
            context = {"form": form}
            return render(request, "register.html", context)

        user = form.save(commit=False)
        # user.username = user.username.lower()
        user.save()

        messages.success(request, "You have singed up successfully.")
        auth.login(request, user)

        user_profile = UserProfile.objects.get(user=user)

        wallet = generate_ethereum_wallet()

        user_profile.crypto_wallet_private_key = wallet["private_key"]
        user_profile.crypto_wallet_address = wallet["address"]

        user_profile.save()

        return redirect("bet")

    raise Exception("Recieved unsupported http method")


def bets(request: HttpRequest) -> HttpResponse:
    if request.user.is_anonymous:
        return redirect("/")

    if request.method == "GET":
        user_profile = UserProfile.objects.get(user=request.user)
        idea_info = get_idea_info(user_profile.crypto_wallet_address)
        matter_info = get_matter_info(user_profile.crypto_wallet_address)

        matter_balance = float(
            matter_info["balance_formatted"] if matter_info is not None else 0
        )
        idea_balance = float(
            idea_info["balance_formatted"] if idea_info is not None else 0
        )

        make_bet_form = MakeBetForm()
        bet_list1 = Bet.objects.filter(
            user=request.user, deleted_at__isnull=True, is_active=True
        ).order_by("created_at")
        user_profile = UserProfile.objects.get(user=request.user)
        gas_price = get_gas_price_in_usdt()
        bnb_info = get_bnb_info(user_profile.crypto_wallet_address)
        bnb_balance = float(
            bnb_info["balance_formatted"] if bnb_info is not None else 0
        )
        get_bnb_info(APP_WALLET)
        context = {
            "app_wallet": get_bnb_info(APP_WALLET)["balance_formatted"],
            "gas_price": gas_price,
            "make_bet_form": make_bet_form,
            "bet_list": bet_list1,
            "user_matter_balance": matter_balance,
            "user_idea_balance": idea_balance,
            "user_bnb_balance": bnb_balance,
        }
        return render(request, "bet.html", context)

    raise Exception("Recieved unsupported http method")


def create_bet(request: HttpRequest) -> HttpResponse:  # TODO: Add bet_ratio field
    if request.user.is_anonymous:
        return redirect("/")

    if request.method == "POST":
        make_bet_form = MakeBetForm(request.POST)
        bet_list = Bet.objects.filter(
            user=request.user, deleted_at__isnull=True, is_active=True
        ).order_by("created_at")

        user_profile = UserProfile.objects.get(user=request.user)
        idea_info = get_idea_info(user_profile.crypto_wallet_address)
        matter_info = get_matter_info(user_profile.crypto_wallet_address)
        gas_price = get_gas_price_in_usdt()

        matter_balance = float(
            matter_info["balance_formatted"] if matter_info is not None else 0
        )
        idea_balance = float(
            idea_info["balance_formatted"] if idea_info is not None else 0
        )

        bnb_info = get_bnb_info(user_profile.crypto_wallet_address)
        bnb_balance = float(
            bnb_info["balance_formatted"] if bnb_info is not None else 0
        )

        if not make_bet_form.is_valid():
            context = {
                "gas_price": gas_price,
                "make_bet_form": make_bet_form,
                "bet_list": bet_list,
                "user_matter_balance": matter_balance,
                "user_idea_balance": idea_balance,
                "user_bnb_balance": bnb_balance,
            }
            return render(request, "bet.html", context)

        if float(make_bet_form.cleaned_data["bet_size"]) > matter_balance:
            make_bet_form.add_error("bet_size", "Bet is bigger than avaliable balance.")
            context = {
                "gas_price": gas_price,
                "make_bet_form": make_bet_form,
                "bet_list": bet_list,
                "user_matter_balance": matter_balance,
                "user_idea_balance": idea_balance,
                "user_bnb_balance": bnb_balance,
            }
            return render(request, "bet.html", context)

        bet: Bet = make_bet_form.save(commit=False)

        try:
            idea_info = get_idea_info(user_profile.crypto_wallet_address)
            matter_info = get_matter_info(user_profile.crypto_wallet_address)

            matter_price = matter_info["usd_price"] if matter_info is not None else 0
            if matter_price == None:
                matter_price = 0
            else:
                matter_price = float(matter_price)

            idea_price = idea_info["usd_price"] if idea_info is not None else 0
            if idea_price == None:
                idea_price = 0
            else:
                idea_price = float(idea_price)

            bet.start_matter_price = matter_price
            bet.start_idea_price = idea_price

            cur_ratio = idea_price / matter_price

            bet.bet_ratio = (1 + float(bet.bet_percent) / 100) * cur_ratio
        except:
            messages.error(request, "Failed to load matter and idea price.")
            context = {
                "gas_price": gas_price,
                "make_bet_form": make_bet_form,
                "bet_list": bet_list,
                "user_matter_balance": matter_balance,
                "user_idea_balance": idea_balance,
                "user_bnb_balance": bnb_balance,
            }
            return render(request, "bet.html", context)

        try:
            send_tokensBSC(
                user_profile.crypto_wallet_private_key,
                APP_WALLET,
                MATTER_TOKEN_ADDRESS,
                float(bet.bet_size),
            )
        except:
            make_bet_form.add_error(
                "bet_size", "You do not have enough BNB to pay for gas."
            )
            context = {

                "gas_price": gas_price,
                "make_bet_form": make_bet_form,
                "bet_list": bet_list,
                "user_matter_balance": matter_balance,
                "user_idea_balance": idea_balance,
                "user_bnb_balance": bnb_balance,
            }
            return render(request, "bet.html", context)

        bet.user = request.user
        bet.save()

        user_profile = UserProfile.objects.get(user=request.user)

        Transaction.objects.create(
            user=request.user,
            amount=bet.bet_size,
            type=1,
            from_wallet=user_profile.crypto_wallet_address,
            to_wallet=APP_WALLET,
            bet=bet,
            block=get_current_or_create_open_block(),
        )

        return redirect("/bet")

    raise Exception("Recieved unsupported http method")


def remove_bet(request: HttpRequest) -> HttpResponse:
    if request.user.is_anonymous:
        return redirect("/")

    if request.method == "POST":
        make_bet_form = MakeBetForm()
        bet_list = Bet.objects.filter(
            user=request.user, deleted_at__isnull=True, is_active=True
        ).order_by("created_at")
        user_profile = UserProfile.objects.get(user=request.user)
        user_matter_balance = get_matter_balance(user_profile.crypto_wallet_address)
        user_idea_balance = get_idea_balance(user_profile.crypto_wallet_address)
        gas_price = get_gas_price_in_usdt()
        bnb_info = get_bnb_info(user_profile.crypto_wallet_address)
        bnb_balance = float(
            bnb_info["balance_formatted"] if bnb_info is not None else 0
        )

        bet_id = request.POST["removed_bet_id"]
        if (
                not Bet.objects.filter(id=bet_id).exists()
                or Bet.objects.get(id=bet_id).deleted_at is not None
        ):
            errors = ["Unexpected error: invalid bet id."]
            context = {
                "gas_price": gas_price,
                "make_bet_form": make_bet_form,
                "bet_list": bet_list,
                "user_matter_balance": user_matter_balance,
                "user_idea_balance": user_idea_balance,
                "errors": errors,
                "user_bnb_balance": bnb_balance,
            }
            return render(request, "bet.html", context)

        bet = Bet.objects.get(id=bet_id)
        if bet.user != request.user:
            errors = ["Unexpected error: unauthorized access."]
            context = {
                "gas_price": gas_price,
                "make_bet_form": make_bet_form,
                "bet_list": bet_list,
                "user_matter_balance": user_matter_balance,
                "user_idea_balance": user_idea_balance,
                "errors": errors,
                "user_bnb_balance": bnb_balance,
            }
            return render(request, "bet.html", context)

        try:
            user_profile = UserProfile.objects.get(user=request.user)
            send_tokensBSC(
                APP_WALLET_PRIVATE_KEY,
                user_profile.crypto_wallet_address,
                MATTER_TOKEN_ADDRESS,
                float(bet.bet_size),
            )

            bet.soft_delete()

            Transaction.objects.create(
                user=request.user,
                amount=bet.bet_size,
                type=0,
                from_wallet=APP_WALLET,
                to_wallet=user_profile.crypto_wallet_address,
                block=get_current_or_create_open_block(),
            )

            user_profile = UserProfile.objects.get(user=request.user)
            idea_info = get_idea_info(user_profile.crypto_wallet_address)
            matter_info = get_matter_info(user_profile.crypto_wallet_address)

            matter_balance = float(
                matter_info["balance_formatted"] if matter_info is not None else 0
            )
            idea_balance = float(
                idea_info["balance_formatted"] if idea_info is not None else 0
            )

            make_bet_form = MakeBetForm()
            bet_list = Bet.objects.filter(
                user=request.user, deleted_at__isnull=True, is_active=True
            ).order_by("created_at")
            user_profile = UserProfile.objects.get(user=request.user)
            context = {
                "bet_ratio": bet.bet_ratio,
                "bet_percent": bet.bet_percent,
                "gas_price": gas_price,
                "make_bet_form": make_bet_form,
                "bet_list": bet_list,
                "user_matter_balance": matter_balance,
                "user_idea_balance": idea_balance,
                "user_bnb_balance": bnb_balance,
            }
            return render(request, "bet.html", context)
        except:
            errors = ["Error: Webapp balance is low."]
            context = {
                "gas_price": gas_price,
                "make_bet_form": make_bet_form,
                "bet_list": bet_list,
                "user_matter_balance": user_matter_balance,
                "user_idea_balance": user_idea_balance,
                "errors": errors,
                "user_bnb_balance": bnb_balance,
            }
            return render(request, "bet.html", context)

    raise Exception("Recieved unsupported http method")


def transaction_history(request: HttpRequest) -> HttpResponse:
    if request.user.is_anonymous:
        return redirect("/")

    if request.method == "GET":
        context = {
            "transaction_list": Transaction.objects.filter(user=request.user).order_by(
                "created_at"
            )
        }
        return render(request, "transaction_history.html", context)

    raise Exception("Recieved unsupported http method")


def sell(request: HttpRequest) -> HttpResponse:
    if request.user.is_anonymous:
        return redirect("/")

    if request.method == "GET":
        context = {"form": SellForm()}
        return render(request, "sell.html", context)

    if request.method == "POST":
        form = SellForm(request.POST)
        if not form.is_valid():
            form = SellForm()
            print(form)
            return render(request, "sell.html", {"form": form})

        user_profile = UserProfile.objects.get(user=request.user)

        token_name = form.cleaned_data["tokens"]

        if token_name == "MATTER":
            token_addres = MATTER_TOKEN_ADDRESS
        elif token_name == "IDEA":
            token_addres = IDEA_TOKEN_ADDRESS
        else:
            raise Exception("Nu kak tak to?")

        try:
            send_tokensBSC(
                user_profile.crypto_wallet_private_key,
                form.cleaned_data["wallet_address"],
                token_addres,
                float(form.cleaned_data["amount"]),
            )
            Transaction.objects.create(
                user=user_profile.user,
                amount=float(form.cleaned_data["amount"]),
                type=0,
                from_wallet=user_profile.crypto_wallet_address,
                to_wallet=form.cleaned_data["wallet_address"],
                block=get_current_or_create_open_block(),
            )
        except:
            form = SellForm()
            form.add_error("amount", "You do not have enough BNB to pay for gas.")
            return render(request, "sell.html", {"form": form})

        form = SellForm()
        return render(request, "sell.html", {"form": form})

    raise Exception("Recieved unsupported http method")


def profile(request: HttpRequest) -> HttpResponse:
    if request.user.is_anonymous:
        return redirect("/")

    if request.method == "GET":
        user_profile = UserProfile.objects.get(user=request.user)
        try:
            idea_info = get_idea_info(user_profile.crypto_wallet_address)
            matter_info = get_matter_info(user_profile.crypto_wallet_address)
            bnb_info = get_bnb_info(user_profile.crypto_wallet_address)

            bnb_price = bnb_info["usd_price"] if bnb_info is not None else 0
            if bnb_price == None:
                bnb_price = 0
            else:
                bnb_price = float(bnb_price)

            matter_price = matter_info["usd_price"] if matter_info is not None else 0
            if matter_price == None:
                matter_price = 0
            else:
                matter_price = float(matter_price)

            idea_price = idea_info["usd_price"] if idea_info is not None else 0
            if idea_price == None:
                idea_price = 0
            else:
                idea_price = float(idea_price)

            matter_balance = float(
                matter_info["balance_formatted"] if matter_info is not None else 0
            )
            idea_balance = float(
                idea_info["balance_formatted"] if idea_info is not None else 0
            )

            bnb_balance = float(
                bnb_info["balance_formatted"] if bnb_info is not None else 0
            )

            matter_balance_in_usdt = round(matter_balance * matter_price, 8)
            idea_balance_in_usdt = round(idea_balance * idea_price, 8)
            bnb_balance_in_usdt = round(bnb_balance * bnb_price, 8)

            # Get balance of connected wallet
            wallet_balance = 0
            wallet_balance_in_usdt = 0
            if user_profile.crypto_wallet_private_key is None and user_profile.crypto_wallet_address:
                # This is connected wallet, get its BNB balance
                try:
                    wallet_bnb_info = get_bnb_info(user_profile.crypto_wallet_address)
                    if wallet_bnb_info:
                        wallet_balance = float(wallet_bnb_info["balance_formatted"])
                        wallet_price = float(wallet_bnb_info["usd_price"]) if wallet_bnb_info["usd_price"] else 0
                        wallet_balance_in_usdt = round(wallet_balance * wallet_price, 8)
                except:
                    wallet_balance = 0
                    wallet_balance_in_usdt = 0

            total_balance_in_usdt = round(
                matter_balance_in_usdt + idea_balance_in_usdt + bnb_balance_in_usdt, 8
            )
            context = {
                "user": request.user,
                "user_profile": UserProfile.objects.get(user=request.user),
                "matter_balance": matter_balance,
                "idea_balance": idea_balance,
                "bnb_price": bnb_price,
                "bnb_balance": bnb_balance,
                "matter_balance_in_usdt": matter_balance_in_usdt,
                "idea_balance_in_usdt": idea_balance_in_usdt,
                "bnb_balance_in_usdt": bnb_balance_in_usdt,
                "wallet_balance": wallet_balance,
                "wallet_balance_in_usdt": wallet_balance_in_usdt,
                "total_balance_in_usdt": total_balance_in_usdt,
            }
            return render(request, "profile.html", context)
        except:
            messages.error(request, "Could not fetch matter and idea token price.")
            context = {
                "user": request.user,
                "user_profile": user_profile,
            }
            return render(request, "profile.html", context)

    raise Exception("Recieved unsupported http method")


def private_key(request: HttpRequest) -> HttpResponse:
    if request.user.is_anonymous:
        return redirect("/")

    user_profile = UserProfile.objects.get(user=request.user)
    context = {"user_profile": user_profile}

    return render(request, "private_key.html", context)


def faq(request: HttpRequest) -> HttpResponse:
    if request.user.is_anonymous:
        return redirect("/")

    return render(request, "faq/profile.html")


def games(request: HttpRequest) -> HttpResponse:
    if request.user.is_anonymous:
        return redirect("/")

    if request.method == "GET":
        user_profile = UserProfile.objects.get(user=request.user)
        context = {
            "usdt_balance": user_profile.usdt_balance,
        }
        return render(request, "games.html", context)

    raise Exception("Received unsupported http method")