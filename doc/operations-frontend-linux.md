# CRM 前端服务操作手册 — Linux 生产环境

适用环境：Ubuntu 22.04 LTS 64bit

> 生产环境中**没有前端开发服务进程**，前端以静态文件形式由 Nginx 托管。
> 部署流程：安装依赖 → 构建生成 `dist/` → Nginx 提供静态文件服务。

---

## 目录

1. [Node.js 安装](#1-nodejs-安装)
2. [依赖安装](#2-依赖安装)
3. [构建前端](#3-构建前端)
4. [部署方式 A：服务器上构建](#4-部署方式-a服务器上构建)
5. [部署方式 B：本地构建后上传](#5-部署方式-b本地构建后上传)
6. [Nginx 托管配置](#6-nginx-托管配置)
7. [前端更新部署流程](#7-前端更新部署流程)
8. [版本回滚](#8-版本回滚)
9. [前端测试](#9-前端测试)
10. [常见问题](#10-常见问题)
11. [命令速查表](#11-命令速查表)

---

## 1. Node.js 安装

Ubuntu 22.04 默认源的 Node.js 版本较旧（v12），建议通过 NodeSource 安装 v20 LTS。

### 安装 NodeSource 20.x

```bash
# 添加 NodeSource 源
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -

# 安装 Node.js（包含 npm）
sudo apt-get install -y nodejs
```

### 验证安装

```bash
node --version   # 应输出 v20.x.x
npm --version    # 应输出 10.x.x 或 9.x.x
```

### 不安装 Node.js 的替代方案

如果不想在服务器上安装 Node.js，可以使用 [方式 B：本地构建后上传](#5-部署方式-b本地构建后上传)，在 Windows 上构建后将 `dist/` 目录上传到服务器即可。

---

## 2. 依赖安装

### 首次安装

```bash
cd /opt/crm/frontend
npm install
```

### 更新依赖（package.json 变更后）

```bash
cd /opt/crm/frontend
npm install --quiet
```

### 使用国内镜像（可选）

```bash
npm config set registry https://registry.npmmirror.com
cd /opt/crm/frontend
npm install
```

---

## 3. 构建前端

### 构建命令

```bash
cd /opt/crm/frontend
npm run build
```

构建过程包含两步（`package.json` 中的 `build` 脚本已配置）：
1. `tsc -b` — TypeScript 类型编译检查
2. `vite build` — 打包生成生产版本

### 构建产物

```
/opt/crm/frontend/dist/
├── index.html              # SPA 入口
└── assets/
    ├── index-xxxx.css      # 样式文件（文件名含内容哈希）
    └── index-xxxx.js       # JavaScript 文件（文件名含内容哈希）
```

每次构建后文件名中的哈希值会变化，确保用户拿到最新版本。

### 验证构建

```bash
# 检查产物目录
ls -la /opt/crm/frontend/dist/

# 应该看到 index.html 和 assets/ 目录
# 如果 dist/ 不存在或为空，说明构建失败，检查上一步的错误信息
```

### 构建时间

首次构建约 30 秒，增量构建约 5-10 秒。

---

## 4. 部署方式 A：服务器上构建

适用于服务器已安装 Node.js 的情况。

### 首次部署

```bash
# 1. 确认前端源码已复制到服务器
ls /opt/crm/frontend/package.json

# 2. 安装依赖
cd /opt/crm/frontend
npm install

# 3. 构建
npm run build

# 4. 验证产物
ls -la /opt/crm/frontend/dist/index.html

# 5. 修复权限
sudo chown -R www-data:www-data /opt/crm/frontend/dist
```

首次部署后 Nginx 即可提供前端静态文件服务，无需重启任何服务。

### 日常更新

```bash
# 1. 更新前端源码（从部署脚本或手动复制）
sudo cp -r app /opt/crm/  # 如果前端源码随 app 一起更新

# 2. 安装依赖（如果 package.json 有变更）
cd /opt/crm/frontend
npm install --quiet

# 3. 重新构建
npm run build

# 4. 修复权限
sudo chown -R www-data:www-data /opt/crm/frontend/dist

# 5. 无需重启任何服务，Nginx 直接提供新的静态文件
```

---

## 5. 部署方式 B：本地构建后上传

适用于服务器没有 Node.js 的情况，在 Windows 本地构建后上传 `dist/` 目录。

### 步骤一：Windows 本地构建

```bash
# 在 Windows 项目根目录执行
npm --prefix frontend run build
```

确认 `frontend/dist/index.html` 已生成。

### 步骤二：上传到服务器

```bash
# 方式一：scp（简单直接）
scp -r frontend/dist 用户名@服务器IP:/tmp/crm-dist/

# 方式二：rsync（增量同步，只传输变化的文件，更快）
rsync -avz --delete frontend/dist/ 用户名@服务器IP:/tmp/crm-dist/
```

### 步骤三：服务器上替换

```bash
# 1. 备份当前版本（推荐）
sudo cp -r /opt/crm/frontend/dist /opt/crm/frontend/dist.bak

# 2. 删除旧版本
sudo rm -rf /opt/crm/frontend/dist

# 3. 复制新版本
sudo cp -r /tmp/crm-dist /opt/crm/frontend/dist

# 4. 修复权限
sudo chown -R www-data:www-data /opt/crm/frontend/dist

# 5. 确认文件已就位
ls -la /opt/crm/frontend/dist/index.html
```

### 一键上传脚本（可选）

在 Windows 上可以创建一个上传脚本 `deploy/upload-frontend.sh`，简化操作：

```bash
#!/bin/bash
# 在 Windows 上通过 WSL 或 Git Bash 执行
SERVER="用户名@服务器IP"
DIST_DIR="/opt/crm/frontend/dist"

echo "构建前端..."
npm --prefix frontend run build

echo "上传到服务器..."
rsync -avz --delete frontend/dist/ $SERVER:/tmp/crm-dist/

echo "替换服务器上的文件..."
ssh $SERVER "sudo rm -rf $DIST_DIR && sudo cp -r /tmp/crm-dist $DIST_DIR && sudo chown -R www-data:www-data $DIST_DIR && echo '前端部署完成'"
```

---

## 6. Nginx 托管配置

Nginx 已在首次部署时配置好，前端相关的关键规则：

```nginx
server {
    listen 80;
    server_name _;

    # 前端静态文件根目录
    root /opt/crm/frontend/dist;
    index index.html;

    # Gzip 压缩（1.3MB → ~400KB）
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml;
    gzip_min_length 256;

    # 带哈希的静态资源 — 长期缓存
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

    # SPA 路由回退 — 非 /api 路径返回 index.html
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

配置文件位置：`/etc/nginx/sites-available/crm`

### 修改 Nginx 配置后

```bash
# 验证配置语法
sudo nginx -t

# 重载生效（不断开现有连接）
sudo systemctl reload nginx
```

---

## 7. 前端更新部署流程

### 按变更类型选择步骤

| 变更类型 | 需要的步骤 |
|---------|-----------|
| 仅前端页面/组件变更 | 构建前端 → 更新 dist → 无需重启后端 |
| 前端 + 新增 npm 依赖 | 安装依赖 → 构建前端 → 更新 dist |
| 仅后端变更 | 无需操作前端 |
| 全栈变更 | 更新后端 → 构建前端 → 重启后端 |

### 方式 A 更新流程（服务器有 Node.js）

```bash
# 1. 确认前端源码已更新
cd /opt/crm/frontend

# 2. 安装依赖（如果 package.json 有变更）
npm install --quiet

# 3. 构建
npm run build

# 4. 修复权限
sudo chown -R www-data:www-data /opt/crm/frontend/dist

# 5. 无需重启任何服务
```

### 方式 B 更新流程（本地构建上传）

```bash
# 1. Windows 本地构建
npm --prefix frontend run build

# 2. 上传
rsync -avz --delete frontend/dist/ 用户名@服务器IP:/tmp/crm-dist/

# 3. 服务器上替换
ssh 用户名@服务器IP "sudo rm -rf /opt/crm/frontend/dist && sudo cp -r /tmp/crm-dist /opt/crm/frontend/dist && sudo chown -R www-data:www-data /opt/crm/frontend/dist"
```

### 用户浏览器缓存

前端更新后，用户浏览器可能缓存了旧版本。处理方式：

- 带哈希文件名的资源（`/assets/index-xxxx.js`）会自动更新，因为文件名变了
- `index.html` 不设置缓存，每次请求都会拿到最新版
- 如果用户仍看到旧版本，建议其 `Ctrl+Shift+R` 强制刷新

---

## 8. 版本回滚

### 方式一：使用备份回滚（最快）

部署前备份当前 `dist/`，出问题时立即恢复：

```bash
# 部署前备份
sudo cp -r /opt/crm/frontend/dist /opt/crm/frontend/dist.bak

# 回滚
sudo rm -rf /opt/crm/frontend/dist
sudo mv /opt/crm/frontend/dist.bak /opt/crm/frontend/dist
```

### 方式二：从旧版本源码重新构建

```bash
# 1. 在本地切回上一个 git 版本
git checkout 上一个commit -- frontend/

# 2. 重新构建
npm --prefix frontend run build

# 3. 上传并替换（同方式 B 的步骤二、三）
```

### 方式三：使用 git 回退后服务器上构建

```bash
# 1. 在服务器上回退前端源码
cd /opt/crm
sudo git checkout 上一个commit -- frontend/

# 2. 安装依赖并构建
cd /opt/crm/frontend
npm install --quiet
npm run build

# 3. 修复权限
sudo chown -R www-data:www-data /opt/crm/frontend/dist
```

---

## 9. 前端测试

### 运行测试

```bash
cd /opt/crm/frontend
npm test
```

### 代码检查

```bash
cd /opt/crm/frontend
npm run lint
```

### TypeScript 类型检查

```bash
cd /opt/crm/frontend
npx tsc --noEmit
```

> 前端测试通常在本地开发时运行，生产服务器上一般不需要执行。如需在服务器上运行测试，需确保已安装 `node_modules` 中的开发依赖。

---

## 10. 常见问题

| 问题 | 解决方案 |
|------|---------|
| 服务器没有 npm | 使用方式 B（本地构建后上传 dist），或安装 Node.js |
| `npm install` 很慢 | 配置国内镜像：`npm config set registry https://registry.npmmirror.com` |
| `npm run build` 报 TypeScript 错误 | 先运行 `npx tsc --noEmit` 查看具体类型错误，修复后再构建 |
| 构建后 Nginx 仍返回旧版本 | 检查 `ls -la /opt/crm/frontend/dist/assets/` 确认文件修改时间已更新 |
| 静态资源 404 | 检查 `/opt/crm/frontend/dist/assets/` 目录是否存在；检查权限：`sudo chown -R www-data:www-data /opt/crm/frontend/dist` |
| 页面空白 | 检查 `dist/index.html` 是否存在；查看 Nginx 错误日志：`sudo tail -f /var/log/nginx/error.log` |
| 用户反馈页面没更新 | 可能是浏览器缓存，建议 `Ctrl+Shift+R` 强制刷新 |
| `dist/` 目录不存在 | 前端未构建，先执行 `cd /opt/crm/frontend && npm run build` |
| 构建产物体积过大警告 | 正常现象，Nginx 已配置 gzip 压缩，实际传输约 300-400KB |
| `node_modules` 损坏 | 删除后重装：`rm -rf /opt/crm/frontend/node_modules && cd /opt/crm/frontend && npm install` |
| 权限错误 | `sudo chown -R www-data:www-data /opt/crm/frontend/dist` |

---

## 11. 命令速查表

### Node.js 管理

| 操作 | 命令 |
|------|------|
| 安装 Node.js 20 | `curl -fsSL https://deb.nodesource.com/setup_20.x \| sudo -E bash - && sudo apt-get install -y nodejs` |
| 验证版本 | `node --version` |
| 验证 npm | `npm --version` |

### 依赖与构建

| 操作 | 命令 |
|------|------|
| 安装依赖 | `cd /opt/crm/frontend && npm install` |
| 更新依赖 | `cd /opt/crm/frontend && npm install --quiet` |
| 构建 | `cd /opt/crm/frontend && npm run build` |
| 验证产物 | `ls -la /opt/crm/frontend/dist/` |
| 修复权限 | `sudo chown -R www-data:www-data /opt/crm/frontend/dist` |

### 部署与回滚

| 操作 | 命令 |
|------|------|
| 备份当前版本 | `sudo cp -r /opt/crm/frontend/dist /opt/crm/frontend/dist.bak` |
| 回滚到备份 | `sudo rm -rf /opt/crm/frontend/dist && sudo mv /opt/crm/frontend/dist.bak /opt/crm/frontend/dist` |
| 本地构建上传 | `npm --prefix frontend run build && rsync -avz --delete frontend/dist/ 服务器:/tmp/crm-dist/` |
| 服务器替换 | `sudo rm -rf /opt/crm/frontend/dist && sudo cp -r /tmp/crm-dist /opt/crm/frontend/dist && sudo chown -R www-data:www-data /opt/crm/frontend/dist` |

### 测试与检查

| 操作 | 命令 |
|------|------|
| 运行测试 | `cd /opt/crm/frontend && npm test` |
| 代码检查 | `cd /opt/crm/frontend && npm run lint` |
| 类型检查 | `cd /opt/crm/frontend && npx tsc --noEmit` |

### Nginx

| 操作 | 命令 |
|------|------|
| 验证配置 | `sudo nginx -t` |
| 重载配置 | `sudo systemctl reload nginx` |
| 查看错误日志 | `sudo tail -f /var/log/nginx/error.log` |
