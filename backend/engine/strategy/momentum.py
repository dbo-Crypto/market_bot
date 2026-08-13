from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MomentumScore:
    symbol: str
    price: float
    ret_12_1: float | None
    sma: float | None
    above_sma: bool
    eligible: bool
    reason: str


def score_closes(
    symbol: str,
    closes: list[float],
    *,
    lookback: int = 252,
    skip: int = 21,
    sma_len: int = 210,
) -> MomentumScore:
    """12-1 momentum with a 10-month SMA absolute filter.

    12-1 = return from `lookback` bars ago to `skip` bars ago.
    Eligible only if last close is above the SMA.
    """
    from engine.strategy.indicators import roc, sma as sma_fn

    if not closes:
        return MomentumScore(symbol, 0.0, None, None, False, False, "no prices")
    price = closes[-1]
    mean = sma_fn(closes, sma_len)
    ret = roc(closes, lookback, skip)
    if mean is None:
        return MomentumScore(symbol, price, ret, None, False, False, f"need {sma_len} daily bars")
    if ret is None:
        return MomentumScore(symbol, price, None, mean, price > mean, False, f"need {lookback + 1} daily bars")
    above = price > mean
    if not above:
        return MomentumScore(symbol, price, ret, mean, False, False, "below 10-month average")
    return MomentumScore(symbol, price, ret, mean, True, True, "above average, ranked")


def pick_winner(scores: list[MomentumScore]) -> MomentumScore | None:
    eligible = [row for row in scores if row.eligible and row.ret_12_1 is not None]
    if not eligible:
        return None
    return max(eligible, key=lambda row: row.ret_12_1 or -999.0)
