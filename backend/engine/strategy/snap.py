from __future__ import annotations

from dataclasses import dataclass

from engine.strategy.indicators import atr, rsi, sma


@dataclass(frozen=True, slots=True)
class SnapSignal:
    action: str
    stop: float | None
    rsi: float | None
    sma_long: float | None
    sma_exit: float | None
    atr: float | None
    reason: str


def _skip(reason: str, **extra) -> SnapSignal:
    return SnapSignal(
        "skip",
        extra.get("stop"),
        extra.get("rsi"),
        extra.get("sma_long"),
        extra.get("sma_exit"),
        extra.get("atr"),
        reason,
    )


def evaluate_snap(
    closes: list[float],
    highs: list[float],
    lows: list[float],
    *,
    rsi_len: int = 2,
    rsi_buy: float = 10.0,
    sma_filter: int = 200,
    sma_exit: int = 5,
    atr_len: int = 20,
    stop_atr: float = 2.5,
    max_days: int = 5,
    days_held: int = 0,
    open_stop: float | None = None,
    has_position: bool = False,
) -> SnapSignal:
    """Aggressive QQQ fade: buy a 2-day washout only in a long uptrend.

    Enter when RSI(2) is washed out and price is still above the 200-day average.
    Exit when price reclaims the 5-day average, after `max_days` sessions,
    or if live/close hits the ATR stop.
    """
    need = max(sma_filter, atr_len, sma_exit, rsi_len) + 2
    if len(closes) < need:
        return _skip(f"need {need} daily bars")
    close = closes[-1]
    r = rsi(closes, rsi_len)
    long_ma = sma(closes, sma_filter)
    exit_ma = sma(closes, sma_exit)
    vol = atr(highs, lows, closes, atr_len)
    if r is None or long_ma is None or exit_ma is None or vol is None or vol <= 0:
        return _skip("indicators not ready")

    if has_position:
        stop = open_stop if open_stop is not None else close - stop_atr * vol
        if close <= stop:
            return SnapSignal("exit", stop, r, long_ma, exit_ma, vol, f"stop {stop:.2f} hit on close")
        if close > exit_ma:
            return SnapSignal("exit", stop, r, long_ma, exit_ma, vol, f"reclaimed {sma_exit}-day average {exit_ma:.2f}")
        if days_held >= max_days:
            return SnapSignal("exit", stop, r, long_ma, exit_ma, vol, f"time stop after {days_held} sessions")
        return SnapSignal("hold", stop, r, long_ma, exit_ma, vol, f"holding bounce, RSI {r:.0f}")

    if close <= long_ma:
        return _skip("below 200-day average — no knife-catching", rsi=r, sma_long=long_ma, sma_exit=exit_ma, atr=vol)
    if r > rsi_buy:
        return _skip(f"RSI({rsi_len}) {r:.0f} not washed out (need ≤ {rsi_buy:.0f})", rsi=r, sma_long=long_ma, sma_exit=exit_ma, atr=vol)
    stop = close - stop_atr * vol
    return SnapSignal(
        "enter",
        stop,
        r,
        long_ma,
        exit_ma,
        vol,
        f"RSI({rsi_len}) {r:.0f} washout above the 200-day average",
    )
