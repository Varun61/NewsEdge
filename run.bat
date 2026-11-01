@echo off
title NewsEdge - Indian Stock Market Intelligence
cd /d "%~dp0"

echo =====================================================================
echo Starting NewsEdge Automated Pipeline...
echo =====================================================================

if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe run_newsedge.py %*
) else (
    python run_newsedge.py %*
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] NewsEdge encountered an issue. Check the output above.
)

echo.
echo Press any key to close this window...
pause >nul
