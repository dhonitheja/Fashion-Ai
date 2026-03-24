@echo off
echo Starting Sahion Mobile Test Server...
echo.

:: Get local IPv4 address
for /f "delims=[] tokens=2" %%a in ('ping -4 -n 1 %ComputerName% ^| findstr [') do set LOCAL_IP=%%a

echo Your phone MUST be connected to the exact same WiFi network as this computer!
echo Detected Local IP: %LOCAL_IP%
echo.

:: Update frontend .env.local to point to the computer's IP instead of localhost
echo VITE_API_URL=http://%LOCAL_IP%:8000 > "d:\Ideas\Sahion\poc\frontend\.env.local"

:: Start Backend on all network interfaces (0.0.0.0)
start "Sahion Mobile Backend" cmd /k "cd /d d:\Ideas\Sahion\poc\backend && uvicorn main:app --host 0.0.0.0 --port 8000"

:: Wait 3 seconds
timeout /t 3 /nobreak > nul

:: Start Frontend on all network interfaces
start "Sahion Mobile Frontend" cmd /k "cd /d d:\Ideas\Sahion\poc\frontend && npm run dev -- --host 0.0.0.0"

echo.
echo ========================================================
echo ON YOUR MOBILE PHONE, OPEN SAFARI OR CHROME AND GO TO:
echo http://%LOCAL_IP%:3000
echo ========================================================
echo.
echo Keep these terminal windows open while testing!
