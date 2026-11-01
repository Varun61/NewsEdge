"""Unit tests for Groww watchlist synchronization and file export."""

import tempfile
from pathlib import Path
from app.integrations.groww_sync import GrowwWatchlistSync


def test_groww_offline_export():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        sync = GrowwWatchlistSync(auth_token=None)

        bullish = [
            {"symbol": "MUTHOOTFIN", "company_name": "Muthoot Finance Limited", "score": "84", "headline": "Profit jumps 27%"},
            {"symbol": "TITAGARH", "company_name": "Titagarh Rail Systems Limited", "score": "86", "headline": "Bags wagon order"},
        ]
        bearish = [
            {"symbol": "POLICYBZR", "company_name": "PB Fintech Limited", "score": "88", "headline": "IRDAI cuts commission"},
            {"symbol": "IGL", "company_name": "Indraprastha Gas Limited", "score": "86", "headline": "APM gas allocation cut"},
        ]

        res = sync.process_sync(bullish, bearish, out_dir)
        assert len(res.export_files) == 3

        bull_file = out_dir / "groww_bullish_watchlist.txt"
        assert bull_file.exists()
        content = bull_file.read_text(encoding="utf-8")
        assert "MUTHOOTFIN, TITAGARH" in content

        bear_file = out_dir / "groww_bearish_watchlist.txt"
        assert bear_file.exists()
        content = bear_file.read_text(encoding="utf-8")
        assert "POLICYBZR, IGL" in content

        csv_file = out_dir / "groww_watchlist_import.csv"
        assert csv_file.exists()
        content = csv_file.read_text(encoding="utf-8")
        assert "MUTHOOTFIN" in content
        assert "POLICYBZR" in content
