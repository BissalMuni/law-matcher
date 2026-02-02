@echo off
chcp 65001 > nul
title Law Matcher - Stop Server

echo ========================================
echo   Law Matcher Server Stop
echo ========================================
echo.

:: Frontend stop (local)
echo [1/2] Stopping Frontend (local)...
taskkill /F /FI "WINDOWTITLE eq Law Matcher - Frontend*" >nul 2>&1
echo Frontend stopped

:: Docker containers stop (backend, worker)
echo [2/2] Stopping Docker containers (Backend, Worker)...
docker-compose stop backend worker
echo Backend/Worker stopped

echo.
echo ========================================
echo   Server stopped.
echo ========================================
echo.
echo   DB/Redis Docker containers are still running.
echo   Full stop: docker-compose down
echo.
pause
