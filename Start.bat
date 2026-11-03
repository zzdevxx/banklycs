@echo off
title Banklycs - Worship Song Vault & Injector
cd /d "%~dp0"

echo ==============================================================================
echo   BANKLYCS - WORSHIP VAULT & PROPRESENTER INJECTOR
echo ==============================================================================
echo Memeriksa server aplikasi lokal...

:: Cek apakah server sudah berjalan di port 5050
netstat -ano | findstr :5050 >nul 2>&1
if %errorlevel% neq 0 (
    echo Menjalankan server aplikasi di latar belakang...
    start /B python app\server.py 5050
    timeout /t 2 /nobreak >nul
)

echo Membuka antarmuka Banklycs...

:: Buka dalam mode native app window menggunakan Microsoft Edge
start "" msedge --app=http://127.0.0.1:5050 --window-size=1600,900
if %errorlevel% neq 0 (
    start http://127.0.0.1:5050
)

exit
