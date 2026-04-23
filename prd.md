================================================================================
                    PRODUCT REQUIREMENTS DOCUMENT (PRD)
                          CryptoShield - Crypto Scam Scanner
                            Version 1.0 | April 23, 2026
================================================================================

1. EXECUTIVE SUMMARY
--------------------------------------------------------------------------------
Problem: The crypto space is flooded with fraudulent websites (rug pulls, 
phishing, fake exchanges) causing users to lose millions. Novice investors 
cannot distinguish legitimate platforms from scams.

Solution: A web-based tool where users paste a crypto website URL. The system 
analyzes the URL and returns:
- A risk score (Fraudulent / Suspicious / Safe to Invest)
- Investment guidance (how much to invest, warning limits)
- Alternative safe recommendations if the site is bad
- Educational "how-to-use" guides for recommended alternatives

Success Metric: 90% accuracy in detecting known fraudulent sites.


2. GOALS & SUCCESS METRICS (KPIs)
--------------------------------------------------------------------------------
| Goal                 | Success Metric                                   |
|----------------------|--------------------------------------------------|
| Accuracy             | >85% correct classification                     |
| Speed                | Analysis completes within 5 seconds             |
| User Trust           | <2% false positives                             |
| Engagement           | 40% click-through to alternatives               |
| Investment Safety    | 50% follow diversification tip                  |


3. USER PERSONAS
--------------------------------------------------------------------------------
Persona 1 - Crypto Newbie (Alex, 24): Has $500 to invest. Can't tell real from 
fake exchanges.

Persona 2 - Casual Trader (Sarah, 34): Uses Binance but clicks Google ads for 
"new coins". Almost lost money to phishing.

Persona 3 - Power User (Mike, 41): Checks 10+ sites daily. Needs quick risk 
assessment before connecting wallet.


4. FUNCTIONAL REQUIREMENTS
--------------------------------------------------------------------------------

