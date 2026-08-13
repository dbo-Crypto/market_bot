from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import httpx

from engine.ingest.types import RawBar

STOOQ = "https://stooq.com/q/d/l/"


def _parse_csv(text: str, limit: int = 600) -> list[RawBar]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines or "," not in lines[0]:
        raise ValueError("stooq returned no CSV")
    rows: list[RawBar] = []
    for line in lines[1:]:
        parts = line.split(",")
        if len(parts) < 5:
            continue
        try:
            day = datetime.strptime(parts[0], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            o, h, l, c = (Decimal(parts[1]), Decimal(parts[2]), Decimal(parts[3]), Decimal(parts[4]))
            vol = Decimal(parts[5]) if len(parts) > 5 and parts[5] not in {"", "0"} else Decimal("0")
        except Exception:
            continue
        if c <= 0:
            continue
        rows.append(RawBar(ts=day, open=o, high=h, low=l, close=c, volume=vol, timeframe="1d"))
    return rows[-limit:]


async def fetch_daily(client: httpx.AsyncClient, feed_symbol: str, limit: int = 600) -> list[RawBar]:
    response = await client.get(STOOQ, params={"s": feed_symbol, "i": "d"})
    response.raise_for_status()
    return _parse_csv(response.text, limit=limit)
