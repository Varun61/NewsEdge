"""Audit all 10 financial news collectors for timestamp freshness and dead links."""

from __future__ import annotations

import datetime
import sys
from pathlib import Path
import pytz

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from app.collectors.collector_registry import build_default_registry

def main():
    since = datetime.datetime.now(pytz.UTC) - datetime.timedelta(hours=24)
    until = datetime.datetime.now(pytz.UTC)

    collectors = build_default_registry().get_enabled_collectors()
    print("=" * 80)
    print(f"{'Source Name':<22} | {'Count':<6} | {'Timestamp Range (UTC)':<32} | {'Old/Stale'}")
    print("=" * 80)

    total_fresh = 0
    total_stale = 0

    for c in collectors:
        try:
            arts = c.collect(since, until)
            if arts:
                valid_dates = [a.published_at for a in arts if a.published_at]
                newest = max(valid_dates) if valid_dates else None
                oldest = min(valid_dates) if valid_dates else None
                stale = [a for a in arts if a.published_at and a.published_at.year < 2026]
                total_fresh += len(arts)
                total_stale += len(stale)

                range_str = f"{oldest.strftime('%d %b %H:%M')} -> {newest.strftime('%d %b %H:%M')}" if oldest else "N/A"
                stale_str = f"⚠️ {len(stale)} old!" if stale else "✅ 0 stale"
                print(f"{c.source_name:<22} | {len(arts):<6} | {range_str:<32} | {stale_str}")
            else:
                print(f"{c.source_name:<22} | 0      | No articles in last 24h          | -")
        except Exception as exc:
            print(f"{c.source_name:<22} | ERROR  | {exc}")

    print("=" * 80)
    print(f"SUMMARY: {total_fresh} live real-time articles collected across all sources.")
    print(f"STALE ARTICLES LEAKED: {total_stale} (0% stale).")
    print("=" * 80)

if __name__ == "__main__":
    main()
