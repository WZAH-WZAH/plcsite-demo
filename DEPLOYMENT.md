# 部署上线（最小可用：首页 + 游戏板块）

> 目标：尽快把站点跑在一台 Linux VPS 上，前端静态 + 后端 API（Django/Gunicorn），保证“首页”和“游戏板块”可访问。

## 0) 你需要准备的环境变量（后端）

在服务器的 `backend/.env` 至少设置：

- `DJANGO_SECRET_KEY`：随机强密码
- `DJANGO_DEBUG=0`
- `DJANGO_ALLOWED_HOSTS=你的域名,你的服务器IP`
- `DJANGO_CORS_ALLOWED_ORIGINS=https://你的域名`
- `DJANGO_CSRF_TRUSTED_ORIGINS=https://你的域名`

可选（强烈建议）：
- `DJANGO_TG_SYNC_SECRET`：如果你用到了 TG 同步 webhook
- `DJANGO_PAYMENTS_WEBHOOK_SECRET`：如果你用到了支付 webhook

## 1) 后端：安装/迁移/静态文件

在服务器上：

- `cd backend`
- `python -m venv .venv`
- `. .venv/bin/activate`
- `pip install -r requirements.txt`
- `python manage.py migrate`
- `python manage.py collectstatic --noinput`
- `python manage.py createsuperuser`

说明：
- 项目已集成 WhiteNoise（生产环境）用于静态文件服务；`collectstatic` 会输出到 `backend/staticfiles/`。
- `media/`（用户上传）建议交给 Nginx 直接静态托管。

## 2) Gunicorn（示例）

在 `backend/` 下：

- `pip install gunicorn`
- `gunicorn tgforum.wsgi:application -b 127.0.0.1:8000 --workers 2 --timeout 60`

## 3) Nginx（示例配置）

下面是「常规的域名规范化 + HTTPS」配置：
- HTTP 自动跳转到 HTTPS
- `www`/非`www` 统一到一个主域名

> 这类跳转用于安全与一致性（SEO/避免混合内容），不用于规避任何平台/地区限制。

```nginx
# 80 -> 443
server {
  listen 80;
  server_name example.com www.example.com;
  return 301 https://example.com$request_uri;
}

server {
  listen 443 ssl http2;
  server_name example.com;

  # SSL 证书（自行用 certbot 配置）
  # ssl_certificate     /etc/letsencrypt/live/example.com/fullchain.pem;
  # ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

  client_max_body_size 25m;

  # 前端：静态文件
  root /var/www/plcsite-demo/frontend-dist;
  index index.html;

  # 前端 SPA 路由
  location / {
    try_files $uri $uri/ /index.html;
  }

  # 后端 API 反代
  location /api/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }

  # Django admin
  location /admin/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }

  # 用户上传媒体
  location /media/ {
    alias /var/www/plcsite-demo/backend-media/;
    access_log off;
    expires 7d;
  }

  # Django collectstatic 输出
  location /static/ {
    alias /var/www/plcsite-demo/backend-staticfiles/;
    access_log off;
    expires 30d;
  }
}
```

## 4) 前端构建与发布

在本机或服务器：

- `cd frontend`
- `npm ci`（或 `npm install`）
- `npm run build`

把 `frontend/dist/` 同步到 Nginx 的 `root` 指向目录（如 `/var/www/plcsite-demo/frontend-dist`）。

## 5) “首页 + 游戏板块”自检清单

- 首页能打开：`/`
- 首页热门推荐能加载：会请求 `/api/home/hero/`、`/api/posts/feed/hot/`、`/api/posts/feed/latest/`
- 顶部导航能看到“游戏”：板块 slug 为 `games`
- 游戏板块页能打开：`/b/games`

如果游戏板块为空：
- 先在后台发几条帖子到“游戏”板块；或确认你已执行 `python manage.py migrate`（含数据迁移 0009）。
