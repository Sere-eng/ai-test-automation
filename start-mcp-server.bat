@echo off
REM Script per avviare il server MCP remoto

echo ========================================
echo   AVVIO SERVER MCP REMOTO
echo ========================================
echo.
echo Porta: 8001
echo Mode: HTTP
echo.

cd backend
call .venv\Scripts\activate
python mcp_servers\playwright_server_remote.py

pause
