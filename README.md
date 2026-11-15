# ⚡ NewsEdge — Institutional Indian Equity Market Intelligence

[![Python 3.11+](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.14-blue.svg)](https://www.python.org/)
[![NSE Equities](https://img.shields.io/badge/NSE%20Equities-2%2C362%20Active-green.svg)](https://www.nseindia.com/)
[![Sources](https://img.shields.io/badge/Sources-17%20Active%20Collectors-orange.svg)](#-key-capabilities)
[![AI Provider](https://img.shields.io/badge/AI-Ollama%20(llama3.2)%20%7C%20OpenAI-purple.svg)](https://ollama.ai)
[![Telegram](https://img.shields.io/badge/Delivery-Telegram%204--Category-0088cc.svg)](https://telegram.org)
[![Broker](https://img.shields.io/badge/Broker-Groww%20Sync-00d09c.svg)](https://groww.in)
[![Tests](https://img.shields.io/badge/Tests-44%20Passing-brightgreen.svg)](tests/)

**NewsEdge** is an automated, institutional-grade equity intelligence pipeline built specifically for Indian stock market (NSE/BSE) traders and research analysts.

It scans overnight, post-market, and pre-market corporate announcements, regulatory filings, earnings disclosures, and brokerage research from **17 premier financial sources and official exchange APIs**, maps them against the complete **2,362+ active NSE equity universe**, runs **institutional conviction & technical trend gates**, and delivers a minimalist, actionable 4-category watchlist directly to **Telegram** and **Groww**.

---

## 🌟 Key Capabilities

### 1. 17 Multi-Source Financial Collectors
- **Financial Wires & Portals (10)**: Google News corporate syndication, Economic Times, Mint, Moneycontrol, Business Standard, Financial Express, Hindu BusinessLine, CNBC-TV18, Zerodha Pulse, and Investing.com India.
- **High-Precision Earnings & Concall Engines (6)**:
  - **Tijori Finance**: Granular operating profit, revenue YoY/QoQ in ₹ Crores, and segment margins.
  - **MarketByte**: Real-time earnings beats/misses and morning pre-market briefs.
  - **Moneycontrol Results**: Quarterly results tables with YoY profit and gross margin growth.
  - **The Core Earnings**: Corporate earnings disclosure tracking and executive highlights.
  - **Screener.in**: Official **Earnings Concall Transcripts**, **Investor Presentations (PPT)**, and Regulation 30 filings.
  - **NSE Announcements**: Direct official corporate disclosures from the National Stock Exchange (NSE) with PDF attachments.
- **Institutional Brokerage Radar (1)**:
  - **Brokerage Radar**: Real-time morning upgrades, downgrades, and target price revisions from top domestic & global brokerages (Jefferies, CLSA, Morgan Stanley, Goldman Sachs, Nomura, Motilal Oswal, Kotak Institutional Equities).

### 2. 5 Institutional Alpha Layers
1. **Technical Trend Alignment (20/50 EMA Filter)**: Eliminates "Sell-on-Rise" counter-trend traps. When a stock is in a confirmed structural downtrend (Price < 20 EMA and < 50 EMA), positive news is penalized (-14.0) and gated out of top watchlists, while breakouts in confirmed uptrends (Price > 20 EMA > 50 EMA) receive conviction boosts (+8.0).
2. **Pre-Market Gap & Microstructure Gate**: Protects against gap-up exhaustion by classifying opening auction prices into:
   - `SWEET_SPOT` (+0.5% to +2.5%): Ideal runway for sustained intraday trend continuation.
   - `EXHAUSTION_RISK` (> +4.0%): Smart money dumping into retail liquidity; warns traders not to chase.
   - `DISCONNECT_TRAP`: Stock gapping down on ostensibly bullish news, flagging institutional distribution.
3. **Earnings Quality Gate**:
   - **Revenue-Profit Divergence**: Flags when profit jumps >25% while revenue is <15% (indicates one-off or accounting gain).
   - **Exceptional Items Filter**: Identifies one-time income, tax write-backs, and asset sales flattering the headline.
   - **Bellwether Modest Growth**: Flags <15% profit growth in institutional bellwethers (HDFC Bank, Infosys, Colgate, TCS) as growth deceleration.
   - **Concall Guidance & Caution Scanner**: Detects management guidance revisions (raised vs cut), margin pressure, and demand headwinds.
4. **Sector Momentum Context Layer**: Tracks Nifty 50, Bank Nifty, Nifty IT, Auto, Pharma, FMCG, and Metals to provide a -12 to +5 point conviction modifier based on whether the stock has a sector tailwind or headwind.
5. **F&O Derivatives Strike Barriers**: Maps all 185 NSE F&O equities. Identifies immediate round-strike Call open interest resistance walls and Put support floors.

### 3. 4-Category Actionable Telegram Watchlist
- 🟢 **BULLISH WATCHLIST**: Fresh post-market positive catalysts (disclosed after 3:30 PM IST) actionable for next day's open.
- 🔴 **BEARISH WATCHLIST**: Fresh post-market negative catalysts (disclosed after 3:30 PM IST) with downside velocity.
- 📊 **PRICED-IN BULLISH**: News/moves that already occurred during market hours (9:15 AM – 3:30 PM IST) — flagged for momentum only, preventing gap-up traps.
- 📊 **PRICED-IN BEARISH**: News/dumps that already unfolded during cash market hours.

### 4. Institutional Conviction Tiers
Every stock card in Telegram is badged with an institutional conviction indicator:
- `🎯` **Strong Conviction** (Score $\ge 85$): Multi-source confirmed, quantified catalyst, technical trend alignment.
- `⚡` **Moderate Conviction** (Score $70–84$): High-quality setup with verified financials.
- `👀` **Tracking / Speculative** (Score $64–69$): Borderline candidate for radar tracking only.

### 5. Smart Weekend & Trading Calendar Windows
- **Sunday or Monday Morning**: Automatically expands lookback to capture everything from **Friday 3:30 PM IST to current run time**, ensuring no weekend earnings announcements or corporate actions are missed.
- **Monday Post-Market (after 3:30 PM IST)**: Automatically switches back to the standard weekday 24-hour post-market lookback.
- **Direct Clickable Source Links (`LINK`)**: Every stock card includes a direct `<a href="...">LINK</a>` to the original news article, exchange filing PDF, concall transcript, or Tijori analysis.

---

## 🏗️ Architecture

```
                      [Pipeline Trigger: Evening / Pre-Market]
                      (Local Cron / Task Scheduler / Desktop Shortcut)
                                     │
                                     ▼
                      [Trading Calendar Engine]
                      (Validates NSE Trading Day & Weekend Windows)
                      (Sunday/Mon pre-market: Friday 15:30 ──► Now)
                      (Mon post-market & Tue-Fri: 15:30 ──► Now)
                                     │
                                     ▼
              [Multi-Source News Collectors (17 Sources)]
     ┌──────────────────────────────┬──────────────────────────────┐
     │  Financial Media (10)        │  Earnings & Research (7)     │
     │  - Google News corporate RSS │  - Tijori Finance Results    │
     │  - Economic Times Markets    │  - MarketByte Earnings Beats │
     │  - Mint & Moneycontrol       │  - Moneycontrol Tables       │
     │  - Business Standard & FE    │  - The Core Earnings         │
     │  - CNBC-TV18 & Pulse         │  - Screener.in Concalls/PPTs │
     │  - Hindu BusinessLine        │  - NSE Corporate API         │
     │  - Investing.com India       │  - Brokerage Radar (Calls)   │
     └──────────────────────────────┴──────────────────────────────┘
                                    │
                                    ▼
              [Normalization & Entity Extraction (2,362 Stocks)]
              (Disambiguation: RIL/ADAG, ICICI Sec, TAKE, TRIDENT)
              (Roundup Headline Blocker, Jaccard Deduplication)
                                    │
                                    ▼
               ┌──────────────────────────────────────────────┐
               │          MULTI-TIER INTELLIGENCE LAYER       │
               ├──────────────────────────────────────────────┤
               │ • Thematic Policy & Sector Catalyst Engine   │
               │ • Quantitative Catalyst & Materiality Engine │
               │ • Technical Trend Analyzer (20/50 EMA)       │
               │ • Earnings Quality Gate (Deceleration/One-off│
               │ • Concall Guidance & Margin Trajectory       │
               │ • Sector Momentum Context (7 Sector Indices) │
               │ • Local Private LLM (Ollama llama3.2)        │
               └──────────────────────┬───────────────────────┘
                                      │
                                      ▼
                     [Multi-Factor Scoring Engine (0-100)]
                  (Impact, Credibility, Freshness, Trend Alignment,
                   Concall Guidance, Retrospective Rally Filter)
                                      │
                                      ▼
             ┌────────────────────────┴────────────────────────┐
             ▼                                                 ▼
    [4-Category Telegram Feed]                      [Groww Watchlist Sync]
    🟢 Fresh Bullish (🎯/⚡/👀 Conviction)          (Automated TOTP Headless Sync)
    🔴 Fresh Bearish (🎯/⚡/👀 Conviction)                         │
    📊 Priced-In Bullish (Momentum Only)                       ▼
    📊 Priced-In Bearish (Momentum Only)            [Desktop Ready Watchlist]
    🔗 Direct Source LINK on every card
    ⚡ Execution & F&O Resistance Tips
```

---

## 📱 Telegram Delivery Preview

NewsEdge formats alerts into 4 distinct trading categories with conviction badges and direct source links:

```text
🟢 BULLISH WATCHLIST • 15 Nov
Fresh post-market catalysts for next trading day

1. 🎯 LT • Larsen & Toubro Limited
   L&T bags mega ₹4,000 crore hydrocarbon order in Middle East • LINK

2. ⚡ ASHOKLEY • Ashok Leyland Limited
   Operating profit jumps 16.4% YoY to ₹2,805 Cr, sales rises 35.4% • LINK

🎯 = Strong Conviction  ⚡ = Moderate  👀 = Tracking

⚡ Execution Tip: If a stock gaps up > 3% at open, avoid chasing market orders. Allow 15-min consolidation.


🔴 BEARISH WATCHLIST • 15 Nov
Fresh post-market catalysts for next trading day

1. 🎯 INVENTURE • Inventure Growth & Securities
   Inventure Growth gets SEBI penalty for disclosure violations • LINK

2. ⚡ PATANJALI • Patanjali Foods Limited
   Operating profit drops 22.9% YoY to ₹425 Cr amid margin compression • LINK


📊 PRICED-IN BULLISH • 15 Nov
Market already reacted — consider momentum only

1. ⚡ CUPID • Cupid Limited
   Cupid Q2 profit doubles; raises FY27 revenue guidance • LINK


📊 PRICED-IN BEARISH • 15 Nov
Market already reacted — consider momentum only

1. ⚡ ALKEM • Alkem Laboratories Limited
   Alkem Lab Q2 profit falls 14.4% to ₹667 Cr; revenue rises to ₹4,552 Cr • LINK


🌐 KEY SECTOR DEVELOPMENTS
• Railways: Ministry allocates ₹25,000 Cr for high-speed corridor contracts
  🔗 Read on Economic Times
```

---

## 📊 Empirical Backtest Performance

NewsEdge includes a rolling historical backtester (`scripts/backtest_one_month.py`) evaluated across the entire 2,362 NSE equity universe with cached daily OHLCV price bars:

| Metric | Benchmark | Result | Takeaway |
|:---|:---:|:---:|:---|
| **Overall Directional Win Rate** | > 55.0% | **59.7%** (117 / 196) | Consistent statistical edge |
| **Bullish Hit Rate** | > 55.0% | **61.0%** (50 / 82) | Strong institutional follow-through |
| **Order Win Hit Rate** | > 65.0% | **75.0%** (6 / 8) | Highest alpha catalyst archetype |
| **Strong Movers ($\ge 3\%$ move)** | 2:1 ratio | **49 Wins vs 27 Losses** | **1.81:1 Win-to-Loss Ratio** |
| **Average Favorable Move** | > +2.00% | **+3.32%** | High reward capture on winners |
| **Average Adverse Move** | < -3.00% | **-2.91%** | Well-contained risk on misses |
| **Profit Factor / Asymmetry Ratio** | > 1.50x | **1.69x** | Highly profitable risk-reward profile |

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

### Option A: One-Click Desktop Shortcut (Windows)
Double-click the **NewsEdge** desktop shortcut or execute:
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

# Run rolling historical backtester
python scripts/backtest_one_month.py --weeks 3
```

---

## 🧪 Testing & Validation

NewsEdge comes with an extensive automated test suite covering all collectors, intelligence layers, and reporting pipelines:

```bash
pytest tests/ -v
```

**All 44 tests pass cleanly**, verifying:
- Technical trend 20/50 EMA calculations & counter-trend penalty gates
- Pre-market opening gap classifications (`SWEET_SPOT`, `EXHAUSTION_RISK`, `DISCONNECT_TRAP`)
- Concall guidance extraction & margin trajectory detection
- NSE F&O derivatives strike barriers and option wall intelligence
- Sector momentum context modifiers across 7 benchmark indices
- Earnings quality gates (growth deceleration, exceptional items, revenue-profit divergence)
- Sunday & Monday weekend lookback windows (Friday 3:30 PM IST start)
- Retrospective rally detection & past price action filters
- Entity disambiguation (RIL/ADAG, ICICI Sec, TAKE, TRIDENT, Kotak Alts)
- 4-category Telegram message generation with conviction badges and clickable links
- Multi-source headline deduplication & scoring engine classification thresholds

---

## 📂 Project Structure

```
NewsEdge/
├── app/
│   ├── collectors/              # 17 multi-source news, earnings & brokerage collectors
│   │   ├── news_collectors/     # RSS, Tijori, MarketByte, MC, Core, Screener, Brokerage Radar
│   │   └── official_collectors/ # Official NSE Announcements API
│   ├── database/                # SQLAlchemy models, SQLite repository, schema
│   ├── integrations/            # Groww automated TOTP login & watchlist sync
│   ├── intelligence/            # 5 Alpha Layers: Trend, Gap, Concall, Derivatives, Scoring
│   │   ├── technical_trend.py   # 20/50 EMA structural trend analyzer
│   │   ├── gap_analyzer.py      # Pre-market opening gap & exhaustion evaluator
│   │   ├── concall_analyzer.py  # Concall transcript & guidance extractor
│   │   ├── derivatives_context.py # F&O round-strike Call/Put barrier intelligence
│   │   ├── sector_momentum.py   # 7 sectoral index momentum context analyzer
│   │   ├── scoring_engine.py    # Multi-factor score & earnings quality gates
│   │   ├── thematic_engine.py   # Sector policy catalyst basket engine
│   │   └── ai_provider.py       # Ollama & heuristic classification engine
│   ├── market_data/             # Market data interfaces
│   ├── processors/              # NSE master resolver, entity extractor, deduplicator
│   ├── reporting/               # 4-Category Telegram formatter with conviction badges
│   ├── services/                # Analysis, collection, and reporting services
│   ├── pipeline.py              # Central pipeline orchestrator
│   └── trading_calendar.py      # NSE trading calendar & weekend lookback calculations
├── data/
│   ├── EQUITY_L.csv             # Official NSE 2,362+ equities master file
│   └── custom_thematic_rules.json # Dynamic user-taught sector correlation rules
├── reports/                     # Generated markdown, JSON, HTML, and Groww watchlists
├── scripts/
│   ├── backtest_one_month.py    # Rolling historical backtest engine with cached prices
│   ├── initialize_database.py   # Database seeder (sources, 2,362 stocks, aliases)
│   └── audit_sources.py         # Source freshness & connectivity diagnostic tool
├── tests/                       # 44 automated pytest tests
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
