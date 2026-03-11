# tg.ma8ka.com — widepiper webapp (отдельный виртуальный хост, не app.tatradev.com)
# Backend port: 8001 (gunicorn). If you run widepiper on 8000, change proxy_pass to 127.0.0.1:8000.
# To apply on server: sudo cp proxy/nginx/sites-available/tg.ma8ka.com /etc/nginx/sites-available/ && sudo nginx -t && sudo systemctl reload nginx

# HTTP — редирект на HTTPS (/.well-known оставлен для certbot)
server {
    listen 80;
    listen [::]:80;
    server_name tg.ma8ka.com;
    server_tokens off;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        return 301 https://tg.ma8ka.com$request_uri;
    }

    access_log /var/log/nginx/tg.ma8ka.com.access.log;
    error_log /var/log/nginx/tg.ma8ka.com.error.log;
}

# HTTPS
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name tg.ma8ka.com;

    ssl_certificate /etc/letsencrypt/live/tg.ma8ka.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tg.ma8ka.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;

    location /static/ {
        alias /home/jk/space/widepiper/staticfiles/;
    }

    # Backend: widepiper gunicorn (use 8001 if 8000 is taken by another app, e.g. uvicorn)
    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    access_log /var/log/nginx/tg.ma8ka.com.access.log;
    error_log /var/log/nginx/tg.ma8ka.com.error.log;
}
