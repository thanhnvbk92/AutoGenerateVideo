@echo off
title Auto Video Generator Launcher
echo ===================================================
echo   KHOI DONG AUTO VIDEO GENERATOR (FASTAPI + REACT)
echo ===================================================
echo.

echo [1/2] Dang khoi dong Backend FastAPI (Port 8000)...
start "Backend - FastAPI" cmd /k "cd /d %~dp0backend && venv\Scripts\activate && python -m uvicorn app.main:app --reload --port 8000 --host 127.0.0.1"

echo [2/2] Dang khoi dong Frontend React Vite...
start "Frontend - React Vite" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ===================================================
echo   Khoi dong hoan tat!
echo   - Backend run at: http://127.0.0.1:8000
echo   - Frontend se hien thi cong o cua so CMD ben canh (mac dinh http://localhost:5173 hoac 5174).
echo ===================================================
pause
