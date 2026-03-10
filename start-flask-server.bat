@echo off
REM Script per avviare il Flask server

echo ========================================
echo   AVVIO FLASK SERVER
echo ========================================
echo.
echo Porta: 5000
echo URL: http://localhost:5000
echo.

cd backend
call .venv\Scripts\activate
python app.py

pause
