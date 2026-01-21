# liquidity

## Running the project with docker

### Running in production

Prerequisites: `docker`, `docker-compose`

> [!IMPORTANT]
> Before runnning the project replace all inclusions of testing domain `liquidity.chilipizdrick.xyz` with your own domain name (in django project settings, nginx settings, etc.)

To run in production environment first make sure to install ssl certificates using certbot:

1. Comment out a section of `./proxy/nginx/conf_prod/nginx.conf` file that looks like this:

```sh
# -- Comment this part out when setuping ssl certs --
# <<<
upstream django_app {
...
...
...
}
# >>>
```

2. Start the project with

```sh
./scripts/start-prod.sh
```

3. Install ssl certs using

```sh
./scripts/setup-ssl.sh
```

4. Uncomment before commented region of `./proxy/nginx/conf_prod/nginx.conf` or use `git stash`

5. Restart the project with

```sh
./scripts/start-prod.sh
```

> [!IMPORTANT]
> SSL cerificates provided by certbot expire in 3 months, to renew them run `./scripts/renew-ssl.sh` while the production
> environment is running.

### Running in development

```sh
./scripts/start-dev.sh
```

 You may also create superuser for dev environment with

```sh
docker-compose -f ./docker-compose.dev.yml exec webapp poetry run python manage.py createsuperuser
```

## Required environment variables (all in global .env file)

```sh
TELEGRAM_BOT_TOKEN="..." # Telegram bot token
WEBAPP_URL="..." # https webapp url (E.g "https://crypto.exapmle.com/")
SECRET_KEY="..." # Django secret key (can be generated on https://djecrety.ir/)
MATTER_TOKEN_ADDRESS="..." # Matter token etherium address
IDEA_TOKEN_ADDRESS="..." # Idea token etherium address
APP_WALLET="..." # Address of etherium app wallet
APP_WALLET_PRIVATE_KEY="..." # Private key to etherium app wallet
MORALIS_API_KEY="..." # Moralis API key.  WARNING : Moralis api should be always accessible for normal app functionality
TON_API_KEY="..." # Ton API key (DEPRECATED)
INFURA_API_KEY="..." # Infura API key
BSC_API_KEY="..." # BSC API key
PANCAKESWAP_ROUTER_ADDRESS="..." # Pancakeswap router address
PANCAKESWAP_ROUTER_ADDRESS_TESTNET="..." # Pancakeswap router address in testnet (For development purposes)
BSC_RPC_URL=https://bsc-dataseed.binance.org/
```
# liquidity
