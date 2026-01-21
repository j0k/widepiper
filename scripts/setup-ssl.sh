#!/usr/bin/env sh

set -e

docker-compose -f ./docker-compose.prod.yml run --rm certbot certonly --webroot --webroot-path /var/www/certbot/ -d liquidity.chilipizdrick.xyz
