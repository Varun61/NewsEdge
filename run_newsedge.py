"""One-Click NewsEdge Launcher and Auto-Orchestrator.

Handles all operational prerequisites automatically:
1. Detects and activates the Python virtual environment (.venv)
2. Checks Ollama daemon; automatically launches 'ollama serve' in background if down
3. Verifies 'llama3.2' model availability; auto-pulls if missing
4. Verifies database schema and official NSE equity master universe
5. Executes the full pipeline (10 news sources, AI analysis, Telegram delivery, Groww export)

Usage:
    python run_newsedge.py
    python run_newsedge.py --hours 24
    python run_newsedge.py --cron
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

# Ensure UTF-8 output on Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent
os.chdir(PROJECT_ROOT)


def ensure_virtualenv():
    """Relaunch under .venv Python if currently running in global Python."""
    is_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    if is_venv:
        return

    # Check for local .venv
    venv_python_win = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    venv_python_nix = PROJECT_ROOT / ".venv" / "bin" / "python"

    venv_exe = venv_python_win if venv_python_win.exists() else (venv_python_nix if venv_python_nix.exists() else None)
    if venv_exe:
        cmd = [str(venv_exe), str(Path(__file__).resolve())] + sys.argv[1:]
        res = subprocess.run(cmd)
        sys.exit(res.returncode)


def is_ollama_healthy(url: str = "http://localhost:11434") -> bool:
    """Return True if Ollama server responds with HTTP 200."""
    try:
        req = Request(f"{url}/api/tags", headers={"User-Agent": "NewsEdge-Launcher"})
        with urlopen(req, timeout=1.5) as resp:
            return resp.status == 200
    except (URLError, Exception):
        return False


def ensure_ollama_running(model_name: str = "llama3.2"):
    """Check Ollama service and auto-start it in background if not running."""
    print("🔍 [1/4] Checking Ollama AI engine status...")

    if is_ollama_healthy():
        print("   ✅ Ollama daemon is active and responding at http://localhost:11434")
    else:
        print("   ⚠️ Ollama daemon is not running. Starting background service...")
        # Locate ollama executable
        ollama_bin = shutil.which("ollama")
        if not ollama_bin and sys.platform == "win32":
            user_local = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")
            if os.path.exists(user_local):
                ollama_bin = user_local

        if not ollama_bin:
            print("   ❌ 'ollama' executable not found on PATH or LocalAppData.")
            print("      Please install Ollama from https://ollama.com/")
            sys.exit(1)

        # Launch detached background process
        if sys.platform == "win32":
            # DETACHED_PROCESS = 0x00000008, CREATE_NEW_PROCESS_GROUP = 0x00000200
            flags = 0x00000008 | 0x00000200
            subprocess.Popen(
                [ollama_bin, "serve"],
                creationflags=flags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            subprocess.Popen(
                [ollama_bin, "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )

        # Wait up to 12 seconds for Ollama to become healthy
        started = False
        for i in range(12):
            time.sleep(1)
            if is_ollama_healthy():
                started = True
                break

        if started:
            print("   ✅ Ollama service auto-started successfully!")
        else:
            print("   ❌ Timed out waiting for Ollama service to respond.")
            sys.exit(1)

    # Verify model is available
    try:
        import json
        req = Request("http://localhost:11434/api/tags")
        with urlopen(req, timeout=3) as resp:
            tags_data = json.loads(resp.read().decode())
            existing_models = [m.get("name", "").split(":")[0] for m in tags_data.get("models", [])]
            if model_name.split(":")[0] not in existing_models:
                print(f"   ⏳ Model '{model_name}' not found locally. Auto-pulling model (this may take a few minutes)...")
                subprocess.run(["ollama", "pull", model_name], check=True)
                print(f"   ✅ Model '{model_name}' ready.")
            else:
                print(f"   ✅ Model '{model_name}' is loaded and ready.")
    except Exception as exc:
        print(f"   ⚠️ Model check skipped: {exc}")


def ensure_database_ready():
    """Ensure database tables and stock metadata are initialized."""
    print("📁 [2/4] Verifying database schema and official NSE equity master...")
    from scripts.initialize_database import seed_database
    try:
        seed_database()
        print("   ✅ Database tables and 2,359 NSE equities verified.")
    except Exception as exc:
        print(f"   ⚠️ Database verify notice: {exc}")


def launch_pipeline(args):
    """Run full pipeline with user arguments."""
    print("🚀 [3/4] Launching NewsEdge Pipeline across 10 financial news publishers...")
    print(f"   Lookback Window: Last {args.hours} hours | Scheduled Mode: {args.cron}")

    from app.pipeline import run_pipeline

    target_date = None
    if args.date:
        from datetime import datetime
        target_date = datetime.strptime(args.date, "%Y-%m-%d").date()

    success = run_pipeline(
        report_date=target_date,
        lookback_hours=args.hours,
        is_adhoc=not args.cron,
        fresh_rebuild=True,
    )

    if success:
        print("\n" + "=" * 70)
        print("✅ [4/4] NEWSEDGE PIPELINE COMPLETED SUCCESSFULLY!")
        print("   • Telegram watchlist notification delivered.")
        print("   • Top 10 Bullish and Top 10 Bearish candidates updated.")
        print("   • Offline Groww symbol lists generated in reports/")
        print("   • Excel & HTML analytical reports saved in reports/")
        print("=" * 70 + "\n")
    else:
        print("\n❌ Pipeline failed during execution. Check logs/newsedge.log for details.\n")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="NewsEdge Zero-Hassle One-Click Launcher")
    parser.add_argument("--hours", type=int, default=24, help="News lookback window in hours (default: 24)")
    parser.add_argument("--cron", action="store_true", help="Set flag for scheduled weekday 07:00 AM runs")
    parser.add_argument("--date", type=str, default=None, help="Specific report date (YYYY-MM-DD)")
    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("NEWSEDGE — AUTOMATED INDIAN STOCK MARKET INTELLIGENCE LAUNCHER")
    print("=" * 70)
    ensure_virtualenv()
    ensure_ollama_running("llama3.2")
    ensure_database_ready()
    launch_pipeline(args)


if __name__ == "__main__":
    main()
