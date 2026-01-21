# Security Setup Guide

This guide will help you configure the project securely before deployment.

## ⚠️ IMPORTANT: Before Transferring the Project

All sensitive information has been removed from this repository. You need to configure your own credentials.

## 🔐 Required Configuration Steps

### 1. Environment Variables

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env` and replace all placeholder values with your actual credentials:

- `TELEGRAM_BOT_TOKEN` - Get from [@BotFather](https://t.me/botfather)
- `SECRET_KEY` - Generate a new Django secret key
- `WEBAPP_URL` - Your domain name
- Wallet addresses and private keys
- API keys (Moralis, Infura, BscScan, TON, WalletConnect)

### 2. Generate Django Secret Key

```python
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 3. Create Crypto Wallets

You need to create wallets for:

#### TRON (TRC-20)
- Use TronLink or similar wallet
- Save address and private key
- Add to `.env` as `DEPOSIT_ADDRESS_TRC20` and `TRON_PRIVATE_KEY`

#### BSC (BEP-20)
- Use MetaMask or similar wallet
- Save address and private key
- Add to `.env` as `DEPOSIT_ADDRESS_BSC` and `BSC_PRIVATE_KEY`

#### TON
- Use TonKeeper or similar wallet
- Save address and 24-word mnemonic
- Add to `.env` as `DEPOSIT_ADDRESS_TON` and `WITHDRAW_TON_MNEMONIC`

### 4. Get API Keys

#### Moralis API
1. Go to https://moralis.io/
2. Sign up and create a project
3. Copy API key to `.env`

#### Infura API
1. Go to https://infura.io/
2. Create account and project
3. Copy API key to `.env`

#### BscScan API
1. Go to https://bscscan.com/apis
2. Register and create API key
3. Copy to `.env`

#### TON API
1. Go to https://toncenter.com/
2. Get API key
3. Copy to `.env`

#### WalletConnect
1. Go to https://cloud.walletconnect.com/
2. Create project
3. Copy Project ID to `.env`

### 5. Configure Domain

Update your domain in:

1. `.env` - `WEBAPP_URL`
2. `webapp/webapp/settings.py` - `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`
3. `proxy/nginx/conf_prod/nginx.conf` - `server_name` and SSL certificate paths
4. `docker-compose.prod.yml` - `WEBAPP_URL` in telegram_bot environment

### 6. Configure Moralis API in Frontend

Edit `webapp/core/static/scripts/moralis-api.js`:

```javascript
// In the init() method or constructor, set your API key
this.apiKey = 'YOUR_MORALIS_API_KEY';
```

Or better yet, load it from backend via an API endpoint.

### 7. SSL Certificates

For production with HTTPS:

```bash
# Generate Let's Encrypt certificates
docker-compose -f docker-compose.prod.yml run --rm certbot certonly --webroot --webroot-path /var/www/certbot/ -d your-domain.com
```

## 🔒 Security Best Practices

### DO:
✅ Use strong, unique passwords and keys
✅ Keep private keys and mnemonics in secure storage
✅ Use separate wallets for testing and production
✅ Regularly backup wallet information
✅ Use environment variables for sensitive data
✅ Enable 2FA on all service accounts
✅ Regularly update dependencies
✅ Monitor wallet balances and transactions
✅ Set up alerts for suspicious activity

### DON'T:
❌ Commit `.env` files to version control
❌ Share private keys or mnemonics
❌ Use testnet wallets in production
❌ Store large amounts on hot wallets
❌ Reuse passwords across services
❌ Hardcode credentials in source code
❌ Use default or weak secret keys
❌ Expose API keys in frontend code

## 📝 Files to Keep Private

These files contain sensitive information and should NEVER be committed:

- `.env`
- `.env.backup`
- `.env.testnet`
- `WALLETS_INFO.txt`
- `TON_WALLET_INFO.txt`
- `test_wallets_backup.txt`
- `ADDRESSES_READY.txt`
- Any files with private keys or mnemonics

## 🧪 Testing Configuration

For testnet testing:

```bash
cp .env.testnet.example .env.testnet
```

Fill in testnet wallet addresses and use testnet faucets to get test tokens.

## 🚀 Deployment Checklist

Before deploying to production:

- [ ] All `.env` variables configured
- [ ] Django SECRET_KEY generated
- [ ] Telegram bot token configured
- [ ] All wallets created and configured
- [ ] All API keys obtained and configured
- [ ] Domain configured in all files
- [ ] SSL certificates generated
- [ ] `.gitignore` includes all sensitive files
- [ ] Database backups configured
- [ ] Monitoring and alerts set up
- [ ] Security audit completed

## 📞 Support

If you need help with configuration:

1. Check the documentation in `README.md`
2. Review example files (`.env.example`, `.env.testnet.example`)
3. Check service documentation for API keys
4. Test with testnet first before production

## 🔄 Regular Maintenance

- Update API keys before expiration
- Rotate secrets periodically
- Monitor wallet balances
- Review transaction logs
- Update dependencies
- Backup database regularly
- Check for security updates

---

**Remember:** Security is not a one-time setup. Regularly review and update your security practices.
