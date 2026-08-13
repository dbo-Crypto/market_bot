from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import httpx

from engine.ingest.types import RawBar

KLINES = "https://api.binance.com/api/v3/klines"
TICKER = "https://api.binance.com/api/v3/ticker/price"


async def fetch_klines(
    client: httpx.AsyncClient,
    symbol: str,
    *,
    interval: str = "4h",
    limit: int = 500,
) -> list[RawBar]:
    response = await client.get(KLINES, params={"symbol": symbol, "interval": interval, "limit": limit})
    response.raise_for_status()
    payload = response.json()
    rows: list[RawBar] = []
    for item in payload:
        ts = datetime.fromtimestamp(int(item[0]) / 1000, tz=timezone.utc)
        rows.append(
            RawBar(
                ts=ts,
                open=Decimal(str(item[1])),
                high=Decimal(str(item[2])),
                low=Decimal(str(item[3])),
                close=Decimal(str(item[4])),
                volume=Decimal(str(item[5])),
                timeframe=interval,
            )
        )
    return rows


async def fetch_last(client: httpx.AsyncClient, symbol: str) -> Decimal | None:
    response = await client.get(TICKER, params={"symbol": symbol})
    response.raise_for_status()
    price = response.json().get("price")
    return Decimal(str(price)) if price else None
