@echo off
setlocal

set "SCRIPT_DIR=%~dp0"

echo [1/3] Stopping existing funnel mapping...
call "%SCRIPT_DIR%stop_funnel.cmd"
if errorlevel 1 (
  echo [ERROR] stop_funnel.cmd failed.
  exit /b 1
)

echo [2/3] Starting app and funnel...
call "%SCRIPT_DIR%start_funnel.cmd"
if errorlevel 1 (
  echo [ERROR] start_funnel.cmd failed.
  exit /b 1
)

echo [3/3] Restart completed.
endlocal
