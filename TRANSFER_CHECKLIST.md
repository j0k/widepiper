# Project Transfer Checklist

## ✅ Security Cleanup Completed

All sensitive information has been removed from this repository. The following items have been cleaned:

### Removed/Cleaned Files:
- ✅ `.env` - All tokens, keys, and addresses replaced with placeholders
- ✅ `.env.backup` - Cleaned
- ✅ `.env.testnet` - Cleaned
- ✅ `WALLETS_INFO.txt` - Replaced with template
- ✅ `TON_WALLET_INFO.txt` - Replaced with template
- ✅ `test_wallets_backup.txt` - Replaced with template
- ✅ `ADDRESSES_READY.txt` - Replaced with template
- ✅ `webapp/core/static/scripts/moralis-api.js` - API key removed
- ✅ `staticfiles/scripts/moralis-api.js` - API key removed
- ✅ `webapp/webapp/settings.py` - Domain replaced with placeholder
- ✅ `proxy/nginx/conf_prod/nginx.conf` - Domain replaced with placeholder
- ✅ `docker-compose.prod.yml` - Domain replaced with placeholder
- ✅ `docker-compose.prod-no-nginx.yml` - Domain replaced with placeholder
- ✅ `webapp/core/const.py` - Default addresses removed
- ✅ Database files removed

### Deleted Files with Sensitive Info:
- ✅ `✅_ВСЁ_ГОТОВО.txt`
- ✅ `TON_BALANCE_CHECK.txt`
- ✅ `TON_DEPOSIT_SUCCESS.txt`
- ✅ `TON_TRANSACTION_MONITOR.txt`
- ✅ `TON_SOLUTION.txt`
- ✅ `ALL_WALLETS_SUMMARY.txt`
- ✅ `QUICK_START_TON.txt`
- ✅ `TEST_NOW.txt`

### Created Template Files:
- ✅ `.env.example` - Complete configuration template
- ✅ `.env.testnet.example` - Testnet configuration template
- ✅ `SECURITY_SETUP.md` - Detailed setup instructions
- ✅ `TRANSFER_CHECKLIST.md` - This file

### Updated .gitignore:
- ✅ Added `.env.backup`
- ✅ Added wallet information files
- ✅ Ensured all sensitive files are excluded

## 📋 What the New Owner Needs to Do

### 1. Environment Configuration
```bash
# Copy template and configure
cp .env.example .env

# Edit .env and fill in all values:
# - Telegram bot token
# - Django secret key
# - Wallet addresses and private keys
# - API keys (Moralis, Infura, BscScan, TON, WalletConnect)
# - Domain name
```

### 2. Generate New Credentials

**Django Secret Key:**
```python
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

**Telegram Bot:**
- Create new bot via [@BotFather](https://t.me/botfather)
- Get bot token

**Crypto Wallets:**
- Create new TRON wallet (TronLink)
- Create new BSC wallet (MetaMask)
- Create new TON wallet (TonKeeper)
- Save addresses and private keys securely

**API Keys:**
- Moralis: https://moralis.io/
- Infura: https://infura.io/
- BscScan: https://bscscan.com/apis
- TON: https://toncenter.com/
- WalletConnect: https://cloud.walletconnect.com/

### 3. Update Domain Configuration

Replace `your-domain.com` in:
- `.env` → `WEBAPP_URL`
- `webapp/webapp/settings.py` → `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `CORS_ORIGIN_WHITELIST`
- `proxy/nginx/conf_prod/nginx.conf` → `server_name` and SSL paths
- `docker-compose.prod.yml` → `WEBAPP_URL`
- `docker-compose.prod-no-nginx.yml` → `WEBAPP_URL`

### 4. Configure Moralis API in Frontend

Edit `webapp/core/static/scripts/moralis-api.js`:
```javascript
// In constructor or init method
this.apiKey = 'YOUR_MORALIS_API_KEY';
```

Or better: Create a backend endpoint to provide the API key securely.

### 5. SSL Certificates

For production with HTTPS:
```bash
docker-compose -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot --webroot-path /var/www/certbot/ \
  -d your-domain.com
```

### 6. Database Setup

```bash
# Create migrations
docker-compose -f docker-compose.prod.yml run --rm webapp python manage.py makemigrations

# Apply migrations
docker-compose -f docker-compose.prod.yml run --rm webapp python manage.py migrate

# Create superuser
docker-compose -f docker-compose.prod.yml run --rm webapp python manage.py createsuperuser
```

### 7. Deploy

```bash
# Build and start
docker-compose -f docker-compose.prod.yml up -d --build

# Check logs
docker-compose -f docker-compose.prod.yml logs -f
```

## 🔒 Security Reminders

### DO:
- ✅ Use strong, unique passwords and keys
- ✅ Keep private keys in secure storage (hardware wallet, encrypted vault)
- ✅ Use separate wallets for testing and production
- ✅ Regularly backup wallet information
- ✅ Enable 2FA on all service accounts
- ✅ Monitor wallet balances and transactions
- ✅ Set up alerts for suspicious activity
- ✅ Regularly update dependencies
- ✅ Review security logs

### DON'T:
- ❌ Commit `.env` files to version control
- ❌ Share private keys or mnemonics
- ❌ Use testnet wallets in production
- ❌ Store large amounts on hot wallets
- ❌ Reuse passwords across services
- ❌ Hardcode credentials in source code
- ❌ Expose API keys in frontend code
- ❌ Use default or weak secret keys

## 📚 Documentation

Read these files for detailed information:

1. **SECURITY_SETUP.md** - Complete security setup guide
2. **README.md** - Project overview and general documentation
3. **.env.example** - All environment variables explained
4. **.env.testnet.example** - Testnet configuration guide

## 🧪 Testing Before Production

1. Set up testnet configuration:
   ```bash
   cp .env.testnet.example .env.testnet
   ```

2. Get testnet tokens:
   - BSC Testnet: https://testnet.binance.org/faucet-smart
   - TRON Testnet: https://nileex.io/join/getJoinPage

3. Test all functionality:
   - User registration
   - Wallet connection
   - Deposits (TRC-20, BSC, TON)
   - Withdrawals
   - Betting system
   - Telegram bot

4. Only after successful testing, deploy to production

## ✅ Final Verification

Before going live, verify:

- [ ] All `.env` variables configured
- [ ] Django SECRET_KEY is unique and strong
- [ ] All API keys are valid and working
- [ ] Wallets created and funded (for gas)
- [ ] Domain configured correctly
- [ ] SSL certificates installed
- [ ] Database migrations applied
- [ ] Superuser created
- [ ] All services start without errors
- [ ] Frontend loads correctly
- [ ] Deposits work (test with small amounts)
- [ ] Withdrawals work (test with small amounts)
- [ ] Telegram bot responds
- [ ] Monitoring and logging configured
- [ ] Backup system in place

## 📞 Support

If you encounter issues:

1. Check logs: `docker-compose logs -f`
2. Review documentation files
3. Verify all environment variables
4. Test with testnet first
5. Check service status pages for API providers

## 🎉 Ready to Go!

Once all items are checked, your project is ready for production deployment.

Good luck! 🚀

---

**Note:** This project has been cleaned of all sensitive information. You are starting with a clean slate and need to configure everything from scratch for security reasons.
