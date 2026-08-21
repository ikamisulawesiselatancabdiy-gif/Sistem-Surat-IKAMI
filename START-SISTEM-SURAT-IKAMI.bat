@echo off
setlocal
cd /d "%~dp0"

echo ===============================================
echo Sistem Surat IKAMI
echo Membersihkan server lama pada port 8765...
echo ===============================================

for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":8765" ^| findstr "LISTENING"') do (
  echo Menghentikan PID %%P...
  taskkill /F /PID %%P >nul 2>&1
)

timeout /t 1 /nobreak >nul

where py >nul 2>&1
if %errorlevel%==0 (
  py server.py
) else (
  python server.py
)

endlocal
pause
