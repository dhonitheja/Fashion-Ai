@echo off
echo Starting Sahion AI Fashion Stylist...
echo.

:: Start Backend
start "Sahion Backend" cmd /k "cd /d d:\Ideas\Sahion\poc\backend && uvicorn main:app --reload --port 8000"

:: Wait 3 seconds for backend to start
timeout /t 3 /nobreak > nul

:: Start Frontend
start "Sahion Frontend" cmd /k "cd /d d:\Ideas\Sahion\poc\frontend && npm run dev"

:: Wait 5 seconds for frontend to start
timeout /t 5 /nobreak > nul

:: Open browser
start http://localhost:3000

echo.
echo Both servers are starting...
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo.
echo Close the two terminal windows to stop the servers.
