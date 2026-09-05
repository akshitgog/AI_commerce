@echo off
REM Start Frontend on port 3000
echo Starting Frontend on http://127.0.0.1:3000...
echo.

cd /d "%~dp0\frontend"
call npm run dev

pause
