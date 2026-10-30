import json
from .config import OPENAI_API_KEY, OPENAI_MODEL

async def explain(report: dict) -> str | None:
    if not OPENAI_API_KEY:
        return None
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        # Only send the structured public-data report. Never send secrets or wallet keys.
        safe = {k: report.get(k) for k in (
            "name", "symbol", "score", "verdict", "liquidity_usd",
            "volume_24h_usd", "market_cap_usd", "price_change_24h_pct",
            "buys_24h", "sells_24h", "mint", "hard_flags", "reasons"
        )}
        response = await client.responses.create(
            model=OPENAI_MODEL,
            instructions=("Explain this token research report neutrally in concise plain English. "
                "Do not invent facts, predict returns, or give personalised financial advice. "
                "Do not override hard risk flags. State that the score is heuristic and not proof of safety."),
            input=json.dumps(safe, ensure_ascii=False),
        )
        return response.output_text.strip()
    except Exception as exc:
        return f"AI explanation unavailable ({type(exc).__name__}). The rule-based report is still available."
