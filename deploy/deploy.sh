#!/bin/bash
#
# 一键部署脚本 — 在 Linux 服务器上执行
#
# 前提：
#   - 服务器已安装 Python 3.10+、PostgreSQL、Nginx、Git
#   - 已将服务器 SSH 公钥添加到 Git 仓库的部署密钥
#
# 用法：
#   首次部署：REPO_URL=git@github.com:用户名/仓库名.git bash deploy/deploy.sh
#   更新部署：bash deploy/deploy.sh
#
# REPO_URL 仅首次部署时需要，后续更新脚本会自动通过 git pull 同步

set -e

APP_DIR="/opt/crm"
REPO_URL="${REPO_URL:-}"

echo "===== CRM 部署开始 ====="

# ---- 1. 安装系统依赖 ----
echo "[1/7] 安装系统依赖..."
sudo apt-get update -qq
sudo apt-get install -y python3-venv python3-pip postgresql nginx git -qq
#sudo apt-get install -y -qq

# ---- 2. 同步项目代码 ----
echo "[2/7] 同步项目代码..."
if [ -d "$APP_DIR/.git" ]; then
    # 已是 git 仓库，拉取最新代码
    echo "  检测到已有仓库，拉取最新代码..."
    cd $APP_DIR
    sudo git fetch --all
    sudo git reset --hard origin/main
    echo "  代码已更新到最新版本"
else
    # 首次部署，克隆仓库
    if [ -z "$REPO_URL" ]; then
        echo "[ERROR] 首次部署需要指定 Git 仓库地址："
        echo "  REPO_URL=git@github.com:用户名/仓库名.git bash deploy/deploy.sh"
        exit 1
    fi
    # 如果目录已存在但不是 git 仓库，先备份
    if [ -d "$APP_DIR" ]; then
        BACKUP_DIR="${APP_DIR}_bak_$(date +%Y%m%d%H%M%S)"
        echo "  备份现有目录到 $BACKUP_DIR ..."
        sudo mv $APP_DIR $BACKUP_DIR
    fi
    sudo git clone "$REPO_URL" $APP_DIR
    echo "  仓库已克隆到 $APP_DIR"
fi

# ---- 3. 创建 Python 虚拟环境并安装依赖 ----
echo "[3/7] 安装 Python 依赖..."
if [ ! -d "$APP_DIR/.venv" ]; then
    sudo python3 -m venv $APP_DIR/.venv
fi
# requirements.txt 已随 git 同步，直接安装
sudo $APP_DIR/.venv/bin/pip install -q -r $APP_DIR/requirements.txt

# ---- 4. 构建前端 ----
echo "[4/7] 构建前端..."
# 前端项目要求 Node.js 20+，Ubuntu 22.04 默认源只有 v12，需要检查版本
NODE_MIN_VERSION=20
NODE_VERSION_OK=false

if command -v node &> /dev/null; then
    NODE_MAJOR=$(node -e "console.log(process.versions.node.split('.')[0])" 2>/dev/null || echo "0")
    if [ "$NODE_MAJOR" -ge "$NODE_MIN_VERSION" ]; then
        NODE_VERSION_OK=true
    else
        echo "  当前 Node.js 版本: v$(node --version)，需要 v${NODE_MIN_VERSION}+"
    fi
fi

# Node.js 版本不够，尝试通过 NodeSource 安装
if [ "$NODE_VERSION_OK" = false ]; then
    echo "  正在安装 Node.js ${NODE_MIN_VERSION}.x ..."
    curl -fsSL https://deb.nodesource.com/setup_${NODE_MIN_VERSION}.x | sudo -E bash -
    sudo apt-get install -y nodejs -qq
    if command -v node &> /dev/null; then
        NODE_MAJOR=$(node -e "console.log(process.versions.node.split('.')[0])" 2>/dev/null || echo "0")
        if [ "$NODE_MAJOR" -ge "$NODE_MIN_VERSION" ]; then
            NODE_VERSION_OK=true
            echo "  Node.js 已安装: v$(node --version)"
        fi
    fi
fi

if [ "$NODE_VERSION_OK" = true ]; then
    cd $APP_DIR/frontend && npm install --quiet && npm run build
else
    echo "  跳过：Node.js 安装失败或版本不满足要求"
    echo "  请在本地构建后上传 frontend/dist："
    echo "    本地执行：npm --prefix frontend run build"
    echo "    上传执行：scp -r frontend/dist 用户名@服务器IP:/tmp/crm-dist/"
    echo "    服务器执行：sudo cp -r /tmp/crm-dist /opt/crm/frontend/dist"
fi

# ---- 5. 配置环境变量 ----
echo "[5/7] 配置环境变量..."
# .env 在 .gitignore 中，git pull 不会覆盖，首次生成模板
if [ ! -f "$APP_DIR/.env" ]; then
    sudo bash -c "cat > $APP_DIR/.env << 'ENVEOF'
APP_DATABASE_URL=postgresql+psycopg://crm:替换为你的密码@127.0.0.1:5432/crm
APP_JWT_SECRET_KEY=替换为一个随机字符串
APP_ACCESS_TOKEN_TTL_MINUTES=60
APP_REFRESH_TOKEN_TTL_DAYS=7
ENVEOF"
    echo "  已生成 .env 模板，请编辑 $APP_DIR/.env 填写实际值"
else
    echo "  .env 已存在，保持不变（git pull 不会覆盖）"
fi

# ---- 6. 配置 Nginx ----
echo "[6/7] 配置 Nginx..."
sudo cp $APP_DIR/deploy/nginx.conf /etc/nginx/sites-available/crm
sudo ln -sf /etc/nginx/sites-available/crm /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl enable nginx && sudo systemctl reload nginx

# ---- 7. 配置 Systemd 服务 ----
echo "[7/7] 配置 Systemd 服务..."
sudo cp $APP_DIR/deploy/crm.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable crm

# ---- 设置文件权限 ----
# .git 目录保留 root 权限，防止 www-data 修改仓库状态
sudo chown -R www-data:www-data $APP_DIR
sudo chown -R root:root $APP_DIR/.git

echo ""
echo "===== 部署完成 ====="
echo ""
echo "当前版本："
cd $APP_DIR && sudo git log --oneline -1
echo ""
echo "后续步骤（首次部署时）："
echo "  1. 编辑 /opt/crm/.env 填写数据库密码和 JWT 密钥"
echo "  2. 创建 PostgreSQL 数据库和用户："
echo "     sudo -u postgres createuser crm"
echo "     sudo -u postgres createdb crm -O crm"
echo "     sudo -u postgres psql -c \"ALTER USER crm PASSWORD '你的密码';\""
echo "  3. 执行数据库迁移："
echo "     cd /opt/crm && sudo -u www-data .venv/bin/python -m alembic upgrade head"
echo "  4. 同步权限数据："
echo "     cd /opt/crm && sudo -u www-data .venv/bin/python -m app.cli seed-permissions"
echo "  5. 启动服务："
echo "     sudo systemctl start crm"
echo ""
echo "更新部署（后续迭代时）："
echo "  bash deploy/deploy.sh                  # 自动 git pull + 重新安装依赖 + 重启"
echo "  sudo systemctl restart crm             # 代码更新后需重启后端"
