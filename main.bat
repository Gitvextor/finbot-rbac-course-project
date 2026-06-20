@echo off
cd /d "%~dp0"
set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%finbot-frontend"
set "PYTHON_EXE=D:\finbot\.venv\Scripts\python.exe"

echo ==========================================
echo FinBot one-click demo launcher
echo ==========================================
echo.

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python environment not found: D:\finbot\.venv
    echo Please create the environment and install backend requirements first.
    pause
    exit /b 1
)

if not exist "%FRONTEND%\node_modules" (
    echo [ERROR] Frontend dependencies not found: finbot-frontend\node_modules
    echo Please run npm install in finbot-frontend first.
    pause
    exit /b 1
)

echo Starting backend at http://127.0.0.1:8000 ...
start "FinBot Backend" "%ROOT%scripts\start_backend.bat"

echo Starting frontend at http://localhost:3000 ...
start "FinBot Frontend" "%ROOT%scripts\start_frontend.bat"

echo.
echo When both windows finish starting, open:
echo http://localhost:3000
echo.
echo Demo accounts use password: password123
echo CEO account: ceo
echo Employee account: employee_demo
echo.
pause
