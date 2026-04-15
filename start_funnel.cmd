@echo off
setlocal enabledelayedexpansion

REM ====== Config ======
set "PROJECT_DIR=D:\project\python\fastapi"
set "PYTHON_EXE=%PROJECT_DIR%\.venv\Scripts\python.exe"
set "APP_MODULE=app.main:app"
set "PORT=8001"

echo [1/5] Checking project directory...
if not exist "%PROJECT_DIR%" (
  echo [ERROR] Project directory not found: %PROJECT_DIR%
  exit /b 1
)

echo [2/5] Checking python executable...
if not exist "%PYTHON_EXE%" (
  echo [ERROR] Python not found: %PYTHON_EXE%
  echo Create venv first: python -m venv .venv
  exit /b 1
)

echo [3/5] Checking tailscale CLI...
where tailscale >nul 2>nul
if errorlevel 1 (
  echo [ERROR] tailscale command not found in PATH.
  echo Please install Tailscale and login first.
  exit /b 1
)

echo [4/5] Starting FastAPI in a new window...
start "FastAPI-Uvicorn" cmd /k "cd /d %PROJECT_DIR% && "%PYTHON_EXE%" -m uvicorn %APP_MODULE% --host 127.0.0.1 --port %PORT%"

echo Waiting 3 seconds for app startup...
timeout /t 3 /nobreak >nul

echo [5/5] Enabling Tailscale Funnel...
tailscale funnel reset >nul 2>nul
tailscale serve reset >nul 2>nul

tailscale serve --bg http://127.0.0.1:%PORT%
if errorlevel 1 (
  echo [ERROR] Failed to configure tailscale serve for port %PORT%.
  echo Run: tailscale status
  exit /b 1
)

tailscale funnel --bg %PORT%
if errorlevel 1 (
  echo [ERROR] Failed to enable tailscale funnel on port %PORT%.
  echo Run these checks:
  echo   tailscale status
  echo   tailscale serve status
  echo   tailscale funnel status
  exit /b 1
)

set "FUNNEL_URL="
for /f "tokens=* delims=" %%L in ('tailscale funnel status ^| findstr /I "https://"') do (
  set "FUNNEL_URL=%%L"
)

if not defined FUNNEL_URL (
  echo [ERROR] Funnel appears not configured. tailscale reported no public HTTPS URL.
  echo tailscale funnel status output:
  tailscale funnel status
  exit /b 1
)

echo.
echo ====== Done ======
echo App local:   http://127.0.0.1:%PORT%
echo Share URL:   !FUNNEL_URL!
echo Funnel info:
tailscale funnel status
echo.
echo Tips:
echo - Stop app: close window "FastAPI-Uvicorn"
echo - Disable funnel: tailscale funnel reset
echo - Disable serve: tailscale serve reset
echo - Check serving: tailscale serve status

echo.
endlocal
