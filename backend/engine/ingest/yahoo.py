from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import httpx

from engine.ingest.types import RawBar

CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"


async def fetch_daily(client: httpx.AsyncClient, symbol: str, range_="2y") -> list[RawBar]:
    response = await client.get(
        CHART.format(symbol=symbol),
        params={"interval": "1d", "range": range_},
    )
    response.raise_for_status()
    payload = response.json()
    result = (payload.get("chart") or {}).get("result") or []
    if not result:
        raise ValueError(f"yahoo empty for {symbol}")
    block = result[0]
    stamps = block.get("timestamp") or []
    quote = ((block.get("indicators") or {}).get("quote") or [{}])[0]
    opens = quote.get("open") or []
    highs = quote.get("high") or []
    lows = quote.get("low") or []
    closes = quote.get("close") or []
    vols = quote.get("volume") or []
    rows: list[RawBar] = []
    for i, stamp in enumerate(stamps):
        try:
            close = closes[i]
            if close is None:
                continue
            ts = datetime.fromtimestamp(int(stamp), tz=timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            rows.append(
                RawBar(
                    ts=ts,
                    open=Decimal(str(opens[i] if opens[i] is not None else close)),
                    high=Decimal(str(highs[i] if highs[i] is not None else close)),
                    low=Decimal(str(lows[i] if lows[i] is not None else close)),
                    close=Decimal(str(close)),
                    volume=Decimal(str(vols[i] or 0)),
                    timeframe="1d",
                )
            )
        except Exception:
            continue
    if not rows:
        raise ValueError(f"yahoo parsed no bars for {symbol}")
    return rows


async def fetch_last(client: httpx.AsyncClient, symbol: str) -> Decimal | None:
    try:
        bars = await fetch_daily(client, symbol, range_="5d")
    except Exception:
        return None
    return bars[-1].close if bars else None
