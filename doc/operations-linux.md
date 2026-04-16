# CRM 系统 Linux 生产环境操作手册

适用环境：Ubuntu 22.04 LTS 64bit

> **前端部署的详细说明**（依赖安装、构建、上传、回滚、缓存处理等）请参见 [operations-frontend-linux.md](operations-frontend-linux.md)。

---

## 目录

1. [环境准备](#1-环境准备)
2. [首次部署](#2-首次部署)
3. [启动服务](#3-启动服务)
4. [关闭服务](#4-关闭服务)
5. [重启服务](#5-重启服务)
6. [日常更新部署](#6-日常更新部署)
7. [数据库操作](#7-数据库操作)
8. [Nginx 配置](#8-nginx-配置)
9. [服务架构](#9-服务架构)
10. [故障排查](#10-故障排查)
11. [命令速查表](#11-命令速查表)

---

## 1. 环境准备

### 服务器要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Ubuntu 22.04 LTS 64bit |
| Python | 3.10+（Ubuntu 22.04 自带 3.10） |
| PostgreSQL | 14+（Ubuntu 22.04 默认源提供） |
| Nginx | 1.18+（Ubuntu 22.04 默认源提供） |
| 磁盘空间 | 至少 2GB（含虚拟环境和前端构建产物） |
| 内存 | 至少 1GB |

### 前置依赖安装

首次部署脚本（`deploy/deploy.sh`）会自动安装以下系统依赖：
- `python3-venv` — Python 虚拟环境
- `python3-pip` — Python 包管理
- `postgresql` — 数据库
- `nginx` — 反向代理
- `git` — 代码版本管理与同步

如需手动安装：

```bash
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip postgresql nginx git
```

### 配置 Git 仓库访问

项目通过 Git 从远程仓库同步到服务器，需要先配置访问权限：

**方式一：SSH 部署密钥（推荐）**

```bash
# 1. 在服务器上生成 SSH 密钥
ssh-keygen -t ed25519 -C "crm-deploy" -f ~/.ssh/crm_deploy -N ""

# 2. 查看公钥
cat ~/.ssh/crm_deploy.pub

# 3. 将公钥添加到 Git 仓库的 Settings → Deploy Keys（勾选 Allow write access）
#    GitHub: 仓库 → Settings → Deploy keys → Add deploy key
#    Gitee:  仓库 → 管理 → 公钥管理 → 添加公钥

# 4. 配置 SSH 使用该密钥
cat >> ~/.ssh/config << 'EOF'
Host github.com
    IdentityFile ~/.ssh/crm_deploy
    StrictHostKeyChecking no
EOF
```

**方式二：HTTPS + Token**

```bash
# 使用 Personal Access Token 认证
# REPO_URL 格式：https://用户名:TOKEN@github.com/用户名/仓库名.git
```

---

## 2. 首次部署

### 一键部署

在服务器上执行部署脚本，首次部署需要指定 Git 仓库地址：

```bash
# 首次部署 — 指定 Git 仓库地址
REPO_URL=git@github.com:用户名/仓库名.git bash deploy/deploy.sh

# 如果仓库已有源码，也可以在仓库目录内执行
cd /opt/crm && bash deploy/deploy.sh
```

脚本会自动完成以下 7 个步骤：

| 步骤 | 内容 |
|------|------|
| 1/7 | 安装系统依赖（python3-venv、postgresql、nginx、git） |
| 2/7 | Git 克隆或拉取最新代码到 `/opt/crm` |
| 3/7 | 创建虚拟环境并安装 Python 依赖 |
| 4/7 | 构建前端（如果服务器有 npm） |
| 5/7 | 生成 `.env` 配置模板（仅首次，后续不覆盖） |
| 6/7 | 配置 Nginx 反向代理 |
| 7/7 | 配置 Systemd 服务 |

### 部署后必做步骤

#### 2.1 编辑配置文件

```bash
sudo nano /opt/crm/.env
```

修改以下关键配置：

```ini
# 数据库连接 — 修改为实际密码
APP_DATABASE_URL=postgresql+psycopg://crm:你的密码@127.0.0.1:5432/crm

# JWT 密钥 — 必须替换为随机字符串，可用以下命令生成：
# python3 -c "import secrets; print(secrets.token_urlsafe(32))"
APP_JWT_SECRET_KEY=替换为生成的随机字符串

# Token 有效期
APP_ACCESS_TOKEN_TTL_MINUTES=60
APP_REFRESH_TOKEN_TTL_DAYS=7
```

#### 2.2 创建数据库

```bash
# 创建数据库用户
sudo -u postgres createuser crm

# 创建数据库并指定所属用户
sudo -u postgres createdb crm -O crm

# 设置用户密码
sudo -u postgres psql -c "ALTER USER crm PASSWORD '你的密码';"
```

#### 2.3 执行数据库迁移

```bash
cd /opt/crm && sudo -u www-data .venv/bin/python -m alembic upgrade head
```

#### 2.4 同步权限数据

```bash
cd /opt/crm && sudo -u www-data .venv/bin/python -m app.cli seed-permissions
```

#### 2.5 启动服务

```bash
sudo systemctl start crm
```

### 验证部署

```bash
# 检查服务状态
sudo systemctl status crm

# 检查 Nginx 状态
sudo systemctl status nginx

# 测试 API 是否响应
curl http://127.0.0.1:8000/docs

# 测试前端是否可访问
curl -I http://127.0.0.1/
```

---

## 3. 启动服务

### 启动后端

```bash
sudo systemctl start crm
```

### 查看服务状态

```bash
sudo systemctl status crm
```

正常输出示例：

```
● crm.service - CRM Backend (FastAPI + Uvicorn)
     Loaded: loaded (/etc/systemd/system/crm.service; enabled; vendor preset: enabled)
     Active: active (running)
```

### 启动 Nginx

Nginx 通常随系统自动启动，如需手动启动：

```bash
sudo systemctl start nginx
```

### 开机自启

首次部署时已通过 `systemctl enable` 设置，如需确认：

```bash
sudo systemctl enable crm    # 后端开机自启
sudo systemctl enable nginx  # Nginx 开机自启
```

---

## 4. 关闭服务

### 停止后端

```bash
sudo systemctl stop crm
```

### 停止 Nginx

```bash
sudo systemctl stop nginx
```

### 停止并禁止开机自启

```bash
# 后端
sudo systemctl stop crm
sudo systemctl disable crm

# Nginx
sudo systemctl stop nginx
sudo systemctl disable nginx
```

---

## 5. 重启服务

### 重启后端

代码更新后需要重启后端服务：

```bash
sudo systemctl restart crm
```

### 重载 Nginx

修改 Nginx 配置后需要重载（不断开现有连接）：

```bash
sudo systemctl reload nginx
```

### 完全重启 Nginx

```bash
sudo systemctl restart nginx
```

---

## 6. 日常更新部署

代码通过 Git 同步，更新部署非常简单。

### 方式一：重新执行部署脚本（推荐）

```bash
# 在服务器上执行，自动 git pull + 安装依赖 + 构建前端
bash /opt/crm/deploy/deploy.sh

# 代码更新后需重启后端
sudo systemctl restart crm
```

脚本会自动检测到 `/opt/crm` 已是 Git 仓库，执行 `git pull` 拉取最新代码，然后重新安装依赖、构建前端。

### 方式二：手动 git pull（更快，适合小更新）

```bash
# 1. 拉取最新代码
cd /opt/crm
sudo git pull

# 2. 如果 requirements.txt 有变更，更新 Python 依赖
sudo /opt/crm/.venv/bin/pip install -q -r /opt/crm/requirements.txt

# 3. 如果前端有变更，重新构建
#    服务器上构建：cd /opt/crm/frontend && npm install --quiet && npm run build
#    本地构建上传：参见 operations-frontend-linux.md

# 4. 如果有新的迁移文件，执行数据库迁移
cd /opt/crm && sudo -u www-data .venv/bin/python -m alembic upgrade head

# 5. 重启后端服务
sudo systemctl restart crm
```

### 方式三：回退到指定版本

```bash
cd /opt/crm

# 查看版本历史
sudo git log --oneline -10

# 回退到指定版本
sudo git checkout 指定的commit哈希

# 重启服务
sudo systemctl restart crm
```

### 更新流程决策

| 变更类型 | 需要的步骤 |
|---------|-----------|
| 仅后端代码 | `git pull` → `systemctl restart crm` |
| 后端 + 新依赖 | `git pull` → 重装依赖 → `systemctl restart crm` |
| 仅前端 | `git pull` → 构建前端 → 无需重启后端 |
| 数据库 Model 变更 | `git pull` → `alembic upgrade head` → `systemctl restart crm` |
| Nginx/服务配置变更 | `git pull` → 脚本自动处理或手动 `systemctl reload nginx` |

---

## 7. 数据库操作

### 执行迁移

```bash
cd /opt/crm && sudo -u www-data .venv/bin/python -m alembic upgrade head
```

### 查看当前迁移版本

```bash
cd /opt/crm && sudo -u www-data .venv/bin/python -m alembic current
```

### 查看迁移历史

```bash
cd /opt/crm && sudo -u www-data .venv/bin/python -m alembic history
```

### 同步权限数据

新增权限码后需要同步到数据库：

```bash
cd /opt/crm && sudo -u www-data .venv/bin/python -m app.cli seed-permissions
```

### 数据库备份

```bash
# 备份整个数据库
sudo -u postgres pg_dump crm > /tmp/crm_backup_$(date +%Y%m%d_%H%M%S).sql

# 恢复备份
sudo -u postgres psql crm < /tmp/crm_backup_20260416_120000.sql
```

> **警告**：数据库迁移、权限同步会修改数据库内容，执行前建议先备份。

---

## 8. Nginx 配置

配置文件位置：`/etc/nginx/sites-available/crm`

### 当前配置说明

```nginx
server {
    listen 80;
    server_name _;  # 替换为域名或 IP

    # 前端静态文件
    root /opt/crm/frontend/dist;
    index index.html;

    # Gzip 压缩
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml;
    gzip_min_length 256;

    # 静态资源 — 长期缓存（文件名带哈希）
    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # API 请求转发给 Uvicorn
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # SPA 路由回退
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

### 修改域名

```bash
sudo nano /etc/nginx/sites-available/crm
# 将 server_name _; 改为 server_name crm.example.com;

# 验证配置语法
sudo nginx -t

# 重载生效
sudo systemctl reload nginx
```

### 配置 HTTPS（推荐）

使用 Certbot 自动配置 Let's Encrypt SSL 证书：

```bash
# 安装 Certbot
sudo apt-get install -y certbot python3-certbot-nginx

# 自动配置 HTTPS（需先将域名指向服务器 IP）
sudo certbot --nginx -d crm.example.com

# 证书会自动续期，验证续期定时任务
sudo systemctl status certbot.timer
```

---

## 9. 服务架构

```
                    Ubuntu 22.04 服务器
┌─────────────────────────────────────────────────┐
│                                                   │
│  客户端 ──→ Nginx(:80/:443)                       │
│               │                                   │
│               ├── /assets/*  ──→ 静态文件缓存      │
│               ├── /api/*     ──→ Uvicorn(:8000)   │
│               │                    │               │
│               │              FastAPI 应用          │
│               │                    │               │
│               │              PostgreSQL(:5432)     │
│               │                                   │
│               └── 其他路径  ──→ index.html (SPA)  │
│                                                   │
└─────────────────────────────────────────────────┘
```

### 进程管理

| 服务 | 管理方式 | 配置文件 | 运行用户 |
|------|---------|---------|---------|
| Uvicorn (FastAPI) | systemd | `/etc/systemd/system/crm.service` | www-data |
| Nginx | systemd | `/etc/nginx/sites-available/crm` | root |
| PostgreSQL | systemd | `/etc/postgresql/14/main/` | postgres |

### 目录结构

```
/opt/crm/                      # Git 仓库
├── .git/                  # Git 版本控制（root 权限，防止误操作）
├── app/                  # 后端应用代码
├── alembic/              # 数据库迁移文件
├── alembic.ini           # Alembic 配置
├── scripts/              # 脚本（数据导入等）
├── deploy/               # 部署配置（nginx.conf、crm.service、deploy.sh）
├── frontend/
│   ├── src/              # 前端源码
│   └── dist/             # 前端构建产物（Nginx 托管，git 已忽略）
├── .venv/                # Python 虚拟环境（git 已忽略）
├── .env                  # 环境变量配置（git 已忽略，不会覆盖）
├── requirements.txt      # Python 依赖
└── Makefile              # 便捷命令
```

### Systemd 服务配置

服务配置文件：`/etc/systemd/system/crm.service`

```ini
[Unit]
Description=CRM Backend (FastAPI + Uvicorn)
After=network.target postgresql.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/crm
ExecStart=/opt/crm/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5
EnvironmentFile=/opt/crm/.env
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=/opt/crm

[Install]
WantedBy=multi-user.target
```

关键参数说明：
- `--workers 2`：Uvicorn 工作进程数，建议设为 CPU 核心数
- `Restart=always`：进程异常退出时自动重启
- `RestartSec=5`：重启间隔 5 秒
- `ProtectSystem=strict`：限制写入范围，仅允许 `/opt/crm`

---

## 10. 故障排查

### 服务问题

| 问题 | 排查命令 |
|------|---------|
| 服务启动失败 | `sudo systemctl status crm` |
| 查看详细错误日志 | `sudo journalctl -u crm -n 50 --no-pager` |
| 查看实时日志 | `sudo journalctl -u crm -f` |
| 检查进程是否在运行 | `ps aux \| grep uvicorn` |
| 端口 8000 被占用 | `sudo lsof -i :8000` 或 `sudo ss -tlnp \| grep 8000` |
| 权限问题 | `sudo chown -R www-data:www-data /opt/crm && sudo chown -R root:root /opt/crm/.git` |

### Git 同步问题

| 问题 | 排查命令 |
|------|---------|
| git pull 失败（权限） | `sudo git pull`（需 root 权限，.git 属于 root） |
| git pull 冲突 | `sudo git status` 查看冲突文件；`sudo git reset --hard origin/main` 强制覆盖 |
| SSH 连接仓库失败 | `ssh -T git@github.com` 测试连接 |
| 查看当前版本 | `cd /opt/crm && sudo git log --oneline -1` |
| 查看本地与远程差异 | `cd /opt/crm && sudo git fetch && sudo git log HEAD..origin/main --oneline` |

### Nginx 问题

| 问题 | 排查命令 |
|------|---------|
| 配置语法错误 | `sudo nginx -t` |
| 查看访问日志 | `sudo tail -f /var/log/nginx/access.log` |
| 查看错误日志 | `sudo tail -f /var/log/nginx/error.log` |
| 502 Bad Gateway | 检查 Uvicorn 是否运行：`sudo systemctl status crm` |
| 静态文件 404 | 检查 `/opt/crm/frontend/dist/` 目录是否存在 |

### 数据库问题

| 问题 | 排查命令 |
|------|---------|
| 连接失败 | 检查 `/opt/crm/.env` 中 `APP_DATABASE_URL` |
| PostgreSQL 未运行 | `sudo systemctl status postgresql` |
| 查看数据库列表 | `sudo -u postgres psql -c "\l"` |
| 查看连接数 | `sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity;"` |
| 检查用户权限 | `sudo -u postgres psql -c "\du crm"` |

### 常见错误及解决方案

#### Uvicorn 启动失败

```bash
# 查看错误详情
sudo journalctl -u crm -n 100 --no-pager

# 常见原因：
# 1. .env 中数据库密码错误 → 修正 /opt/crm/.env
# 2. Python 依赖缺失 → sudo /opt/crm/.venv/bin/pip install -r /opt/crm/requirements.txt
# 3. 端口被占用 → sudo lsof -i :8000，kill 占用进程或修改 crm.service 中的端口
```

#### 修改 crm.service 后

```bash
# 修改服务配置后必须重载
sudo systemctl daemon-reload
sudo systemctl restart crm
```

#### 文件权限修复

```bash
# 应用文件归 www-data
sudo chown -R www-data:www-data /opt/crm
# .git 目录归 root，防止应用进程修改仓库状态
sudo chown -R root:root /opt/crm/.git
sudo chmod -R 755 /opt/crm/app
sudo chmod -R 755 /opt/crm/frontend/dist
sudo chmod 600 /opt/crm/.env  # 保护敏感配置
```

---

## 11. 命令速查表

### 服务管理

| 操作 | 命令 |
|------|------|
| 启动后端 | `sudo systemctl start crm` |
| 停止后端 | `sudo systemctl stop crm` |
| 重启后端 | `sudo systemctl restart crm` |
| 查看状态 | `sudo systemctl status crm` |
| 查看实时日志 | `sudo journalctl -u crm -f` |
| 查看最近日志 | `sudo journalctl -u crm -n 100 --no-pager` |
| 开机自启 | `sudo systemctl enable crm` |
| 禁止自启 | `sudo systemctl disable crm` |

### Nginx

| 操作 | 命令 |
|------|------|
| 启动 | `sudo systemctl start nginx` |
| 停止 | `sudo systemctl stop nginx` |
| 重启 | `sudo systemctl restart nginx` |
| 重载配置 | `sudo systemctl reload nginx` |
| 验证配置 | `sudo nginx -t` |
| 访问日志 | `sudo tail -f /var/log/nginx/access.log` |
| 错误日志 | `sudo tail -f /var/log/nginx/error.log` |

### 数据库

| 操作 | 命令 |
|------|------|
| 执行迁移 | `cd /opt/crm && sudo -u www-data .venv/bin/python -m alembic upgrade head` |
| 查看迁移版本 | `cd /opt/crm && sudo -u www-data .venv/bin/python -m alembic current` |
| 同步权限 | `cd /opt/crm && sudo -u www-data .venv/bin/python -m app.cli seed-permissions` |
| 备份数据库 | `sudo -u postgres pg_dump crm > backup.sql` |
| 恢复数据库 | `sudo -u postgres psql crm < backup.sql` |

### 部署

| 操作 | 命令 |
|------|------|
| 首次部署 | `REPO_URL=git@github.com:用户/仓.git bash deploy/deploy.sh` |
| 更新部署（自动） | `bash /opt/crm/deploy/deploy.sh` |
| 更新部署（手动） | `cd /opt/crm && sudo git pull && sudo systemctl restart crm` |
| 回退到指定版本 | `cd /opt/crm && sudo git checkout commit哈希 && sudo systemctl restart crm` |
| 查看当前版本 | `cd /opt/crm && sudo git log --oneline -1` |
| 更新 Python 依赖 | `sudo /opt/crm/.venv/bin/pip install -q -r /opt/crm/requirements.txt` |
| 修复权限 | `sudo chown -R www-data:www-data /opt/crm && sudo chown -R root:root /opt/crm/.git` |

### PostgreSQL

| 操作 | 命令 |
|------|------|
| 启动 | `sudo systemctl start postgresql` |
| 查看状态 | `sudo systemctl status postgresql` |
| 连接数据库 | `sudo -u postgres psql crm` |
| 创建用户 | `sudo -u postgres createuser crm` |
| 创建数据库 | `sudo -u postgres createdb crm -O crm` |
