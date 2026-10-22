@echo off
REM One-time setup on Windows: Python venv, dashboard build, desktop icon + start at login.
setlocal
cd /d "%~dp0"

where python >nul 2>nul || (echo Python 3.10+ is required: https://www.python.org/downloads/ & pause & exit /b 1)
where npm >nul 2>nul || (echo Node.js 18+ is required: https://nodejs.org/ & pause & exit /b 1)

echo [1/3] Installing Python packages...
if not exist backend\.venv python -m venv backend\.venv
call backend\.venv\Scripts\python -m pip install --upgrade pip >nul
call backend\.venv\Scripts\python -m pip install -r backend\requirements.txt || goto :fail

echo [2/3] Building the TypeScript dashboard...
pushd frontend
call npm install --no-audit --no-fund || goto :fail
call npm run build || goto :fail
popd

echo [3/3] Adding desktop icon and start-at-login...
call backend\.venv\Scripts\python scripts\autostart.py install || goto :fail

echo.
echo Done. Launching EGX Monitor...
cd backend
start "" .venv\Scripts\pythonw -m egx_monitor
exit /b 0

:fail
echo Setup failed - see the messages above.
pause
exit /b 1
