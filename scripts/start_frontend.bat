@echo off
cd /d "%~dp0..\finbot-frontend"

if not exist "node_modules" (
    echo [ERROR] Frontend dependencies not found.
    echo Please run npm install in finbot-frontend first.
    pause
    exit /b 1
)

echo Starting FinBot frontend on http://localhost:3000
npm.cmd run dev
pause
