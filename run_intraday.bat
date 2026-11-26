@echo off
chcp 65001 >nul
title STOCKSCOPE 360 — Live Intraday Scanner

echo.
echo ========================================================================
echo   STOCKSCOPE 360 — LIVE 5-MIN INTRADAY SCANNER (Angel One SmartAPI)
echo ========================================================================
echo   Scans NewsEdge watchlist every 5 minutes (9:15 AM - 3:25 PM IST)
echo   Checks VWAP, Opening Range (9:15-9:30), RSI-14, EMA-9, RelVol
echo   Pushes confirmed LONG/SHORT playbooks to Telegram.
echo ========================================================================
echo.

cd /d "%~dp0"
.venv\Scripts\python.exe -m app.intraday_runner --loop --interval 300 --telegram %*

echo.
pause
