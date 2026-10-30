from datetime import datetime, timezone
from .config import MIN_LIQUIDITY_USD

def _num(value, default=0.0):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return default

def analyse(address: str, pair: dict, mint: dict | None) -> dict:
    base = pair.get("baseToken") or {}
    quote = pair.get("quoteToken") or {}
    liquidity = _num((pair.get("liquidity") or {}).get("usd"))
    volume = pair.get("volume") or {}
    txns = pair.get("txns") or {}
    h24 = txns.get("h24") or {}
    price_change = pair.get("priceChange") or {}
    fdv = _num(pair.get("fdv"))
    market_cap = _num(pair.get("marketCap"), fdv)
    created_ms = pair.get("pairCreatedAt")
    age_hours = None
    if created_ms:
        age_hours = max(0, (datetime.now(timezone.utc).timestamp() - created_ms / 1000) / 3600)

    score = 50
    reasons = []
    hard_flags = []

    if mint is None:
        reasons.append("Mint authority and holder-account checks unavailable; verify independently.")
    else:
        if mint["mint_authority_enabled"]:
            score -= 20
            hard_flags.append("Mint authority is still enabled.")
        else:
            score += 8
            reasons.append("Mint authority is revoked.")
        if mint["freeze_authority_enabled"]:
            score -= 15
            hard_flags.append("Freeze authority is still enabled.")
        else:
            score += 6
            reasons.append("Freeze authority is revoked.")
        top10 = mint.get("top10_account_share_pct")
        if top10 is not None:
            if top10 >= 60:
                score -= 20
                hard_flags.append(f"Top 10 token accounts hold about {top10:.1f}% of supply.")
            elif top10 >= 35:
                score -= 10
                reasons.append(f"Top 10 token accounts hold about {top10:.1f}% of supply; concentration is elevated.")
            else:
                score += 5
                reasons.append(f"Top 10 token accounts hold about {top10:.1f}% of supply.")
        else:
            reasons.append("Holder concentration could not be calculated.")

    if liquidity < MIN_LIQUIDITY_USD:
        score -= 25
        hard_flags.append(f"Liquidity is below the configured ${MIN_LIQUIDITY_USD:,.0f} minimum.")
    elif liquidity >= 100_000:
        score += 10
        reasons.append("Reported pool liquidity is above $100,000.")
    else:
        score += 3
        reasons.append("Reported liquidity clears the configured minimum.")

    vol24 = _num(volume.get("h24"))
    if vol24 > 0 and liquidity > 0:
        ratio = vol24 / liquidity
        if ratio > 20:
            score -= 8
            reasons.append("24-hour volume is unusually high relative to liquidity; investigate wash trading or volatile turnover.")
        elif ratio >= 1:
            score += 4
            reasons.append("24-hour volume is material relative to liquidity.")
        else:
            reasons.append("24-hour volume is low relative to liquidity.")

    buys = int(_num(h24.get("buys")))
    sells = int(_num(h24.get("sells")))
    if buys + sells:
        if sells > buys * 2:
            score -= 8
            reasons.append("24-hour sell transactions substantially exceed buys.")
        elif buys > sells * 1.5:
            score += 3
            reasons.append("Buy transactions exceed sells; this is not proof of sustainable demand.")
        else:
            reasons.append("Buy/sell transaction counts are relatively balanced.")

    chg = _num(price_change.get("h24"))
    if chg <= -50:
        score -= 12
        reasons.append(f"24-hour price change is {chg:.1f}%; severe downside volatility.")
    elif chg >= 100:
        score -= 5
        reasons.append(f"24-hour price change is +{chg:.1f}%; sharp rallies can reverse quickly.")
    else:
        reasons.append(f"24-hour price change: {chg:+.1f}%.")

    score = max(0, min(100, score))
    if hard_flags:
        verdict = "AVOID / HIGH RISK"
    elif mint is None:
        verdict = "INSUFFICIENT DATA"
    elif score >= 75:
        verdict = "POTENTIAL CANDIDATE — RESEARCH FURTHER"
    elif score >= 55:
        verdict = "WATCH"
    else:
        verdict = "HIGH RISK"

    return {
        "address": address,
        "name": base.get("name") or "Unknown",
        "symbol": base.get("symbol") or "???",
        "pair_url": pair.get("url"),
        "dex": pair.get("dexId"),
        "price_usd": pair.get("priceUsd"),
        "liquidity_usd": liquidity,
        "volume_24h_usd": vol24,
        "market_cap_usd": market_cap,
        "fdv_usd": fdv,
        "price_change_24h_pct": chg,
        "buys_24h": buys,
        "sells_24h": sells,
        "pair_age_hours": age_hours,
        "mint": mint,
        "score": score,
        "verdict": verdict,
        "hard_flags": hard_flags,
        "reasons": reasons,
    }