FR-01: URL INPUT & VALIDATION
- User can paste a URL into a text box
- System validates URL format (http://, https://, or domain name)
- Invalid URLs show immediate error message
- Max URL length: 2048 characters

FR-02: WEBSITE ANALYSIS ENGINE
On submission, system analyzes URL using:
- Known scam databases (Etherscan, Chainabuse, ScamAdviser API)
- Domain age (Whois lookup - younger domains = higher risk)
- SSL certificate validity
- Blacklist check (Google Safe Browsing, PhishTank)
- On-chain contract verification (if URL is a DEX or token site)

Returns one of three verdicts:
- 🔴 FRAUDULENT - High confidence scam (never invest)
- 🟡 SUSPICIOUS - Some red flags (invest with extreme caution)
- 🟢 SAFE TO INVEST - Verified legitimate platform

FR-03: INVESTMENT GUIDANCE
- For 🟢 Safe sites: "Recommended Max Investment: 5-10% of your portfolio" 
  plus diversification warning
- For 🟡 Suspicious sites: "DO NOT INVEST MORE THAN YOU CAN LOSE - Max 1% 
  of portfolio" and flags specific risks
- For 🔴 Fraudulent sites: "DO NOT INVEST - This site is likely a scam"

FR-04: ALTERNATIVE RECOMMENDATIONS (If site is not good)
- If verdict is 🟡 or 🔴, show 2-3 safe alternative websites
- For each alternative: Name & URL, "Why it's safe", Brief "How to use" guide
- Examples: Binance, Coinbase, Kraken, Uniswap

FR-05: "HOW TO USE" GUIDES FOR ALTERNATIVES
Each alternative has a collapsible guide with:
- Step 1: Create account (link to signup)
- Step 2: Deposit funds (minimum amounts, accepted currencies)
- Step 3: Buy the desired crypto
- Security tip for that platform

FR-06: INVESTMENT TIPS SECTION (Persistent)
Sidebar or footer showing dynamic tips:
- "Never invest more than 10% of savings in crypto"
- "Use a hardware wallet for amounts over $1000"
- "Enable 2FA on every exchange"
- "If it promises 1000% returns in a week - it's a scam"

FR-07: HISTORY / RECENT SEARCHES (Nice-to-have)
- Store last 5 searches in local browser storage
- Allow user to re-run or clear history


5. NON-FUNCTIONAL REQUIREMENTS
--------------------------------------------------------------------------------
| Category      | Requirement                                      |
|---------------|--------------------------------------------------|
| Performance   | Analysis response <5 seconds for 95% of URLs    |
| Availability  | 99.5% uptime                                     |
| Security      | No API keys exposed client-side                  |
| Privacy       | URLs not permanently logged                      |
| Scalability   | Handle 10,000 concurrent users                   |
| Usability     | Mobile-responsive design                         |


6. USER FLOW
--------------------------------------------------------------------------------
User lands on homepage
    ↓
Pastes URL (e.g., "https://fakecryptoexchange.xyz")
    ↓
Clicks "Analyze" button
    ↓
[Loading spinner for 2-5 seconds]
    ↓
Result Page:
  - Verdict: 🔴 FRAUDULENT
  - Risk signals: Domain age 3 days, no SSL, on 12 blacklists
  - Investment advice: "Do not invest any amount"
  - Alternative #1: Binance (with "How to use" guide)
  - Alternative #2: Kraken (with "How to use" guide)
  - Pro tip sidebar: "Legit exchanges never ask for your private key"
    ↓
User clicks alternative → reads guide → goes to safe site


7. EDGE CASES & ERROR HANDLING
--------------------------------------------------------------------------------
| Edge Case                                      | System Response                           |
|------------------------------------------------|-------------------------------------------|
| User pastes non-website URL (search result)   | "Please enter a website URL"              |
| Site is down (404/timeout)                    | "Site unreachable - check URL or try later"|
| All external risk APIs fail                   | Fallback to local cached blacklist        |
| User submits same URL twice                   | Show cached result instantly              |
| Mobile + slow connection                      | Show lightweight result (no heavy images) |


8. OUT OF SCOPE (Version 1.0)
--------------------------------------------------------------------------------
❌ Browser extension or mobile app (web only first)
❌ User accounts / login system
❌ Real-time wallet connection (MetaMask integration)
❌ Automated on-chain transaction simulation
❌ Paid subscription or premium tier
❌ Multi-language support (English only for MVP)


9. RECOMMENDED TECH STACK
--------------------------------------------------------------------------------

FRONTEND (User Interface)
- Framework: Next.js 14 (React)
- UI Library: Tailwind CSS + shadcn/ui
- State Management: React Context + SWR
- Charts: Recharts (optional for risk meter)

BACKEND (Analysis Engine)
- API Layer: Next.js API Routes or Python FastAPI
- URL Analysis: Python FastAPI (recommended)
- Background Jobs: Celery + Redis (if scaling)
- Caching: Upstash Redis or Vercel KV

EXTERNAL APIS (Risk Data)
- Google Safe Browsing API (free tier: 10k requests/day)
- VirusTotal API (free tier: 500 requests/day)
- Whois API (whoisxmlapi.com) - Freemium
- ScamAdviser API (~$49/mo)
- Chainabuse / Etherscan (free with API key)

DATABASE (Optional for caching)
- PostgreSQL (Supabase free tier) or Upstash Redis

HOSTING & DEPLOYMENT
- Vercel (Frontend + Next.js API) - Free tier
- Railway or Render (Python backend if separate)
- GitHub (version control)

MONITORING & ANALYTICS
- Sentry (error tracking)
- Google Analytics or Plausible (anonymous user behavior)
- Upstash Redis Insights (cache performance)


10. SAMPLE ARCHITECTURE DIAGRAM
--------------------------------------------------------------------------------

User Browser
     │
     ▼
┌─────────────────┐
│  Next.js (Vercel)│ ◄─── Serve HTML/CSS/JS
│  - UI Component │
│  - API Routes   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│ Python FastAPI  │────►│ Whois / SSL API  │
│ (Analysis Logic)│     └──────────────────┘
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│  Redis Cache    │     │ Google Safe      │
│  (24hr results) │     │ Browsing API     │
└─────────────────┘     └──────────────────┘
                                │
                                ▼
                      ┌──────────────────┐
                      │ VirusTotal API   │
                      └──────────────────┘


11. SAMPLE OUTPUT (Mock Result Page)
--------------------------------------------------------------------------------

🔍 Analyzing: https://coinswapp.netlify.app

✅ Verdict: 🟡 SUSPICIOUS
Risk score: 68/100 (High risk)

⚠️ Red flags found:
- Domain age: 12 days (very new)
- SSL issuer: Self-signed certificate
- Blacklisted by: 2 sources (ScamAdviser, PhishTank)

💰 Investment advice:
DO NOT invest more than 1% of your portfolio. This site shows multiple 
warning signs.

🚀 Better alternatives:

1. Binance
   ✅ Why safe: Licensed, 5+ years, audited.
   📖 How to use: [Click for guide]

2. Coinbase
   ✅ Why safe: Publicly traded company (NASDAQ: COIN).
   📖 How to use: [Click for guide]

💡 Pro tip: Never invest based on a single tool. Always check official Twitter 
and Reddit communities first.


12. RISKS & MITIGATION
--------------------------------------------------------------------------------
| Risk                                      | Mitigation                               |
|-------------------------------------------|------------------------------------------|
| APIs rate limit us (free tiers exhausted)| Cache aggressively. Upgrade to paid tier |
| False positives (safe marked fraud)      | Use multiple sources + "Report error"    |
| Users ignore advice and invest anyway    | Add pop-up warning requiring confirmation|
| Legal liability                          | Add disclaimer: "DYOR - informational only"|


13. DEVELOPMENT CHECKLIST
--------------------------------------------------------------------------------
[ ] Get stakeholder sign-off
[ ] Choose hosting platform (Vercel + Railway recommended)
[ ] Sign up for free API keys
[ ] Build MVP: URL input + domain age + one blacklist API
[ ] Add investment tips and alternatives (Phase 2)
[ ] Add disclaimer page and privacy policy


================================================================================
                              END OF PRD
================================================================================