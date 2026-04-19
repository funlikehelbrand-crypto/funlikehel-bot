@echo off
chcp 65001 >nul
echo Uruchamiam FUN like HEL bota...
echo Ctrl+C aby zatrzymac
echo.
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
pause
