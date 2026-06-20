@echo off
cd /d "%~dp0..\backend"
set FINBOT_RELOAD=0
set FINBOT_SKIP_RAG=1
set PYTHONIOENCODING=utf-8

if not exist "D:\finbot\.venv\Scripts\python.exe" (
    echo [ERROR] Python environment not found: D:\finbot\.venv
    pause
    exit /b 1
)

echo Starting FinBot backend on http://127.0.0.1:8000
"D:\finbot\.venv\Scripts\python.exe" main.py
pause
