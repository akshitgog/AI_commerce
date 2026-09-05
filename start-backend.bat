@echo off
REM Start Backend on port 8001
echo Starting Backend on http://127.0.0.1:8001...
echo.

cd /d "%~dp0"
.venv\Scripts\python.exe -m uvicorn ai_commerce_gateway.api.app:app --host 127.0.0.1 --port 8001 --reload

pause
