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


def _money(value: object) -> str:
    if value is None:
        return "—"
    return f"${float(value):,.2f}"


def _num(value: object, digits: int = 3) -> str:
    if value is None:
        return "—"
    return f"{float(value):.{digits}f}"


def _ts(value: object) -> str:
    if not value:
        return "—"
    return str(value).replace("T", " ")[:19] + " UTC"


def format_briefing(payload: dict) -> str:
    """Plain-text book a human can upload to Grok chat."""
    account = payload.get("account") or {}
    settings = payload.get("settings") or {}
    summary = payload.get("summary") or {}
    trades = payload.get("completed_trades") or []
    opens = payload.get("open_positions") or []
    decisions = payload.get("recent_decisions") or []
    lines = [
        "PAPER DESK BRIEFING — Market Bot",
        f"Snapshot: {_ts(datetime.now(timezone.utc).isoformat())}",
        "Mode: paper only. Virtual bankroll. No live orders.",
        "",
        "HOW TO USE THIS FILE",
        "You are Grok reviewing a paper multi-sleeve desk:",
        "- Slow (~80%): monthly dual momentum on ETFs.",
        "- Snap (~8%): short-hold QQQ RSI washout.",
        "- Pulse (~12%): crypto 4h Donchian breakout with ATR stop/trail.",
        "Read every trade, open position, knob, and decision. Then tell me:",
        "1) What is working and what is leaking money.",
        "2) Specific setting changes (key, current → suggested, why, confidence low/medium/high).",
        "3) What NOT to change given the sample size.",
        "Do not invent trades. Respect sleeve jobs — do not retune Slow because Pulse is quiet.",
        "If fewer than 8 completed trades, confidence must be low.",
        "This is paper. Do not suggest wallets, live brokers, or new asset classes.",
        "Only recommend these keys: " + ", ".join(ALLOWED_KEYS) + ".",
        "",
        "ACCOUNT",
        f"- Bankroll start: {_money(account.get('bankroll_start'))}",
        f"- Equity:         {_money(account.get('equity'))}",
        f"- Cash:           {_money(account.get('cash'))}",
        f"- Open MTM:       {_money(account.get('mtm'))}",
        f"- Realized P&L:   {_money(account.get('realized_pnl'))}",
        "",
        "KNOBS",
    ]
    for key in ALLOWED_KEYS:
        if key in settings:
            lines.append(f"  {key}={settings[key]}")
    lines += [
        "",
        "COMPLETED BOOK",
        (
            f"  N={summary.get('trades', 0)}  {summary.get('wins', 0)}W/"
            f"{summary.get('losses', 0)}L  win_rate={summary.get('win_rate')}  "
            f"net={_money(summary.get('pnl'))}  expectancy={_money(summary.get('expectancy'))}"
        ),
        "  TRADE TAPE",
    ]
    if not trades:
        lines.append("    (none yet)")
    for row in trades:
        lines.append(
            "    "
            f"#{row.get('id')} {row.get('result')} {row.get('sleeve')} {row.get('symbol')}  "
            f"qty={row.get('qty')} avg={_num(row.get('avg_price'))} "
            f"pnl={_money(row.get('realized_pnl'))} exit={row.get('exit_reason')} "
            f"hold_h={_num(row.get('hold_hours'), 1)}  {_ts(row.get('opened_at'))} → {_ts(row.get('closed_at'))}"
        )
    for name, key in (("BY SLEEVE", "by_sleeve"), ("BY SYMBOL", "by_symbol"), ("BY EXIT", "by_exit")):
        rows = payload.get(key) or []
        if not rows:
            continue
        lines.append(f"  {name}")
        for row in rows:
            lines.append(
                f"    {row.get('key')}  n={row.get('trades')}  "
                f"{row.get('wins')}W/{row.get('losses')}L  pnl={_money(row.get('pnl'))}"
            )
    lines += ["", "OPEN POSITIONS"]
    if not opens:
        lines.append("  (none)")
    for row in opens:
        lines.append(
            f"  {row.get('sleeve')} {row.get('symbol')}  qty={row.get('qty')} "
            f"avg={_num(row.get('avg_price'))} mark={_num(row.get('mark'))} "
            f"mtm={_money(row.get('market_value'))} latent={_money(row.get('latent_pnl'))}  "
            f"opened {_ts(row.get('opened_at'))}"
        )
    lines += ["", "RECENT DECISIONS"]
    if not decisions:
        lines.append("  (none)")
    for row in decisions[:40]:
        lines.append(
            f"  {_ts(row.get('ts'))}  {row.get('action')}  {row.get('sleeve')} {row.get('symbol')}  "
            f"qty={row.get('qty')} score={row.get('score')}  {row.get('reason')}"
        )
    lines += [
        "",
        "OUTPUT FORMAT",
        "Headline, thesis, working, broken, recommendations (key | current → suggested | why | confidence),",
        "do_not_change, sample_caveat.",
        "",
    ]
    return "\n".join(lines)
