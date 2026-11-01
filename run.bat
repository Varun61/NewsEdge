@echo off
title NewsEdge - Indian Stock Market Intelligence
:: Ensure working directory is set to NewsEdge repository root
if exist "%~dp0run_newsedge.py" (
    cd /d "%~dp0"
) else (
    cd /d "C:\Users\varun\NewsEdge"
)

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
