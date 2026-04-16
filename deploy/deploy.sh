#!/bin/bash
#
# 一键部署脚本 — 在 Linux 服务器上执行
#
# 前提：服务器已安装 Python 3.11+、PostgreSQL、Nginx
# 用法：bash deploy/deploy.sh
#
# 本脚本只需首次部署时执行一次，后续更新只需重新构建前端并重启服务

set -e

APP_DIR="/opt/crm"
REPO_DIR=$(cd "$(dirname "$0")/.." && pwd)

echo "===== CRM 部署开始 ====="

# ---- 1. 安装系统依赖 ----
echo "[1/7] 安装系统依赖..."
sudo apt-get update -qq
# sudo apt-get install -y python3-venv python3-pip postgresql nginx -qq
sudo -qq

# ---- 2. 创建应用目录 ----
echo "[2/7] 创建应用目录..."
sudo mkdir -p $APP_DIR
sudo cp -r $REPO_DIR/app $APP_DIR/
sudo cp -r $REPO_DIR/alembic $APP_DIR/
sudo cp -r $REPO_DIR/scripts $APP_DIR/
sudo cp $REPO_DIR/alembic.ini $APP_DIR/
sudo cp $REPO_DIR/Makefile $APP_DIR/
sudo cp $REPO_DIR/pyproject.toml $APP_DIR/ 2>/dev/null || true
sudo cp $REPO_DIR/requirements.txt $APP_DIR/

# ---- 3. 创建 Python 虚拟环境并安装依赖 ----
echo "[3/7] 安装 Python 依赖..."
if [ ! -d "$APP_DIR/.venv" ]; then
    sudo python3 -m venv $APP_DIR/.venv
fi
# 使用项目中的 requirements.txt 安装，不再硬编码包列表
sudo $APP_DIR/.venv/bin/pip install -q -r $APP_DIR/requirements.txt

# ---- 4. 构建前端 ----
echo "[4/7] 构建前端..."
if command -v npm &> /dev/null; then
    cd $REPO_DIR/frontend && npm install --quiet && npm run build
else
    echo "  跳过：服务器未安装 npm，请本地构建后将 frontend/dist 上传"
fi
sudo mkdir -p $APP_DIR/frontend
sudo cp -r $REPO_DIR/frontend/dist $APP_DIR/frontend/

# ---- 5. 配置环境变量 ----
echo "[5/7] 配置环境变量..."
if [ ! -f "$APP_DIR/.env" ]; then
    sudo bash -c "cat > $APP_DIR/.env << 'ENVEOF'
APP_DATABASE_URL=postgresql+psycopg://crm:替换为你的密码@127.0.0.1:5432/crm
APP_JWT_SECRET_KEY=替换为一个随机字符串
APP_ACCESS_TOKEN_TTL_MINUTES=60
APP_REFRESH_TOKEN_TTL_DAYS=7
ENVEOF"
    echo "  已生成 .env 模板，请编辑 $APP_DIR/.env 填写实际值"
fi

# ---- 6. 配置 Nginx ----
echo "[6/7] 配置 Nginx..."
sudo cp $REPO_DIR/deploy/nginx.conf /etc/nginx/sites-available/crm
sudo ln -sf /etc/nginx/sites-available/crm /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl enable nginx && sudo systemctl reload nginx

# ---- 7. 配置 Systemd 服务 ----
echo "[7/7] 配置 Systemd 服务..."
sudo cp $REPO_DIR/deploy/crm.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable crm

# ---- 设置文件权限 ----
sudo chown -R www-data:www-data $APP_DIR

echo ""
echo "===== 部署完成 ====="
echo ""
echo "后续步骤："
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
echo "  bash deploy/deploy.sh   # 重新执行此脚本即可"
