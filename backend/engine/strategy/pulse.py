from __future__ import annotations

from dataclasses import dataclass

from engine.strategy.indicators import atr, donchian_high, donchian_low


@dataclass(frozen=True, slots=True)
class PulseSignal:
    action: str
    stop: float | None
    atr: float | None
    channel_high: float | None
    channel_low: float | None
    reason: str


def _empty(reason: str) -> PulseSignal:
    return PulseSignal("skip", None, None, None, None, reason)


def evaluate_bar(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    *,
    donchian: int = 20,
    exit_channel: int = 10,
    atr_len: int = 14,
    stop_atr: float = 2.5,
    trail_atr: float = 3.0,
    open_stop: float | None = None,
    has_position: bool = False,
) -> PulseSignal:
    """Long-only 4h Donchian breakout with ATR stop / trail.

    Entry: just-closed bar closes above the prior `donchian` highs.
    Exit: last close under the prior `exit_channel` lows, or price at/under stop.
    Trail: stop ratchets to close − trail_atr × ATR, never down.
    """
    if len(closes) < max(donchian, exit_channel, atr_len) + 2:
        return _empty("not enough 4h bars")
    close = closes[-1]
    vol = atr(highs, lows, closes, atr_len)
    hi = donchian_high(highs, donchian)
    lo = donchian_low(lows, exit_channel)
    if vol is None or vol <= 0:
        return _empty("ATR not ready")

    if has_position:
        stop = open_stop if open_stop is not None else close - stop_atr * vol
        trailed = max(stop, close - trail_atr * vol)
        if close <= trailed:
            return PulseSignal("exit", trailed, vol, hi, lo, f"stop {trailed:.2f} hit on close")
        if lo is not None and close < lo:
            return PulseSignal("exit", trailed, vol, hi, lo, f"close under {exit_channel}-bar low {lo:.2f}")
        if trailed > (open_stop or 0) + 1e-9:
            return PulseSignal("trail", trailed, vol, hi, lo, f"trail stop → {trailed:.2f}")
        return PulseSignal("hold", trailed, vol, hi, lo, "in trade, stop intact")

    if hi is None:
        return _empty("Donchian not ready")
    if close > hi:
        stop = close - stop_atr * vol
        return PulseSignal(
            "enter",
            stop,
            vol,
            hi,
            lo,
            f"4h close {close:.2f} broke {donchian}-bar high {hi:.2f}",
        )
    return PulseSignal("skip", None, vol, hi, lo, f"close {close:.2f} inside channel {hi:.2f}")


def stop_hit(last: float, stop: float | None) -> bool:
    return stop is not None and last > 0 and last <= stop


def should_rearm(close: float, channel_high: float | None) -> bool:
    """After a stop, wait until a closed bar is back inside the channel."""
    if channel_high is None:
        return False
    return close <= channel_high


def entry_blocked(
    *,
    armed: bool,
    live: float,
    channel_high: float | None,
    stop: float | None,
) -> str | None:
    if not armed:
        return "disarmed — wait for a 4h close back inside the channel"
    if stop is not None and live <= stop:
        return "live price already through the stop"
    if channel_high is not None and live <= channel_high:
        return "live price back inside the channel"
    return None
