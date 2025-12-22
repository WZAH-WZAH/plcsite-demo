# tgforum backend（Django）

## 1) 本地开发（Windows）

在 `backend/` 目录执行：

1. 创建虚拟环境
   - `python -m venv .venv`
   - `./.venv/Scripts/Activate.ps1`
2. 安装依赖
   - `pip install -r requirements.txt`
3. 配置环境变量
   - 复制 `.env.example` 为 `.env`，修改 `DJANGO_SECRET_KEY`
4. 初始化数据库
   - `python manage.py migrate`
5. 创建管理员
   - `python manage.py createsuperuser`
6. 启动
   - `python manage.py runserver`

访问：
- API 根：`http://127.0.0.1:8000/api/`
- 管理后台：`http://127.0.0.1:8000/admin/`

## 2) Linux 部署（搬瓦工）

后续我会在你完成本地跑通后，再给你一份更细的「Nginx + Gunicorn + Systemd + PostgreSQL」部署步骤与安全清单。
