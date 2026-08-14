from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import httpx

GROK_MODEL = "grok-4.6"
GROK_URL = "https://api.x.ai/v1/chat/completions"
CACHE_KEY = "grok_review"
ALLOWED_KEYS = (
    "slow_symbols",
    "slow_sleeve_fraction",
    "slow_lookback",
    "slow_skip",
    "slow_sma",
    "snap_symbols",
    "snap_sleeve_fraction",
    "snap_rsi",
    "snap_rsi_buy",
    "snap_sma_filter",
    "snap_sma_exit",
    "snap_max_days",
    "snap_atr",
    "snap_stop_atr",
    "snap_risk_fraction",
    "pulse_symbols",
    "pulse_sleeve_fraction",
    "pulse_risk_fraction",
    "pulse_donchian",
    "pulse_exit_channel",
    "pulse_atr",
    "pulse_stop_atr",
    "pulse_trail_atr",
    "daily_loss_halt",
    "min_trade_notional",
)

REVIEW_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "headline": {"type": "string"},
        "thesis": {"type": "string"},
        "working": {"type": "array", "items": {"type": "string"}},
        "broken": {"type": "array", "items": {"type": "string"}},
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "key": {"type": "string"},
                    "current": {"type": "string"},
                    "suggested": {"type": "string"},
                    "why": {"type": "string"},
                    "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
                },
                "required": ["key", "current", "suggested", "why", "confidence"],
            },
        },
        "do_not_change": {"type": "array", "items": {"type": "string"}},
        "sample_caveat": {"type": "string"},
    },
    "required": [
        "headline",
        "thesis",
        "working",
        "broken",
        "recommendations",
        "do_not_change",
        "sample_caveat",
    ],
}

SYSTEM = """You are Grok reviewing a paper multi-sleeve desk:
- Slow (most of the book): monthly dual momentum on ETFs.
- Snap (small): short-hold QQQ RSI washout.
- Pulse (small): crypto 4h Donchian breakout with ATR stop/trail.

You see the FULL completed book, open positions, current knobs, and recent decisions.

Rules:
- Do not invent trades.
- Only recommend keys from this list: """ + ", ".join(ALLOWED_KEYS) + """.
- Do not retune Slow because Snap or Pulse had a loud week. Sleeves have different jobs.
- If fewer than 8 completed trades, confidence must be low and prefer do_not_change.
- Be specific: sleeve, symbol, exit reason, hold time.
- This is paper. No live brokers, no new asset classes.
- One recommendation per knob.
"""


def empty_review(*, available: bool, error: str | None = None) -> dict:
    return {
        "available": available,
        "model": GROK_MODEL,
        "generated_at": None,
        "review": None,
        "error": error,
    }


def parse_cache(raw: str | None, *, available: bool) -> dict:
    if not raw:
        return empty_review(available=available)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return empty_review(available=available)
    if not isinstance(payload, dict):
        return empty_review(available=available)
    return {
        "available": available,
        "model": payload.get("model") or GROK_MODEL,
        "generated_at": payload.get("generated_at"),
        "review": payload.get("review"),
        "error": payload.get("error"),
    }


def pack_cache(review: dict) -> str:
    return json.dumps(
        {
            "model": GROK_MODEL,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "review": review,
            "error": None,
        }
    )


def build_prompt(payload: dict) -> str:
    return (
        "Review this desk and tell me what to change.\n\n"
        + json.dumps(payload, default=str, indent=2)
    )


async def complete_review(api_key: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=90.0) as client:
        response = await client.post(
            GROK_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": GROK_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": build_prompt(payload)},
                ],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "desk_review",
                        "schema": REVIEW_SCHEMA,
                        "strict": True,
                    },
                },
            },
        )
    if response.status_code >= 400:
        detail = response.text[:400]
        raise RuntimeError(f"Grok HTTP {response.status_code}: {detail}")
    body = response.json()
    content = body["choices"][0]["message"]["content"]
    review = json.loads(content)
    recs = []
    for item in review.get("recommendations") or []:
        key = str(item.get("key") or "")
        if key in ALLOWED_KEYS:
            recs.append(item)
    review["recommendations"] = recs
    return review
