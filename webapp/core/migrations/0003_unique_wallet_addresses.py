# Migration to add unique constraints on wallet addresses
# IMPORTANT: Before running this migration, ensure there are no duplicate wallet addresses in the database!
# Run this query to check: SELECT crypto_wallet_address, COUNT(*) FROM core_userprofile WHERE crypto_wallet_address IS NOT NULL GROUP BY crypto_wallet_address HAVING COUNT(*) > 1;

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_deposit_system'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='ton_wallet_address',
            field=models.CharField(blank=True, max_length=74, null=True),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='crypto_wallet_address',
            field=models.CharField(blank=True, max_length=74, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='ton_wallet_address',
            field=models.CharField(blank=True, max_length=74, null=True, unique=True),
        ),
    ]
