@echo off
title AI Traffic Management - Cloudflare Tunnel Launcher
color 0B
echo ========================================================
echo   Starting Cloudflare Tunnel for AI Traffic Management
echo ========================================================
echo.
echo Connecting local server (http://127.0.0.1:8000) to Cloudflare Edge Network...
echo.
"%~dp0cloudflared.exe" tunnel --url http://127.0.0.1:8000
pause
vhttp://convicted-makes-came-merchandise.trycloudflare.com/frontend/index.html2