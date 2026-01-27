@echo off
chcp 65001 > nul
title Law Matcher - Local Server

echo ========================================
echo   Law Matcher Local Server Start
echo ========================================
echo   Backend/DB/Redis: Docker
echo   Frontend: Local (for network access)
echo ========================================
echo.

:: Project root directory
set PROJECT_ROOT=%~dp0

:: Docker Backend/DB/Redis start
echo [1/3] Docker (Backend, PostgreSQL, Redis) starting...
docker-compose up -d backend db redis worker
if %errorlevel% neq 0 (
    echo [ERROR] Docker start failed! Check if Docker Desktop is running.
    pause
    exit /b 1
)
echo Docker containers running
echo.

:: Wait for Backend to be ready
echo [2/3] Waiting for Backend to start...
timeout /t 5 /nobreak > nul
echo.

:: Frontend start (new window)
echo [3/3] Frontend server starting (local)...
start "Law Matcher - Frontend" cmd /k "cd /d %PROJECT_ROOT%frontend && npm run dev"

echo.
echo ========================================
echo   Server started!
echo ========================================
echo.
echo   Frontend: http://localhost:3000
echo   Backend:  http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo.
echo   [Network Access]
echo   Other PCs can connect via your IP:3000
echo.
echo   Stop: run stop-local.bat
echo ========================================
pause
