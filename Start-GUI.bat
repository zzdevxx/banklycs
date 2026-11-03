@echo off
title Banklycs - GUI Launcher
cd /d "%~dp0"

echo ==============================================================================
echo   BANKLYCS - PLAYLIST BUILDER FOR PROPRESENTER
echo ==============================================================================
echo Menjalankan server lokal di latar belakang...

:: Cek apakah server sudah berjalan di port 5050
netstat -ano | findstr :5050 >nul 2>&1
if %errorlevel% neq 0 (
    start /B python gui\server.py 5050
    timeout /t 2 /nobreak >nul
)

echo Membuka antarmuka aplikasi...

:: Buka dalam mode native app window menggunakan Microsoft Edge
start "" msedge --app=http://127.0.0.1:5050 --window-size=1600,900
if %errorlevel% neq 0 (
    start http://127.0.0.1:5050
)

exit
