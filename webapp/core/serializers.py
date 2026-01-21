from rest_framework import serializers
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password

from .models import UserProfile, Block, Bet, Transaction


class RegisterSerializer(serializers.ModelSerializer):
    password1 = serializers.CharField(write_only=True, required=True)
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate(self, data):
        password1 = data.get("password1")
        password2 = data.get("password2")

        if password1 != password2:
            raise serializers.ValidationError("Passwords do not match.")

        try:
            validate_password(password1)
        except ValidationError as e:
            raise serializers.ValidationError({"password1": list(e.messages)})

        return data

    def create(self, validated_data):
        password = validated_data.pop("password1")
        validated_data.pop("password2")

        user = User.objects.create(**validated_data)

        user.set_password(password)
        user.save()

        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    def validate(self, data):
        username = data.get("username")
        password = data.get("password")

        if not User.objects.filter(username=username).exists():
            raise serializers.ValidationError("A user with this username and password does not exist.")

        user = User.objects.get(username=username)
        if not user.check_password(password):
            raise serializers.ValidationError("A user with this username and password does not exist.")

        data['user'] = user
        return data

    def get_user(self):
        return self.validated_data.get("user")


class MakeBetSerializer(serializers.ModelSerializer):
    wallet_address = serializers.CharField(required=False, allow_null=True, allow_blank=True, write_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Bet
        fields = ('bet_size', 'bet_percent', 'id', 'is_winning', 'is_active', 'created_at', 'wallet_address')

    def validate_bet_size(self, value):
        if value < 1e-9:
            raise serializers.ValidationError("Bet is too small.")
        return value
    
    def create(self, validated_data):
        # Remove wallet_address from validated_data as it's not a field of Bet model
        validated_data.pop('wallet_address', None)
        return super().create(validated_data)


class SellSerializer(serializers.Serializer):
    CHOICES = [
        ("IDEA", 'Idea'),
        ("MATTER", 'Matter'),
    ]

    tokens = serializers.ChoiceField(choices=CHOICES)
    amount = serializers.DecimalField(max_digits=20, decimal_places=8)
    wallet_address = serializers.CharField(max_length=255)

    def validate_tokens(self, value):
        if value not in dict(self.CHOICES):
            raise serializers.ValidationError("Invalid token choice.")
        return value

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value


class RemoveBetSerializer(serializers.Serializer):
    removed_bet_id = serializers.CharField()

    def validate_removed_bet_id(self, value):
        if not Bet.objects.filter(id=value).exists():
            raise serializers.ValidationError("Invalid bet ID.")
        return value


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'amount', 'type', 'from_wallet', 'to_wallet', 'block', 'created_at']


class WalletConnectSerializer(serializers.Serializer):
    wallet_address = serializers.CharField(max_length=42, required=True)
    signature = serializers.CharField(required=True)
    message = serializers.CharField(required=True)
    
    def validate_wallet_address(self, value):
        # Basic Ethereum address validation
        if not value.startswith('0x') or len(value) != 42:
            raise serializers.ValidationError("Invalid wallet address format.")
        return value.lower()


class WalletAuthSerializer(serializers.Serializer):
    wallet_address = serializers.CharField(max_length=42, required=True)
    signature = serializers.CharField(required=True)
    message = serializers.CharField(required=True)
    
    def validate_wallet_address(self, value):
        if not value.startswith('0x') or len(value) != 42:
            raise serializers.ValidationError("Invalid wallet address format.")
        return value.lower()