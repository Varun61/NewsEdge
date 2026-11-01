# NewsEdge – Indian Intraday Stock Intelligence

NewsEdge is an automated stock market intelligence system designed for discretionary Indian equity intraday traders. It monitors major financial publishers and corporate disclosure channels, identifies market-moving catalysts (order wins, quarterly earnings, regulatory orders, corporate restructuring), evaluates financial materiality against baseline company revenue, and generates an actionable, ranked watchlist delivered straight to Telegram every trading morning before 8:00 AM IST.

---

## Architecture Overview: Single Daily Batch Job

NewsEdge runs as an efficient **single daily batch-processing job** executed at **8:00 AM IST**:

```
[Cron / Task Scheduler @ 08:00 AM IST]
                    │
                    ▼
     [Trading Calendar Validation]
      (Skips Weekends & NSE Holidays)
                    │
                    ▼
       [Determine Collection Window]
   (Prev Trading Day 15:30 -> Today 07:59 IST)
                    │
                    ▼
        [Step 1: Multi-Source News Collection]
  (Google News, Moneycontrol, ET Markets, Mint, etc.)
                    │
                    ▼
       [Step 2: Normalization & Deduplication]
    (Entity Resolution to NSE symbols & Grouping)
                    │
                    ▼
     [Step 3: AI Intelligence & Materiality]
  (Ollama / OpenAI classification + % revenue impact)
                    │
                    ▼
         [Step 4: Ranking & Scoring Engine]
     (Heuristic multi-factor score: 0 to 100)
                    │
                    ▼
      [Step 5: Telegram Delivery & Local Reports]
    (HTML / Excel reports archived in reports/)
```

---

## Key Features

## Collection Window Logic

1. **Standard Trading Days (Tue – Fri @ 8:00 AM IST)**:
   - Window: **Previous trading day 15:30 IST &rarr; Today 07:59 IST**.
   - Captures overnight disclosures and morning news before market open.

2. **Mondays (or Trading Days Following Holidays)**:
   - Window: **Previous trading day (Friday) 15:30 IST &rarr; Monday 07:59 IST**.
   - Automatically and completely spans **Friday evening, Saturday (all day), Sunday (all day)**, and Monday pre-market news!

3. **Ad-hoc / Manual Run "Now" (e.g. running on weekends or intraday)**:
   - If executed on a weekend (Saturday / Sunday) or non-trading holiday:
     - Automatically collects the **last 24 hours of news data** (from `now - 24 hours` up to `now`).
   - You can also explicitly specify any custom lookback window with `--hours`:
     ```bash
     python -m app.pipeline --hours 24
     python -m app.pipeline --hours 48
     ```

2. **Entity Resolution & NSE Stock Master**:
   - Built-in universe of top NSE stocks with financial baseline figures (revenue) and aliases (e.g. *RIL* / *Jio* &rarr; `RELIANCE`, *L&T* &rarr; `LT`, *State Bank of India* &rarr; `SBIN`).

3. **Multi-Source Deduplication**:
   - Groups multi-publisher coverage of the same event into a single `NewsEvent`, preventing duplicate stories from artificially inflating scores.

4. **Financial Materiality Analysis**:
   - Compares order sizes against baseline annual revenue (e.g., a ₹1,000 Cr order represents 10% of a ₹10,000 Cr revenue company, but only 1% of a ₹100,000 Cr company).

5. **Multi-Factor Scoring (0 to 100)**:
   - News Impact (25%), Financial Materiality (20%), Source Credibility (15%), Freshness (10%), Confirmations (10%), Historical Baseline (10%), Company Confidence (10%).

6. **Telegram Delivery**:
   - Categorizes candidates into **Bullish Candidates**, **Bearish Candidates**, and **Watch Only**, with reasons, sentiment, confidence, risks, and source links.

---

## Quick Start & Installation

### 1. Prerequisites
- Python 3.11 or 3.12
- Local [Ollama](https://ollama.ai) (optional, e.g. with `llama3.1`) or OpenAI API key
- Telegram Bot Token & Chat ID (from [@BotFather](https://t.me/BotFather))

### 2. Setup Virtual Environment
```bash
# Navigate to project folder
cd c:\Users\varun\NewsEdge

# Create virtual environment
python -m venv .venv

# Activate environment
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On macOS / Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Edit `.env` to configure your AI provider and Telegram credentials:
```ini
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1

# If using OpenAI instead:
# AI_PROVIDER=openai
# OPENAI_API_KEY=sk-...
# OPENAI_MODEL=gpt-4o-mini

TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

### 4. Initialize Database
Initialize the SQLite schema and seed the NSE stock universe and news sources:
```bash
python -m scripts.initialize_database
```

### 5. Run the Daily Pipeline Manually
```bash
# Run for today
python -m app.pipeline

# Or run for a specific historical date:
python -m app.pipeline --date 2026-11-02
```

---

## Scheduling the Daily 8:00 AM IST Batch Job

### On Linux / macOS (cron)
Because 8:00 AM IST is **02:30 AM UTC**:
```cron
# Run Monday through Friday at 08:00 AM IST (02:30 UTC)
30 2 * * 1-5 cd /path/to/NewsEdge && .venv/bin/python -m app.pipeline >> logs/cron.log 2>&1
```

### On Windows (Task Scheduler)
Create a Scheduled Task to run every weekday at 08:00 AM:
- **Program/script**: `C:\Users\varun\NewsEdge\.venv\Scripts\python.exe`
- **Add arguments**: `-m app.pipeline`
- **Start in**: `C:\Users\varun\NewsEdge`

---

## Running the Automated Test Suite

NewsEdge includes a comprehensive test suite with mock data:
```bash
pytest
```

---

## Telegram Bot Commands (Optional Interactive Mode)
You can optionally run the interactive bot for on-demand queries:
```bash
python -c "from app.reporting.telegram_bot import TelegramBot; import asyncio; bot = TelegramBot(); bot.build_application().run_polling()"
```
Available commands:
- `/today` – Get today's full watchlist
- `/bullish` – Top bullish candidates
- `/bearish` – Top bearish candidates
- `/stock SYMBOL` – Specific stock profile (e.g. `/stock RELIANCE`)
- `/status` – System health and active sources
- `/help` – Command assistance

---

## Disclaimer
NewsEdge generates **research candidates**, not guaranteed trade signals or investment advice. Discretionary intraday traders should always evaluate market opening behavior, price action, VWAP, liquidity, and risk management before entering any positions.
