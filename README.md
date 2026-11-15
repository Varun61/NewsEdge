# ⚡ NewsEdge — Institutional Indian Equity Market Intelligence

[![Python 3.11+](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.14-blue.svg)](https://www.python.org/)
[![NSE Equities](https://img.shields.io/badge/NSE%20Equities-2%2C362%20Active-green.svg)](https://www.nseindia.com/)
[![Sources](https://img.shields.io/badge/Sources-16%20Active%20Collectors-orange.svg)](#-key-capabilities)
[![AI Provider](https://img.shields.io/badge/AI-Ollama%20(llama3.2)%20%7C%20OpenAI-purple.svg)](https://ollama.ai)
[![Telegram](https://img.shields.io/badge/Delivery-Telegram%204--Category-0088cc.svg)](https://telegram.org)
[![Groww Sync](https://img.shields.io/badge/Broker-Groww%20Sync-00d09c.svg)](https://groww.in)
[![Tests](https://img.shields.io/badge/Tests-33%20Passing-brightgreen.svg)](tests/)

**NewsEdge** is an automated, institutional-grade equity intelligence pipeline built specifically for Indian stock market (NSE/BSE) traders and research analysts.

It scans overnight, post-market, and pre-market corporate announcements, regulatory filings, and earnings results from **16 premier financial sources and official exchange APIs**, maps them against the complete **2,362+ active NSE equity universe**, runs a **calibrated catalyst & materiality classification engine**, and delivers a minimalist, actionable 4-category watchlist directly to **Telegram** and **Groww**.

---

## 🌟 Key Capabilities

- **16 Multi-Source Financial Collectors**:
  - **Financial Wires & Portals**: Google News corporate syndication, Economic Times, Mint, Moneycontrol, Business Standard, Financial Express, Hindu BusinessLine, CNBC-TV18, Zerodha Pulse, and Investing.com India.
  - **High-Precision Earnings & Concall Engines**:
    - **Tijori Finance**: Granular operating profit, revenue YoY/QoQ in ₹ Crores, and segment performance.
    - **MarketByte**: Real-time earnings beats/misses and morning pre-market briefs.
    - **Moneycontrol Results**: Latest quarterly results tables with YoY profit and gross margin growth.
    - **The Core Earnings**: Corporate earnings disclosure tracking and executive highlights.
    - **Screener.in**: Official **Earnings Concall Transcripts**, **Investor Presentations (PPT)**, and Regulation 30 disclosures.
    - **NSE Announcements**: Direct official filings from National Stock Exchange (NSE) corporate disclosures with PDF attachments.
- **4-Category Actionable Telegram Watchlist**:
  - 🟢 **BULLISH WATCHLIST**: Fresh post-market positive catalysts (disclosed after 3:30 PM IST) actionable for next day's open.
  - 🔴 **BEARISH WATCHLIST**: Fresh post-market negative catalysts (disclosed after 3:30 PM IST) with immediate downside velocity.
  - 📊 **PRICED-IN BULLISH**: News/moves that already occurred during market hours (9:15 AM – 3:30 PM IST) — flagged for momentum only, preventing gap-up traps.
  - 📊 **PRICED-IN BEARISH**: News/dumps that already unfolded during market hours.
- **Direct Clickable Source Links (`LINK`)**: Every stock card includes a direct `<a href="...">LINK</a>` to the original news source, exchange filing PDF, concall transcript, or Tijori analysis.
- **Retrospective Rally Filter**: Eliminates laggard news where the media explains why a stock already surged (e.g. *"shares jump 8%"*, *"stock up 6% today"*, *"hits record high"*, *"up 118% from low"*), preventing chasing exhausted gap-up opens.
- **Entity Disambiguation Guards**:
  - Prevents Anil Ambani ADAG legal issues from wrongly mapping to Mukesh Ambani's `RELIANCE` (RIL).
  - Prevents ICICI Securities / ICICI Direct broker research notes from mapping to `ICICIBANK`.
  - Prevents PE/VC investments by Kotak Alts from mapping to `KOTAKBANK` equity.
  - Prevents "take over" phrases from matching `TAKE` Solutions.
  - Prevents Trident Hotel (EIH) news from matching `TRIDENT` textiles.
  - Blocks generic listicle and roundup headlines (*"Buzzing stocks"*, *"Top 10 stocks to buy"*).
- **Post-Market Collection Window**:
  - Default evening/night runs collect from **Today's 3:30 PM IST to current run time** to isolate fresh post-market catalysts.
  - Morning runs collect from previous trading day's 3:30 PM IST to run time.
- **Full NSE Universe (2,362+ Stocks)**: Complete coverage from official NSE `EQUITY_L.csv`, with company aliases, revenue baselines, and fuzzy ticker resolution.
- **3-Tier Intelligence Architecture**:
  1. **Thematic Sector Policy Engine**: Identifies macro/policy events (e.g. Railway capex, Gas allocation cuts, Anti-dumping duties, Insurance caps) and maps baskets of beneficiaries and casualties.
  2. **Quantitative Catalyst Heuristics**: Micro-level extraction of order wins, quarterly earnings beats/misses, SEBI penalties, USFDA alerts, auditor resignations, and debt covenants.
  3. **Local Private LLM (Ollama `llama3.2`)**: Structured JSON output with calibrated confidence anchors and serialized inference locks.
- **Financial Materiality Scaling**: Evaluates order win magnitude relative to annual company revenue (e.g. ₹500 Cr order has 10× higher impact on a ₹5,000 Cr firm than a ₹50,000 Cr conglomerate).
- **Asymmetric Negativity Pricing**: Accounts for Indian market reality where negative catalysts (fraud, probe, loss, SEBI order) trigger immediate downside repricing faster than positive news.
- **Groww Watchlist Integration**: Automatically syncs top bullish/bearish candidates directly into your Groww trading app using headless automated TOTP login or session token.

---

## 🏗️ Architecture

```
                      [Pipeline Trigger: Evening / Pre-Market]
                      (Local Cron / Task Scheduler / Manual Run)
                                    │
                                    ▼
                      [Trading Calendar Engine]
                      (Validates NSE Trading Day)
                                    │
                                    ▼
                      [Post-Market Collection Window]
              (Today 15:30 IST ──► Current Run Time IST)
              (Or Prev Trading Day 15:30 ──► 07:59 for Morning)
                                    │
                                    ▼
              [Multi-Source News Collectors (16 Sources)]
     ┌──────────────────────────────┬──────────────────────────────┐
     │  Financial Media (10)        │  Earnings & Filings (6)      │
     │  - Google News corporate RSS │  - Tijori Finance Results    │
     │  - Economic Times Markets    │  - MarketByte Earnings Beats │
     │  - Mint & Moneycontrol       │  - Moneycontrol Tables       │
     │  - Business Standard & FE    │  - The Core Earnings         │
     │  - CNBC-TV18 & Pulse         │  - Screener.in Concalls/PPTs │
     │  - Hindu BusinessLine        │  - NSE Corporate API         │
     └──────────────────────────────┴──────────────────────────────┘
                                    │
                                    ▼
              [Normalization & Entity Extraction (2,362 Stocks)]
              (Disambiguation Guards: ADAG/RIL, ICICI Sec, TAKE, TRIDENT)
              (Roundup Headline Blocker, Jaccard Deduplication)
                                    │
                                    ▼
               ┌──────────────────────────────────────────────┐
               │          3-TIER INTELLIGENCE LAYER           │
               ├──────────────────────────────────────────────┤
               │ Tier 1: Thematic Sector Policy Engine        │
               │ Tier 2: Quantitative Catalyst Heuristics     │
               │         - Retrospective Rally Filter         │
               │         - Profit Decline Guard               │
               │         - Margin Compression Detector        │
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
                   Capex/Buyback Filter, Tiny Profit Penalty)
                                      │
                                      ▼
             ┌────────────────────────┴────────────────────────┐
             ▼                                                 ▼
    [4-Category Telegram Feed]                      [Groww Watchlist Sync]
    🟢 Fresh Bullish (Post-Market)              (Automated TOTP Headless Sync)
    🔴 Fresh Bearish (Post-Market)                             │
    📊 Priced-In Bullish (Market Hours)                        ▼
    📊 Priced-In Bearish (Market Hours)             [Desktop Ready Watchlist]
    🔗 Direct Source LINK on every card
```

---

## 📱 Telegram Delivery Preview

NewsEdge formats alerts into 4 distinct trading categories with direct source links:

```text
🟢 BULLISH WATCHLIST • 15 Nov
Fresh post-market catalysts for next trading day

1. LT • Larsen & Toubro Limited
   L&T bags mega ₹4,000 crore hydrocarbon order in Middle East • LINK

2. ASHOKLEY • Ashok Leyland Limited
   Operating profit jumps 16.4% YoY to ₹2,805 Cr, sales rises 35.4% • LINK


🔴 BEARISH WATCHLIST • 15 Nov
Fresh post-market catalysts for next trading day

1. INVENTURE • Inventure Growth & Securities
   Inventure Growth gets SEBI penalty for disclosure violations • LINK

2. PATANJALI • Patanjali Foods Limited
   Operating profit drops 22.9% YoY to ₹425 Cr amid margin compression • LINK


📊 PRICED-IN BULLISH • 15 Nov
Market already reacted — consider momentum only

1. CUPID • Cupid Limited
   Cupid Q2 profit doubles; raises FY27 revenue guidance • LINK


📊 PRICED-IN BEARISH • 15 Nov
Market already reacted — consider momentum only

1. ALKEM • Alkem Laboratories Limited
   Alkem Lab Q2 profit falls 14.4% to ₹667 Cr; revenue rises to ₹4,552 Cr • LINK


🌐 KEY SECTOR DEVELOPMENTS
• Railways: Ministry allocates ₹25,000 Cr for high-speed corridor contracts
  🔗 Read on Economic Times
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

### Option B: Python Command Line
```bash
# Standard evening/post-market run (collects from 3:30 PM to now)
python run_newsedge.py

# Custom lookback window (e.g. past 24 hours on weekends)
python run_newsedge.py --hours 24

# Headless / Scheduled Cron mode
python run_newsedge.py --cron

# CLI execution via app module
python -m app.pipeline
```

---

## 🧪 Testing & Validation

NewsEdge comes with an extensive automated test suite covering all collectors, classification filters, and Telegram outputs:

```bash
pytest tests/ -v
```

All 33 test modules pass cleanly covering:
- Trading calendar & post-market collection windows
- Retrospective rally detection & past price action filters
- Bearish profit decline detection & margin compression rules
- Entity disambiguation (RIL/ADAG, ICICI Sec, TAKE, TRIDENT, Kotak Alts)
- 4-category Telegram message generation with clickable links
- Multi-source headline deduplication
- Scoring engine gates & classification thresholds
- Thematic catalyst matching & custom rule learning

---

## 📂 Project Structure

```
NewsEdge/
├── app/
│   ├── collectors/              # 16 multi-source news & earnings collectors
│   │   ├── news_collectors/     # RSS, Tijori, MarketByte, MC, Core, Screener
│   │   └── official_collectors/ # Official NSE Announcements API
│   ├── database/                # SQLAlchemy models, SQLite repository, schema
│   ├── integrations/            # Groww automated TOTP login & watchlist sync
│   ├── intelligence/            # Thematic engine, Ollama/OpenAI, scoring, materiality
│   ├── market_data/             # Market data interfaces
│   ├── processors/              # NSE master resolver, entity extractor, deduplicator
│   ├── reporting/               # 4-Category Telegram formatter, HTML & Excel reports
│   ├── services/                # Analysis, collection, and reporting services
│   ├── pipeline.py              # Central pipeline orchestrator
│   └── trading_calendar.py      # NSE trading calendar & lookback calculations
├── data/
│   ├── EQUITY_L.csv             # Official NSE 2,362+ equities master file
│   └── custom_thematic_rules.json # Dynamic user-taught sector correlation rules
├── reports/                     # Generated HTML, Excel, and Groww watchlists
├── scripts/
│   ├── backtest_one_month.py    # Rolling historical backtest engine with cached prices
│   ├── initialize_database.py   # Database seeder (sources, 2,362 stocks, aliases)
│   └── audit_sources.py         # Source freshness & connectivity diagnostic tool
├── tests/                       # 33 automated pytest tests
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
