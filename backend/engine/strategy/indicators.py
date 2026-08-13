from __future__ import annotations


def rsi(values: list[float], length: int) -> float | None:
    """Simple RSI. length=2 is the Connors-style washout gauge."""
    if length <= 0 or len(values) < length + 1:
        return None
    gains = 0.0
    losses = 0.0
    for i in range(-length, 0):
        change = values[i] - values[i - 1]
        if change >= 0:
            gains += change
        else:
            losses -= change
    avg_gain = gains / length
    avg_loss = losses / length
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def sma(values: list[float], length: int) -> float | None:
    if length <= 0 or len(values) < length:
        return None
    window = values[-length:]
    return sum(window) / length


def roc(values: list[float], start: int, end: int) -> float | None:
    """Return from `start` bars ago to `end` bars ago. Latest bar is index -1."""
    if start <= end or len(values) < start + 1:
        return None
    older = values[-(start + 1)]
    newer = values[-(end + 1)]
    if older <= 0:
        return None
    return newer / older - 1.0


def true_ranges(highs: list[float], lows: list[float], closes: list[float]) -> list[float]:
    out: list[float] = []
    prev = closes[0] if closes else 0.0
    for high, low, close in zip(highs, lows, closes):
        tr = max(high - low, abs(high - prev), abs(low - prev))
        out.append(tr)
        prev = close
    return out


def atr(highs: list[float], lows: list[float], closes: list[float], length: int) -> float | None:
    if length <= 0 or len(closes) < length + 1:
        return None
    ranges = true_ranges(highs, lows, closes)
    window = ranges[-length:]
    return sum(window) / length


def donchian_high(highs: list[float], length: int, *, exclude_last: bool = True) -> float | None:
    if length <= 0:
        return None
    series = highs[:-1] if exclude_last else highs
    if len(series) < length:
        return None
    return max(series[-length:])


def donchian_low(lows: list[float], length: int, *, exclude_last: bool = True) -> float | None:
    if length <= 0:
        return None
    series = lows[:-1] if exclude_last else lows
    if len(series) < length:
        return None
    return min(series[-length:])
