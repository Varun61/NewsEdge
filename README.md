# ⚡ NewsEdge — Institutional Indian Equity Market Intelligence

[![Python 3.11+](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.14-blue.svg)](https://www.python.org/)
[![NSE Equities](https://img.shields.io/badge/NSE%20Equities-2%2C362%20Active-green.svg)](https://www.nseindia.com/)
[![AI Provider](https://img.shields.io/badge/AI-Ollama%20(llama3.2)%20%7C%20OpenAI-purple.svg)](https://ollama.ai)
[![Telegram](https://img.shields.io/badge/Delivery-Telegram%20Bot-0088cc.svg)](https://telegram.org)
[![Groww Sync](https://img.shields.io/badge/Broker-Groww%20Sync-00d09c.svg)](https://groww.in)
[![Tests](https://img.shields.io/badge/Tests-25%20Passing-brightgreen.svg)](tests/)

**NewsEdge** is an automated, institutional-grade equity intelligence pipeline built specifically for Indian stock market (NSE/BSE) traders and research analysts.

It scans overnight and pre-market corporate announcements, regulatory filings, and news from **10 premier financial publishers**, maps them against the complete **2,362+ active NSE equity universe**, runs a **3-tier catalyst & materiality classification engine**, and delivers a minimalist, actionable watchlist directly to **Telegram** and **Groww** before market open at 08:00 AM IST.

---

## 🌟 Key Capabilities

- **10 Financial News Sources**: Live Google News corporate syndication, Economic Times, Mint, Moneycontrol, Business Standard, Financial Express, Hindu BusinessLine, CNBC-TV18, Zerodha Pulse, and Investing.com India.
- **Full NSE Universe (2,362+ Stocks)**: Complete coverage from official NSE `EQUITY_L.csv`, with company aliases, revenue baselines, and fuzzy ticker resolution.
- **3-Tier Intelligence Architecture**:
  1. **Thematic Sector Policy Engine**: Identifies macro/policy events (e.g. Railway capex, Gas allocation cuts, Anti-dumping duties, Insurance caps) and maps entire baskets of direct beneficiaries and casualties. Supports dynamic user-feedback learning.
  2. **Quantitative Catalyst Heuristics**: Micro-level extraction of order wins, quarterly earnings results, SEBI penalties, USFDA alerts, auditor resignations, debt covenants, and management changes.
  3. **Local Private LLM (Ollama `llama3.2`)**: Structured JSON output with calibrated confidence anchors, serialized inference locks, and timeout fallback.
- **Financial Materiality Scaling**: Evaluates order win magnitude relative to annual company revenue (e.g. ₹500 Cr order has 10× higher impact on a ₹5,000 Cr firm than a ₹50,000 Cr conglomerate).
- **Asymmetric Negativity Pricing**: Accounts for Indian market reality where negative catalysts (fraud, probe, loss, SEBI order) trigger immediate downside repricing faster than positive news.
- **Groww Watchlist Integration**: Automatically syncs top bullish/bearish candidates directly into your Groww trading app using headless automated TOTP login or session token.
- **Modern Minimalist Telegram Feed**: Tap-to-copy `<code>TICKER</code>` tags, concise single-line catalysts, and key macro sector developments with direct publisher links.
- **Zero-Hassle One-Click Launcher**: Auto-detects virtual environment, auto-starts Ollama daemon if inactive, verifies database schema, and runs pipeline.

---

## 🏗️ Architecture

```
                      [08:00 AM IST Batch Trigger]
                     (Local Cron / Task Scheduler / GitHub Actions)
                                   │
                                   ▼
                      [Trading Calendar Engine]
                      (Validates NSE Trading Day)
                                   │
                                   ▼
                     [Pre-Market Lookback Window]
            (Prev Trading Day 15:30 IST ──► Today 07:59 IST)
            (Includes Weekend for Mondays & Holiday Spans)
                                   │
                                   ▼
              [Multi-Source News Collectors (10 Sources)]
        (ET, Mint, Moneycontrol, BS, FE, CNBC, BL, Pulse, etc.)
                                   │
                                   ▼
             [Normalization & Entity Extraction (2,362 Stocks)]
             (Alias mapping, Title cleaning, Jaccard Deduplication)
                                   │
                                   ▼
              ┌──────────────────────────────────────────────┐
              │          3-TIER INTELLIGENCE LAYER           │
              ├──────────────────────────────────────────────┤
              │ Tier 1: Thematic Sector Policy Engine        │
              │ Tier 2: Quantitative Catalyst Heuristics     │
              │ Tier 3: Local Private LLM (Ollama llama3.2)  │
              └──────────────────────┬───────────────────────┘
                                     │
                                     ▼
                      [Financial Materiality Analyzer]
                 (Order Size vs Annual Revenue % Baseline)
                                     │
                                     ▼
                    [Multi-Factor Scoring Engine (0-100)]
                 (Impact, Credibility, Freshness, Confirmation,
                  Min-Confidence Filter, Negativity Multiplier)
                                     │
                                     ▼
                 ┌───────────────────┴───────────────────┐
                 ▼                                       ▼
        [Telegram Delivery]                    [Groww Watchlist Sync]
   (Minimalist Bullish/Bearish)             (Automated TOTP Headless Sync)
                 │                                       │
                 ▼                                       ▼
       [HTML & Excel Archives]             [Desktop Ready Watchlist]
```

---

## 📱 Telegram Delivery Preview

NewsEdge formats alerts with clean tap-to-copy tickers and zero clutter:

```text
🟢 BULLISH WATCHLIST • 02 Nov

1. TATASTEEL • Tata Steel Ltd
   Anti-dumping duty recommended on steel imports

2. BHEL • Bharat Heavy Electricals Ltd
   Secures ₹1,200 Cr EPC order from NTPC

3. SANOFI • Sanofi India Ltd
   Receives DCGI approval for new diabetes formulation


🔴 BEARISH WATCHLIST • 02 Nov

1. ADANIPORTS • Adani Ports & SEZ
   CBI registers preliminary inquiry into port concession

2. ASIANPAINT • Asian Paints Ltd
   Q2 net drops 38% YoY amid raw material price escalation


🌐 KEY SECTOR DEVELOPMENTS
• Railways: Ministry allocates ₹25,000 Cr for high-speed corridor contracts
  Source: The Economic Times (https://economictimes.indiatimes.com/...)
• City Gas: 20% cut in APM gas quota raises raw material costs for CGD players
  Source: Moneycontrol (https://www.moneycontrol.com/...)
```

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.11+** installed
- **[Ollama](https://ollama.ai)** (recommended for 100% free, private, local analysis) or OpenAI API key
- **Telegram Bot Token & Chat ID** (via [@BotFather](https://t.me/BotFather))

### 2. Clone & Setup
```bash
git clone https://github.com/Varun61/NewsEdge.git
cd NewsEdge

# Create virtual environment
python -m venv .venv

# Activate environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Configure your credentials in `.env`:
```ini
# AI Provider (ollama or openai)
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Telegram Alerts
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# Optional: Groww Automatic Watchlist Sync
GROWW_EMAIL=your_groww_email
GROWW_PASSWORD=your_groww_password
GROWW_TOTP_SECRET=your_groww_totp_secret_key
# Alternatively, use session token:
# GROWW_AUTH_TOKEN=your_jwt_bearer_token
```

### 4. Initialize Database & NSE Equities
Seed all 2,362+ verified NSE equity stocks, default sources, and aliases:
```bash
python -m scripts.initialize_database
```

---

## ⚡ Execution

### Option A: One-Click Launcher (Windows / Desktop)
Run directly via the included launcher:
```bat
run.bat
```
or in PowerShell:
```powershell
.\run.ps1
```
*Tip: A desktop shortcut can link directly to `run.bat` for 1-click morning execution.*

### Option B: Python Command Line
```bash
# Standard run for the current trading day window
python run_newsedge.py

# Custom lookback window (e.g. past 24 hours on weekends)
python run_newsedge.py --hours 24

# Headless / Cron mode
python run_newsedge.py --cron

# CLI execution via app module
python -m app.pipeline --hours 24
```

---

## ⏰ Automated Scheduling

### Linux / macOS (cron)
Run every weekday at 08:00 AM IST (02:30 UTC):
```cron
30 2 * * 1-5 cd /path/to/NewsEdge && .venv/bin/python run_newsedge.py --cron >> logs/cron.log 2>&1
```

### Windows (Task Scheduler)
Create a Scheduled Task triggering Monday–Friday at 08:00 AM:
- **Program/Script**: `C:\Users\<user>\NewsEdge\run.bat`
- **Start in**: `C:\Users\<user>\NewsEdge`

### GitHub Actions
A pre-configured GitHub Actions workflow is included at:
`.github/workflows/daily_market_watchlist.yml`

---

## 🧠 Thematic Learning Engine

NewsEdge can dynamically learn new sectoral and thematic correlation rules based on user feedback. When a macro or regulatory news item impacts specific stocks:

```python
from app.intelligence.thematic_engine import get_thematic_engine

engine = get_thematic_engine()
engine.learn_rule(
    theme_key="DEFENCE_DRONES",
    theme_title="Defence Drone Indigenisation Mandate",
    keywords=["defence drone", "uav order", "anti-drone system"],
    beneficiaries=[
        ("PARAS", "Paras Defence & Space Technologies", 90.0, "Leader in defence optics & drone sub-systems"),
        ("ZEN", "Zen Technologies Limited", 88.0, "Primary supplier of anti-drone training simulators"),
    ],
    casualties=[],
    macro_risk="Defence procurement contract award delays",
)
```
Rules are automatically saved to `data/custom_thematic_rules.json` and persist across pipeline runs.

---

## 🧪 Testing & Validation

NewsEdge comes with an extensive unit and integration test suite:

```bash
pytest tests/ -v
```

All 25 test modules pass cleanly covering:
- Trading calendar & lookback intervals
- Multi-source headline deduplication
- Entity extraction & NSE stock resolution
- Materiality calculation with directional context
- Scoring engine gates & classification thresholds
- Thematic catalyst matching & custom rule learning
- Telegram formatting & Groww export

---

## 📂 Project Structure

```
NewsEdge/
├── app/
│   ├── collectors/              # 10 news collectors (RSS, Syndication, Scrapers)
│   ├── database/                # SQLAlchemy models, SQLite repository, schema
│   ├── integrations/            # Groww automated TOTP login & watchlist sync
│   ├── intelligence/            # Thematic engine, Ollama/OpenAI, scoring, materiality
│   ├── market_data/             # Market data interfaces
│   ├── processors/              # NSE master resolver, entity extractor, deduplicator
│   ├── reporting/               # Minimalist Telegram formatter, HTML & Excel reports
│   ├── services/                # Analysis, collection, and reporting services
│   ├── pipeline.py              # Central pipeline orchestrator
│   └── trading_calendar.py      # NSE trading calendar & lookback calculations
├── assets/                      # Icons and design assets
├── data/
│   ├── EQUITY_L.csv             # Official NSE 2,600+ equities master file
│   └── custom_thematic_rules.json # Dynamic user-taught sector correlation rules
├── reports/                     # Generated HTML, Excel, and Groww watchlists
├── scripts/
│   ├── initialize_database.py   # Database seeder (sources, 2,362 stocks, aliases)
│   ├── audit_sources.py         # Source freshness & connectivity diagnostic tool
│   └── run_pipeline.py          # Script pipeline entry point
├── tests/                       # 25 automated pytest tests
├── run.bat                      # 1-click Windows launcher
├── run.ps1                      # 1-click PowerShell launcher
├── run_newsedge.py              # Operational auto-orchestrator
├── requirements.txt             # Python dependencies
└── .env.example                 # Configuration template
```

---

## ⚠️ Disclaimer

NewsEdge is designed as a **pre-market research and intelligence tool** for discretionary traders and investors. It generates **candidate watchlists**, not algorithmic trade execution signals or financial advice. Intraday price movements depend heavily on opening price action, broader market sentiment, liquidity, and risk management. Always conduct your own due diligence before placing trades.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
