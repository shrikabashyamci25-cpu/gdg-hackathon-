"""
NebulaScan — Single-file backend
Crypto fraud detection API with SQLite database.
Run: uvicorn main:app --host 0.0.0.0 --port 8000
"""

import os
import ssl
import asyncio
import socket
import time
import math
from datetime import datetime, timezone
from typing import Optional, Any
from contextlib import asynccontextmanager

import httpx
import tldextract
from fastapi import FastAPI, HTTPException, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings
from sqlalchemy import (
    String, Integer, Boolean, DateTime, JSON, Text,
    select, func, delete, create_engine
)
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

class Settings(BaseSettings):
    APP_NAME: str = "NebulaScan"
    DATABASE_URL: str = "sqlite+aiosqlite:///./nebula.db"
    GOOGLE_SAFE_BROWSING_KEY: str = ""
    RATE_LIMIT_PER_MINUTE: int = 30
    CACHE_TTL_SECONDS: int = 86400
    ALLOWED_ORIGINS: list[str] = ["*"]
    class Config:
        env_file = ".env"

settings = Settings()

# ─────────────────────────────────────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass

engine = create_async_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=False,
)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

# ─────────────────────────────────────────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────────────────────────────────────────

class ScanRecord(Base):
    __tablename__ = "scan_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    trust_score: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    verdict_label: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    google_safe_browsing: Mapped[dict] = mapped_column(JSON, default={})
    whois_data: Mapped[dict] = mapped_column(JSON, default={})
    ssl_data: Mapped[dict] = mapped_column(JSON, default={})
    risk_flags: Mapped[list] = mapped_column(JSON, default=[])
    investment_advice: Mapped[str] = mapped_column(Text, default="")
    alternatives: Mapped[list] = mapped_column(JSON, default=[])
    risk_tips: Mapped[str] = mapped_column(Text, default="")
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    scanned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AlternativePlatform(Base):
    __tablename__ = "alternative_platforms"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    url: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    why_safe: Mapped[str] = mapped_column(Text, default="")
    how_to_use: Mapped[str] = mapped_column(Text, default="")
    is_regulated: Mapped[bool] = mapped_column(Boolean, default=True)
    region: Mapped[str] = mapped_column(String(100), default="Global")
    logo_url: Mapped[str] = mapped_column(String(255), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

# ─────────────────────────────────────────────────────────────────────────────
# SEED DATA
# ─────────────────────────────────────────────────────────────────────────────

PLATFORMS_SEED = [
    {"name": "Coinbase", "url": "https://www.coinbase.com",
     "description": "US-based regulated exchange, publicly listed on NASDAQ (COIN). Trusted by 100M+ users.",
     "why_safe": "Publicly traded (NASDAQ: COIN), FDIC-insured USD balances, regulated by FinCEN. Operating since 2012.",
     "how_to_use": "1. Sign up at coinbase.com  2. Verify your identity (KYC)  3. Add a payment method  4. Buy crypto  5. Enable 2FA immediately.",
     "is_regulated": True, "region": "USA / Global"},
    {"name": "Kraken", "url": "https://www.kraken.com",
     "description": "US-based exchange with an impeccable security record since 2011. Never been hacked.",
     "why_safe": "Founded 2011, never suffered a major hack, registered MSB with FinCEN. Regular proof-of-reserves audits.",
     "how_to_use": "1. Create account at kraken.com  2. Complete identity verification  3. Fund via bank transfer  4. Trade  5. Withdraw to hardware wallet for large amounts.",
     "is_regulated": True, "region": "USA / Global"},
    {"name": "Binance", "url": "https://www.binance.com",
     "description": "World's largest crypto exchange by volume. Huge asset selection and low fees.",
     "why_safe": "SAFU insurance fund ($1B+), licensed in multiple jurisdictions. 10B+ daily volume provides deep liquidity.",
     "how_to_use": "1. Register at binance.com  2. Complete Level 1 KYC  3. Deposit via P2P, card, or bank wire  4. Trade on Spot market  5. Enable all security features (2FA, anti-phishing code).",
     "is_regulated": True, "region": "Global"},
    {"name": "Gemini", "url": "https://www.gemini.com",
     "description": "NY Department of Financial Services regulated exchange, founded by the Winklevoss twins.",
     "why_safe": "NY DFS regulated, SOC 2 Type 2 certified, FDIC-insured USD up to $250k.",
     "how_to_use": "1. Sign up at gemini.com  2. Verify identity  3. Connect bank account  4. Buy via ActiveTrader for lower fees  5. Enable all security features.",
     "is_regulated": True, "region": "USA"},
    {"name": "Uniswap", "url": "https://app.uniswap.org",
     "description": "Leading decentralized exchange (DEX) on Ethereum. Non-custodial — you keep your keys.",
     "why_safe": "Open-source, audited smart contracts, non-custodial. $4T+ in historical volume. Use only app.uniswap.org.",
     "how_to_use": "1. Install MetaMask  2. Go to app.uniswap.org (bookmark it)  3. Connect wallet  4. Select tokens and swap  5. Always verify contract addresses on Etherscan.",
     "is_regulated": False, "region": "Global (Ethereum)"},
]

async def seed_platforms(db: AsyncSession):
    for data in PLATFORMS_SEED:
        existing = await db.execute(
            select(AlternativePlatform).where(AlternativePlatform.name == data["name"])
        )
        if existing.scalar_one_or_none() is None:
            db.add(AlternativePlatform(**data))
    await db.commit()

# ─────────────────────────────────────────────────────────────────────────────
# SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    url: str = Field(..., max_length=2048)

    @field_validator("url")
    @classmethod
    def ensure_scheme(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            v = "https://" + v
        return v

class GSBResult(BaseModel):
    is_safe: bool
    threats: list[str] = []

class WhoisResult(BaseModel):
    domain_age_days: Optional[int] = None
    registrar: Optional[str] = None
    creation_date: Optional[str] = None
    is_private: bool = False

class SSLResult(BaseModel):
    has_ssl: bool
    issuer: Optional[str] = None
    days_until_expiry: Optional[int] = None

class PlatformOut(BaseModel):
    id: int
    name: str
    url: str
    description: str
    why_safe: str
    how_to_use: str
    is_regulated: bool
    region: str
    logo_url: str
    class Config:
        from_attributes = True

class AnalyzeResponse(BaseModel):
    url: str
    domain: str
    trust_score: int
    status: str
    verdict_label: str
    google_safe_browsing: GSBResult
    whois_data: WhoisResult
    ssl_data: SSLResult
    risk_flags: list[str]
    investment_advice: str
    alternatives: list[PlatformOut]
    risk_tips: str
    scan_id: int
    scanned_at: str

class ScanOut(BaseModel):
    id: int
    url: str
    domain: str
    trust_score: int
    status: str
    verdict_label: str
    is_flagged: bool
    scanned_at: datetime
    class Config:
        from_attributes = True

class RiskCalcRequest(BaseModel):
    portfolio_value: float = Field(..., gt=0)
    risk_percentage: float = Field(..., gt=0, le=100)
    trust_score: int = Field(..., ge=0, le=100)

class RiskCalcResponse(BaseModel):
    portfolio_value: float
    risk_percentage: float
    max_position_usd: float
    adjusted_position_usd: float
    recommendation: str
    trust_score: int

# ─────────────────────────────────────────────────────────────────────────────
# FRAUD SCORING ENGINE
# ─────────────────────────────────────────────────────────────────────────────

SUSPICIOUS_KEYWORDS = [
    "yield","airdrop","free","double","giveaway","profit","100x","moon",
    "pump","get-rich","instant","guaranteed","claim","reward","bonus",
    "presale","ido","ico-drop","free-crypto","earn-now",
]
SUSPICIOUS_TLDS = {".xyz",".tk",".ml",".ga",".cf",".gq",".pw",".top",".click",".loan",".win",".racing"}
BLACKLISTED_DOMAINS = {"fakeexchange.io","crypto-double.net","eth-giveaway.xyz"}

def calculate_trust_score(url: str, gsb: GSBResult, whois: WhoisResult, ssl: SSLResult) -> int:
    score = 100
    real_threats = [t for t in gsb.threats if t != "API_UNAVAILABLE"]
    score -= len(real_threats) * 55
    if not ssl.has_ssl:
        score -= 25
    elif ssl.days_until_expiry is not None and ssl.days_until_expiry < 14:
        score -= 8
    if whois.domain_age_days is not None:
        if whois.domain_age_days < 30:   score -= 40
        elif whois.domain_age_days < 90: score -= 18
    if whois.is_private:
        score -= 12
    url_lower = url.lower()
    hits = sum(1 for kw in SUSPICIOUS_KEYWORDS if kw in url_lower)
    score -= min(hits * 8, 24)
    try:
        ext = tldextract.extract(url)
        tld = f".{ext.suffix}" if ext.suffix else ""
        if tld in SUSPICIOUS_TLDS: score -= 20
        if f"{ext.domain}.{ext.suffix}" in BLACKLISTED_DOMAINS: score = 0
    except Exception:
        pass
    return max(0, min(100, score))

def score_to_status(score: int) -> str:
    if score >= 70: return "Safe"
    if score >= 40: return "Medium Risk"
    return "High Risk"

def score_to_verdict(score: int) -> str:
    if score >= 70: return "SAFE TO INVEST"
    if score >= 40: return "SUSPICIOUS"
    return "FRAUDULENT"

def build_risk_flags(url: str, gsb: GSBResult, whois: WhoisResult, ssl: SSLResult) -> list[str]:
    flags = []
    real_threats = [t for t in gsb.threats if t != "API_UNAVAILABLE"]
    if real_threats:
        flags.append(f"Flagged by Google Safe Browsing for: {', '.join(real_threats)}")
    if not ssl.has_ssl:
        flags.append("No SSL certificate — connection is unencrypted")
    elif ssl.days_until_expiry is not None and ssl.days_until_expiry < 14:
        flags.append(f"SSL certificate expires in {ssl.days_until_expiry} days")
    if whois.domain_age_days is not None:
        if whois.domain_age_days < 30:
            flags.append(f"Domain registered only {whois.domain_age_days} days ago (very new)")
        elif whois.domain_age_days < 90:
            flags.append(f"Domain is only {whois.domain_age_days} days old (recently registered)")
    if whois.is_private:
        flags.append("Registrant identity is hidden (WHOIS privacy protection)")
    url_lower = url.lower()
    hits = [kw for kw in SUSPICIOUS_KEYWORDS if kw in url_lower]
    if hits:
        flags.append(f"Suspicious keywords in URL: {', '.join(hits[:4])}")
    try:
        ext = tldextract.extract(url)
        tld = f".{ext.suffix}" if ext.suffix else ""
        if tld in SUSPICIOUS_TLDS:
            flags.append(f"High-risk TLD '{tld}' commonly used by scam sites")
    except Exception:
        pass
    return flags

def build_investment_advice(score: int) -> str:
    if score < 40:
        return "DO NOT INVEST — This site shows multiple high-risk signals consistent with a scam. Never connect your wallet or send funds to this address."
    if score < 70:
        return "EXTREME CAUTION — Multiple red flags detected. If you choose to interact, cap exposure to no more than 1% of your portfolio. Never invest more than you can afford to lose entirely."
    return "Site appears legitimate based on available signals. Still, never invest more than 5–10% of your portfolio in any single crypto platform. Always enable 2FA and never share your private keys."

def build_risk_tips(score: int, gsb: GSBResult, whois: WhoisResult, ssl: SSLResult) -> str:
    tips = []
    real_threats = [t for t in gsb.threats if t != "API_UNAVAILABLE"]
    if real_threats: tips.append(f"GSB flagged: {', '.join(real_threats)}.")
    if not ssl.has_ssl: tips.append("No SSL — never enter credentials here.")
    if whois.domain_age_days is not None and whois.domain_age_days < 90:
        tips.append(f"Domain only {whois.domain_age_days} days old.")
    if whois.is_private: tips.append("Registrant identity hidden.")
    if score < 40: tips.append("Score below 40/100 — never invest here.")
    elif score < 70: tips.append("Limit exposure to max 1% of portfolio.")
    else: tips.append("No major red flags. Always do your own research.")
    return " | ".join(tips)

# ─────────────────────────────────────────────────────────────────────────────
# EXTERNAL CHECK SERVICES
# ─────────────────────────────────────────────────────────────────────────────

async def check_google_safe_browsing(url: str) -> GSBResult:
    api_key = settings.GOOGLE_SAFE_BROWSING_KEY
    if not api_key:
        return GSBResult(is_safe=True, threats=[])
    payload = {
        "client": {"clientId": "nebulascan", "clientVersion": "1.0.0"},
        "threatInfo": {
            "threatTypes": ["MALWARE","SOCIAL_ENGINEERING","UNWANTED_SOFTWARE","POTENTIALLY_HARMFUL_APPLICATION"],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": url}],
        },
    }
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.post(
                "https://safebrowsing.googleapis.com/v4/threatMatches:find",
                params={"key": api_key}, json=payload,
            )
            resp.raise_for_status()
            matches = resp.json().get("matches", [])
            threats = list({m["threatType"] for m in matches})
            return GSBResult(is_safe=len(threats) == 0, threats=threats)
    except Exception:
        return GSBResult(is_safe=True, threats=["API_UNAVAILABLE"])


def _whois_sync(domain: str) -> WhoisResult:
    try:
        import whois
        w = whois.whois(domain)
        d = w.get("creation_date")
        if isinstance(d, list): d = d[0]
        age_days = None
        creation_str = None
        if isinstance(d, datetime):
            now = datetime.now(timezone.utc)
            dt = d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d
            age_days = max(0, (now - dt).days)
            creation_str = d.isoformat()
        name = str(w.get("name", "") or "").lower()
        is_private = name in ("redacted for privacy","data protected","not disclosed","withheld for privacy","")
        registrar = w.get("registrar")
        return WhoisResult(
            domain_age_days=age_days,
            registrar=registrar if isinstance(registrar, str) else None,
            creation_date=creation_str,
            is_private=is_private,
        )
    except Exception:
        return WhoisResult()

async def get_whois_data(domain: str) -> WhoisResult:
    loop = asyncio.get_event_loop()
    try:
        return await asyncio.wait_for(loop.run_in_executor(None, _whois_sync, domain), timeout=8.0)
    except Exception:
        return WhoisResult()


def _ssl_sync(hostname: str) -> SSLResult:
    ctx = ssl.create_default_context()
    try:
        with socket.create_connection((hostname, 443), timeout=5) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                issuer_dict = dict(x[0] for x in cert.get("issuer", []))
                issuer = issuer_dict.get("organizationName", "Unknown")
                expiry_str = cert.get("notAfter", "")
                expiry_dt = datetime.strptime(expiry_str, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
                days_left = (expiry_dt - datetime.now(timezone.utc)).days
                return SSLResult(has_ssl=True, issuer=issuer, days_until_expiry=days_left)
    except Exception:
        return SSLResult(has_ssl=False)

async def check_ssl(hostname: str) -> SSLResult:
    loop = asyncio.get_event_loop()
    try:
        return await asyncio.wait_for(loop.run_in_executor(None, _ssl_sync, hostname), timeout=7.0)
    except Exception:
        return SSLResult(has_ssl=False)

# ─────────────────────────────────────────────────────────────────────────────
# IN-MEMORY CACHE
# ─────────────────────────────────────────────────────────────────────────────

_cache: dict[str, tuple[float, AnalyzeResponse]] = {}

# ─────────────────────────────────────────────────────────────────────────────
# APP + LIFESPAN
# ─────────────────────────────────────────────────────────────────────────────

limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"])

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as session:
        await seed_platforms(session)
    yield

app = FastAPI(
    title="NebulaScan API",
    description="Crypto fraud & phishing detection — URL analysis, trust scoring, investment guidance.",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# ROUTES — HEALTH
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "app": settings.APP_NAME, "version": "1.0.0"}

# ─────────────────────────────────────────────────────────────────────────────
# ROUTES — ANALYZE
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/v1/analyze/", response_model=AnalyzeResponse, tags=["Analysis"])
@limiter.limit("20/minute")
async def analyze(request: Request, payload: AnalyzeRequest, db: AsyncSession = Depends(get_db)):
    """Analyse a URL for crypto fraud signals."""
    url = payload.url
    cache_key = url.lower().rstrip("/")

    # Return cached result if fresh
    if cache_key in _cache:
        ts, cached = _cache[cache_key]
        if time.time() - ts < settings.CACHE_TTL_SECONDS:
            return cached

    try:
        ext = tldextract.extract(url)
        domain = f"{ext.domain}.{ext.suffix}" if ext.suffix else ext.domain
    except Exception:
        domain = url.split("//")[-1].split("/")[0]

    # Run all external checks concurrently
    gsb, whois, ssl_res = await asyncio.gather(
        check_google_safe_browsing(url),
        get_whois_data(domain),
        check_ssl(domain),
    )

    score         = calculate_trust_score(url, gsb, whois, ssl_res)
    status        = score_to_status(score)
    verdict       = score_to_verdict(score)
    flags         = build_risk_flags(url, gsb, whois, ssl_res)
    advice        = build_investment_advice(score)
    tips          = build_risk_tips(score, gsb, whois, ssl_res)

    # Fetch safe alternatives when site is risky
    alts_rows = []
    if score < 70:
        res = await db.execute(
            select(AlternativePlatform).where(AlternativePlatform.is_active == True).limit(3)
        )
        alts_rows = list(res.scalars().all())

    # Persist to database
    record = ScanRecord(
        url=url, domain=domain, trust_score=score, status=status,
        verdict_label=verdict,
        google_safe_browsing=gsb.model_dump(),
        whois_data=whois.model_dump(),
        ssl_data=ssl_res.model_dump(),
        risk_flags=flags,
        investment_advice=advice,
        alternatives=[a.name for a in alts_rows],
        risk_tips=tips,
        is_flagged=(score < 40),
        scanned_at=datetime.utcnow(),
    )
    db.add(record)
    await db.flush()

    response = AnalyzeResponse(
        url=url, domain=domain, trust_score=score, status=status,
        verdict_label=verdict,
        google_safe_browsing=gsb,
        whois_data=whois,
        ssl_data=ssl_res,
        risk_flags=flags,
        investment_advice=advice,
        alternatives=[PlatformOut.model_validate(a) for a in alts_rows],
        risk_tips=tips,
        scan_id=record.id,
        scanned_at=datetime.utcnow().isoformat(),
    )

    _cache[cache_key] = (time.time(), response)
    return response


@app.post("/api/v1/analyze/risk-calculator", tags=["Analysis"])
async def risk_calculator(payload: RiskCalcRequest):
    max_pos = payload.portfolio_value * (payload.risk_percentage / 100)
    adjusted = max_pos * (payload.trust_score / 100)
    if payload.trust_score < 40:
        rec = f"HIGH RISK — Do not invest. If you must, cap at ${adjusted:,.2f}."
    elif payload.trust_score < 70:
        rec = f"MEDIUM RISK — Limit position to ${adjusted:,.2f} (risk-adjusted max)."
    else:
        rec = f"Site looks legitimate. Standard position: ${max_pos:,.2f}. Adjusted: ${adjusted:,.2f}."
    return RiskCalcResponse(
        portfolio_value=payload.portfolio_value,
        risk_percentage=payload.risk_percentage,
        max_position_usd=round(max_pos, 2),
        adjusted_position_usd=round(adjusted, 2),
        recommendation=rec,
        trust_score=payload.trust_score,
    )

# ─────────────────────────────────────────────────────────────────────────────
# ROUTES — SCAN HISTORY (Database)
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/v1/scans/stats", tags=["Scan History"])
async def scan_stats(db: AsyncSession = Depends(get_db)):
    """Dashboard statistics from the database."""
    row = (await db.execute(
        select(
            func.count(ScanRecord.id).label("total"),
            func.sum(func.cast(ScanRecord.status == "High Risk", type_=None)).label("high"),
            func.sum(func.cast(ScanRecord.status == "Medium Risk", type_=None)).label("medium"),
            func.sum(func.cast(ScanRecord.status == "Safe", type_=None)).label("safe"),
            func.avg(ScanRecord.trust_score).label("avg"),
            func.max(ScanRecord.scanned_at).label("latest"),
        )
    )).one()
    return {
        "total": row.total or 0,
        "high_risk_count": int(row.high or 0),
        "medium_risk_count": int(row.medium or 0),
        "safe_count": int(row.safe or 0),
        "average_score": round(float(row.avg), 1) if row.avg else None,
        "latest_scan_at": row.latest,
    }


@app.get("/api/v1/scans/", tags=["Scan History"])
async def list_scans(
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Paginated scan history with optional filter and search."""
    q = select(ScanRecord)
    if status and status in ("Safe", "Medium Risk", "High Risk"):
        q = q.where(ScanRecord.status == status)
    if search:
        like = f"%{search.lower()}%"
        q = q.where(ScanRecord.url.ilike(like) | ScanRecord.domain.ilike(like))
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    items = (await db.execute(q.order_by(ScanRecord.scanned_at.desc()).offset(skip).limit(limit))).scalars().all()
    return {"total": total, "items": [ScanOut.model_validate(i) for i in items]}


@app.get("/api/v1/scans/{scan_id}", tags=["Scan History"])
async def get_scan(scan_id: int, db: AsyncSession = Depends(get_db)):
    record = (await db.execute(select(ScanRecord).where(ScanRecord.id == scan_id))).scalar_one_or_none()
    if not record:
        raise HTTPException(404, f"Scan {scan_id} not found")
    return ScanOut.model_validate(record)


@app.delete("/api/v1/scans/{scan_id}", status_code=204, tags=["Scan History"])
async def delete_scan(scan_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(delete(ScanRecord).where(ScanRecord.id == scan_id))
    if result.rowcount == 0:
        raise HTTPException(404, f"Scan {scan_id} not found")


@app.delete("/api/v1/scans/", tags=["Scan History"])
async def clear_scans(db: AsyncSession = Depends(get_db)):
    result = await db.execute(delete(ScanRecord))
    return {"deleted": result.rowcount}

# ─────────────────────────────────────────────────────────────────────────────
# ROUTES — PLATFORMS
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/v1/platforms/", response_model=list[PlatformOut], tags=["Platforms"])
async def list_platforms(db: AsyncSession = Depends(get_db)):
    """List all safe regulated alternative platforms."""
    result = await db.execute(
        select(AlternativePlatform).where(AlternativePlatform.is_active == True)
    )
    return result.scalars().all()

# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

_DIR = os.path.dirname(os.path.abspath(__file__))

def _read_html(filename: str) -> str:
    with open(os.path.join(_DIR, filename), encoding="utf-8") as f:
        return f.read()

@app.get("/", include_in_schema=False)
async def home_root():
    from fastapi.responses import HTMLResponse
    return HTMLResponse(_read_html("home_mobile_UI.html"))

@app.get("/home_mobile_UI.html", include_in_schema=False)
async def home():
    from fastapi.responses import HTMLResponse
    return HTMLResponse(_read_html("home_mobile_UI.html"))

@app.get("/results_UI.html", include_in_schema=False)
async def results():
    from fastapi.responses import HTMLResponse
    return HTMLResponse(_read_html("results_UI.html"))

@app.get("/design(UI).html", include_in_schema=False)
async def design():
    from fastapi.responses import HTMLResponse
    return HTMLResponse(_read_html("design(UI).html"))

@app.get("/history.html", include_in_schema=False)
async def history():
    from fastapi.responses import HTMLResponse
    return HTMLResponse(_read_html("history.html"))

@app.get("/security.html", include_in_schema=False)
async def security():
    from fastapi.responses import HTMLResponse
    return HTMLResponse(_read_html("security.html"))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
