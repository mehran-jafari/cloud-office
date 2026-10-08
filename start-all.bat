@echo off
cd /d %~dp0
start "CloudOffice-Backend" cmd /k start-backend.bat
timeout /t 3 /nobreak >nul
start "CloudOffice-Frontend" cmd /k start-frontend.bat
echo Backend و Frontend در دو پنجره ترمینال جدا اجرا شدند.
