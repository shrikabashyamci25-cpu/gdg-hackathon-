# NebulaScan

> **Crypto Fraud Detection & Safety Platform** — Paste any crypto URL, get an instant trust score, risk breakdown, and safe alternatives powered by real-time analysis.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-aiosqlite-003B57?style=flat&logo=sqlite&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/Tailwind-CDN-38B2AC?style=flat&logo=tailwind-css&logoColor=white)
![Gemini](https://img.shields.io/badge/Google-Gemini%202.0-4285F4?style=flat&logo=google&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Render](https://img.shields.io/badge/Deployed%20on-Render-46E3B7?style=flat&logo=render&logoColor=white)

---

## Table of Contents

1. [Project Title & Description](#nebulascan)
2. [Badges](#)
3. [Table of Contents](#table-of-contents)
4. [Core Features](#core-features)
5. [Tech Stack](#tech-stack)
6. [Installation Instructions](#installation-instructions)
7. [Configuration](#configuration)
8. [Usage Examples](#usage-examples)
9. [Dependencies](#dependencies)
10. [How to Contribute](#how-to-contribute)
11. [License](#license)
12. [Acknowledgements / Contact](#acknowledgements--contact)

---

## Core Features

- **Real-Time URL Analysis** — Paste any crypto-related link to instantly verify its legitimacy using SSL checks, WHOIS domain age lookup, Google Safe Browsing, and keyword pattern detection.

- **Trust Score Engine** — Every URL is assigned a score from 0–100 with one of three verdicts: `SAFE TO INVEST`, `SUSPICIOUS`, or `FRAUDULENT`, along with a detailed list of risk flags explaining why.

- **Smart Redirection** — If a site is flagged as medium or high risk, NebulaScan automatically surfaces 2–3 reputable, regulated alternative platforms (Coinbase, Kraken, Binance, Gemini, Uniswap) with step-by-step onboarding guides.

- **Investment Advice Engine** — Context-aware guidance based on the trust score: from "DO NOT INVEST" to portfolio position-sizing recommendations capped at 5–10% for safe platforms.

- **Risk Calculator** — Built-in calculator that takes your portfolio value, risk tolerance percentage, and a site's trust score to produce an adjusted maximum position size.

- **Scan History & Stats** — All scans are persisted to a local SQLite database. A dashboard displays total scans, safe/medium/high-risk counts, and a full paginated scan history.

- **Trusted Platforms Directory** — A curated, database-backed list of regulated and decentralised exchanges with safety explanations and getting-started guides.

- **NebulaAI Chatbot** — An in-app AI advisor powered by Google Gemini 2.0 Flash. Ask anything about crypto safety, scam patterns, or how to interpret a trust score.

- **Live Bitcoin Trend Analysis** — Fetches 30-day price data from CoinGecko and calculates SMA-7, SMA-14, SMA-30, and RSI-14 to produce a BULLISH / NEUTRAL / BEARISH market signal.

- **Zero Trust Security Architecture** — Rate limiting (20 req/min via SlowAPI), Pydantic v2 input validation, parameterised SQLAlchemy ORM queries, no client-side secrets, and anonymous scan history with no user identity stored.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.11 · FastAPI 0.115 · Uvicorn |
| **Database** | SQLite via SQLAlchemy 2.0 async + aiosqlite |
| **Frontend** | Plain HTML5 · Tailwind CSS (CDN) · Space Grotesk / Inter fonts |
| **AI Chatbot** | Google Gemini 2.0 Flash API |
| **External APIs** | Google Safe Browsing v4 · python-whois · CoinGecko API |
| **Security** | SlowAPI rate limiting · Pydantic v2 validation · FastAPI CORSMiddleware |
| **Deployment** | Render (single web service — backend serves all HTML pages) |

> **Note:** There is no separate frontend build step. The FastAPI backend serves all HTML pages directly via route handlers, keeping the project as a single deployable service.

---

## Installation Instructions

Follow these steps to run NebulaScan on your local machine.

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/nebulascan.git
cd nebulascan
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Add your environment variables

Create a `.env` file in the project root (same folder as `main.py`):

```env
GEMINI_API_KEY=your_gemini_api_key_here
GOOGLE_SAFE_BROWSING_KEY=your_google_safe_browsing_key_here
```

### 5. Start the server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The app will be available at **http://localhost:8000**. The SQLite database (`nebula.db`) and all tables are created automatically on first startup.

---

## Configuration

All configuration is handled via environment variables loaded from a `.env` file using `pydantic-settings`. No manual database setup is required — SQLAlchemy creates the schema on startup.

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | ✅ Yes | Google Gemini API key for the NebulaAI chatbot |
| `GOOGLE_SAFE_BROWSING_KEY` | ⚠️ Optional | Google Safe Browsing v4 API key. If omitted, GSB checks are skipped gracefully |
| `DATABASE_URL` | ❌ No | Defaults to `sqlite+aiosqlite:///./nebula.db`. Override for PostgreSQL in production |
| `RATE_LIMIT_PER_MINUTE` | ❌ No | Requests per IP per minute. Defaults to `30` |
| `CACHE_TTL_SECONDS` | ❌ No | How long scan results are cached. Defaults to `86400` (24 hours) |
| `ALLOWED_ORIGINS` | ❌ No | CORS allowed origins. Defaults to `["*"]` |

---

## Usage Examples

### 1. Analysing a URL via the Web Interface

1. Navigate to `http://localhost:8000`
2. Paste a suspicious link (e.g. `https://eth-airdrop-claim.xyz`) into the search bar
3. Click **Analyze**
4. Review the trust score, risk flags, investment advice, and safe alternatives

### 2. API call — URL Analysis

```bash
curl -X POST "http://localhost:8000/api/v1/analyze/" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://example-crypto-site.com"}'
```

**Example response:**

```json
{
  "url": "https://example-crypto-site.com",
  "domain": "example-crypto-site.com",
  "trust_score": 12,
  "status": "High Risk",
  "verdict_label": "FRAUDULENT",
  "risk_flags": [
    "Domain registered only 4 days ago (very new)",
    "No SSL certificate — connection is unencrypted",
    "High-risk TLD '.xyz' commonly used by scam sites"
  ],
  "investment_advice": "DO NOT INVEST — This site shows multiple high-risk signals consistent with a scam.",
  "alternatives": ["Coinbase", "Kraken", "Binance"],
  "risk_tips": "Domain only 4 days old. | No SSL — never enter credentials here. | Score below 40/100 — never invest here."
}
```

### 3. API call — Risk Calculator

```bash
curl -X POST "http://localhost:8000/api/v1/analyze/risk-calculator" \
     -H "Content-Type: application/json" \
     -d '{"portfolio_value": 5000, "risk_percentage": 10, "trust_score": 82}'
```

### 4. API call — Scan History

```bash
curl "http://localhost:8000/api/v1/scans/?limit=10"
```

### 5. API call — Bitcoin Trend

```bash
curl "http://localhost:8000/api/v1/bitcoin/trend"
```

---

## Dependencies

Ensure the following are installed before setting up the project:

- **Python** v3.11 or higher
- **pip** (comes with Python)
- **Git**

> Node.js is **not required** — there is no frontend build step.

Key Python packages (see `requirements.txt` for pinned versions):

| Package | Purpose |
|---|---|
| `fastapi` | Web framework and API routing |
| `uvicorn` | ASGI server |
| `pydantic` / `pydantic-settings` | Request validation and settings management |
| `sqlalchemy` + `aiosqlite` | Async ORM and SQLite driver |
| `httpx` | Async HTTP client for external API calls |
| `python-whois` | Domain registration age lookup |
| `tldextract` | TLD and domain parsing |
| `slowapi` | IP-based rate limiting |
| `python-dotenv` | `.env` file loading |

---

## How to Contribute

Contributions are welcome! To get started:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes and commit: `git commit -m "Add your feature"`
4. Push to your fork: `git push origin feature/your-feature-name`
5. Open a Pull Request describing what you changed and why

Please ensure any new API endpoints include Pydantic schema validation and that no secrets are introduced client-side.

---

## License

This project is licensed under the **MIT License**. See the `LICENSE` file for full details.

---

## Acknowledgements / Contact

- **Developer:** [Your Name / Handle]
- **Contact:** reachme@example.com
- **Project Link:** https://github.com/yourusername/nebulascan

Special thanks to the teams behind [FastAPI](https://fastapi.tiangolo.com), [CoinGecko](https://www.coingecko.com), [Google Safe Browsing](https://safebrowsing.google.com), and [Google Gemini](https://deepmind.google/technologies/gemini/) for the APIs that power this tool.

> ⚠️ **Disclaimer:** NebulaScan is for informational and educational purposes only. Trust scores are automated estimates and should never be the sole basis for a financial decision. Always do your own research (DYOR).