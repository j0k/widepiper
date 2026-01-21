from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .models import Bet

class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "password1",
            "password2",
        )

    username = forms.CharField(
        label="",
        required=True,
        widget=forms.TextInput(
            attrs={
                "required": "required",
                "placeholder": "Enter your username",
                "class": "username-field",
            }
        ),
    )
    email = forms.CharField(
        label="",
        required=True,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter your email",
                "class": "email-field",
                "required": "required",
            }
        ),
    )
    password1 = forms.CharField(
        label="",
        required=True,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Enter your password",
                "required": "required",
            }
        ),
    )
    password2 = forms.CharField(
        label="",
        required=True,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Confirm your password",
                "required": "required",
            }
        ),
    )

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email

    def get_user(self):
        username = self.cleaned_data.get("username")
        user = User.objects.get(username=username)
        return user


class LoginForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("username", "password")

    username = forms.CharField(
        label="Username",
        required=True,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Username",
                "type": "text",
                "class": "username-field",
                "required": "required",
            }
        ),
    )
    password = forms.CharField(
        label="Password",
        required=True,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Password",
                "type": "password",
                "required": "required",
            }
        ),
    )

    def clean(self):
        username = self.cleaned_data.get("username")
        if not User.objects.filter(username=username).exists():
            raise forms.ValidationError(
                "A user with this username and password does not exist."
            )
        user = User.objects.get(username=username)
        password = self.cleaned_data.get("password")
        if password is None:
            raise forms.ValidationError(
                "A user with this username and password does not exist."
            )
        if not user.check_password(password):
            raise forms.ValidationError(
                "A user with this username and password does not exist."
            )
        return self.cleaned_data

    def get_user(self):
        username = self.cleaned_data["username"]
        user = User.objects.get(username=username)
        return user


class MakeBetForm(forms.ModelForm):
    class Meta:
        model = Bet
        fields = ("bet_size", "bet_percent")

    bet_size = forms.DecimalField(
        label="",
        widget=forms.TextInput(
            attrs={
                "class": "input-area",
                "placeholder": "USDT amount",
                "type": "number",
                "step": "0.00000001",
                "required": "required",
            }
        ),
    )
    bet_percent = forms.DecimalField(
        label="",
        widget=forms.TextInput(
            attrs={
                "class": "persent",
                "placeholder": "DMT/USDT bet percent",
                "type": "number",
                "step": "0.00000001",
                "required": "required",
            }
        ),
    )

    def clean_bet_size(self):
        bet_size = self.cleaned_data["bet_size"]
        if bet_size < 1e-9:
            raise ValidationError("Bet is too small.")
        return bet_size

    def clean_bet_percent(self):
        bet_percent = self.cleaned_data["bet_percent"]
        return bet_percent


# class DepositForm(forms.Form):
#     def __init__(self, *args, **kwargs):
#         super(forms.Form, self).__init__(*args, **kwargs)
#         self.choices = [(c, c) for c in kwargs.pop("choices")]
#         self.fields["payment_method"].initial = forms.ChoiceField(
#             widget=forms.Select(attrs={"class": "payment-select"}),
#             choices=self.choices,
#             label="",
#         )
#
#     amount = forms.FloatField(
#         widget=forms.TextInput(
#             attrs={"class": "payment", "placeholder": "Quantity", "type": "number"}
#         ),
#         label="",
#     )



class SellForm(forms.Form):
    CHOICES = [
        ("IDEA", 'Idea'),
        ("MATTER", 'Matter'),
    ]

    tokens = forms.ChoiceField(
        widget=forms.Select(attrs={"class": "payment-select"}),
        choices=CHOICES,
        label=""
    )

    amount = forms.DecimalField(
        widget=forms.TextInput(
            attrs={
                "class": "payment",
                "placeholder": "Quantity",
                "type": "number",
                "step": "0.00000001",
                "required": "required",
            }
        ),
        label="",
    )

    wallet_address = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "wallet",
                "placeholder": "Wallet Address",
                "type": "text",
                "required": "required",
            }
        ),
        label="",
    )

    def clean_tokens(self):
        tokens = self.cleaned_data["tokens"]
        if tokens not in ["IDEA", "MATTER"]:
            raise ValidationError("Invalid token choice.")
        return tokens
