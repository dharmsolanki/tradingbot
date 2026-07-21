@echo off

cd /d C:\Users\dharm\OneDrive\Desktop\trading_bot

echo Starting Trading Bot...

REM Start FastAPI Server
start "Trading Bot" cmd /k py -m uvicorn app.main:app --host 0.0.0.0 --port 8000

REM Wait for FastAPI to start
timeout /t 8 /nobreak >nul

echo Starting ngrok...

REM Start ngrok using your static domain
start "ngrok" cmd /k C:\Users\dharm\Downloads\ngrok.exe http --url=buckshot-contact-surfboard.ngrok-free.dev 8000

echo.
echo ==========================================
echo Trading Bot Started Successfully
echo Dashboard URL:
echo https://buckshot-contact-surfboard.ngrok-free.dev
echo ==========================================

pause