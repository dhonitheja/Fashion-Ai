@echo off
echo Starting Sahion AI Fashion Stylist...
echo.

:: Kill any old backend processes
echo Stopping old servers...
taskkill /IM python3.13.exe /F >nul 2>&1
taskkill /IM python.exe /F >nul 2>&1
timeout /t 2 /nobreak >nul

:: Start Backend
start "Sahion Backend" cmd /k "cd /d d:\Ideas\Sahion\poc\backend && uvicorn main:app --port 8000"

:: Wait for backend to start
timeout /t 4 /nobreak >nul

:: Start Frontend
start "Sahion Frontend" cmd /k "cd /d d:\Ideas\Sahion\poc\frontend && npm run dev"

:: Wait for frontend to start
timeout /t 5 /nobreak >nul

:: Open browser
start http://localhost:3000

echo Both servers started.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
