# Generated migration for deposit system

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='usdt_balance',
            field=models.DecimalField(decimal_places=8, default=0, max_digits=18),
        ),
        migrations.CreateModel(
            name='DepositTransaction',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('amount', models.DecimalField(decimal_places=8, max_digits=18)),
                ('network', models.CharField(choices=[('TRC20', 'TRON TRC-20'), ('BSC', 'Binance Smart Chain'), ('TON', 'TON Network'), ('BYBIT', 'Bybit')], max_length=10)),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('CONFIRMED', 'Confirmed'), ('CREDITED', 'Credited'), ('FAILED', 'Failed')], default='PENDING', max_length=20)),
                ('tx_hash', models.CharField(max_length=100, unique=True)),
                ('from_address', models.CharField(max_length=74)),
                ('to_address', models.CharField(max_length=74)),
                ('confirmations', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('confirmed_at', models.DateTimeField(blank=True, null=True)),
                ('credited_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'managed': True,
                'app_label': 'core',
            },
        ),
    ]

