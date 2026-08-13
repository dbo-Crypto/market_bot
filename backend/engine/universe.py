from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Spec:
    symbol: str
    name: str
    sleeve: str
    kind: str
    venue: str
    feed_symbol: str
    lot_size: Decimal


CATALOG: dict[str, Spec] = {
    "SPY": Spec("SPY", "S&P 500", "slow", "etf", "stooq", "spy.us", Decimal("0.001")),
    "EZU": Spec("EZU", "Eurozone", "slow", "etf", "stooq", "ezu.us", Decimal("0.001")),
    "QQQ": Spec("QQQ", "Nasdaq 100", "snap", "etf", "stooq", "qqq.us", Decimal("0.001")),
    "IWM": Spec("IWM", "Russell 2000", "slow", "etf", "stooq", "iwm.us", Decimal("0.001")),
    "VGK": Spec("VGK", "Europe", "slow", "etf", "stooq", "vgk.us", Decimal("0.001")),
    "BTCUSDT": Spec("BTCUSDT", "Bitcoin", "pulse", "crypto", "binance", "BTCUSDT", Decimal("0.0001")),
    "ETHUSDT": Spec("ETHUSDT", "Ether", "pulse", "crypto", "binance", "ETHUSDT", Decimal("0.001")),
    "SOLUSDT": Spec("SOLUSDT", "Solana", "pulse", "crypto", "binance", "SOLUSDT", Decimal("0.01")),
}


def parse_symbols(raw: str, *, sleeve: str) -> list[Spec]:
    out: list[Spec] = []
    for token in raw.split(","):
        key = token.strip().upper()
        if not key:
            continue
        spec = CATALOG.get(key)
        if spec is None:
            raise ValueError(f"unknown symbol {key}")
        if spec.sleeve != sleeve:
            raise ValueError(f"{key} does not belong on the {sleeve} sleeve")
        out.append(spec)
    if not out:
        raise ValueError(f"need at least one {sleeve} symbol")
    return out
