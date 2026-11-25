@echo off
chcp 65001 >nul
title NewsEdge — Yesterday Close to Now

echo.
echo ========================================================================
echo   NEWSEDGE — FROM YESTERDAY'S 15:30 IST CLOSE TO NOW
echo ========================================================================
echo   This run collects all news from yesterday's 3:30 PM market close
echo   until the current time. Use this on market holidays or weekends.
echo ========================================================================
echo.

cd /d "%~dp0"
.venv\Scripts\python.exe run_newsedge.py --from-yesterday-close %*

echo.
pause
