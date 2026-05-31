@echo off
cd /d E:\finbot-rbac-course-project-whq\backend
set FINBOT_RELOAD=0
set PYTHONIOENCODING=utf-8
"D:\finbot\.venv\Scripts\python.exe" main.py >> "E:\finbot-rbac-course-project-whq\backend_server.combined.log" 2>&1
