# fastapi

# 开启虚拟环境
```bash
source .venv/bin/activate
```

# 关闭虚拟环境
```bash
deactivate
```

# 导入依赖
```bash
pip freeze > requirements.txt
```

# 安装依赖
```bash
pip install -r requirements.txt
```

# 运行项目
```bash
uvicorn app.main:app --reload
```


# Windows (cmd.exe) — 创建与激活虚拟环境
```cmd
REM 在项目根目录运行：
python -m venv .venv
.venv\Scripts\activate.bat
```

# Windows (PowerShell)
```powershell
# 创建并激活（如果遇到执行策略阻止，参考下文）
python -m venv .venv
.venv\Scripts\Activate.ps1
```

# 如果需要重建虚拟环境（删除并重新创建）
```cmd
deactivate
rmdir /S /Q .venv
python -m venv .venv
.venv\Scripts\activate.bat
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

# PowerShell 策略（可选）
```powershell
# 如果在 PowerShell 激活时报 ExecutionPolicy 错误，可运行：
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

# 运行项目（cmd）
## 运行后端开发服务器
```cmd
cd /D D:\project\python\fastapi && .venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## 运行前端开发服务器
```cmd
npm --prefix "D:/project/python/fastapi/frontend" run build
```