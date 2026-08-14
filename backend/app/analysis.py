from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

ANALYSIS_WINDOW = 2000
FLAT = 0.50


def classify(pnl: float) -> str:
    if pnl > FLAT:
        return "win"
    if pnl < -FLAT:
        return "loss"
    return "flat"


def _aware(stamp: datetime | None) -> datetime | None:
    if stamp is None:
        return None
    if stamp.tzinfo is None:
        return stamp.replace(tzinfo=timezone.utc)
    return stamp


def hold_hours(opened_at: datetime | None, closed_at: datetime | None) -> float | None:
    start = _aware(opened_at)
    end = _aware(closed_at)
    if start is None or end is None:
        return None
    return max(0.0, (end - start).total_seconds() / 3600.0)


def _group_stats(rows: list[dict]) -> dict:
    wins = [row["realized_pnl"] for row in rows if row["result"] == "win"]
    losses = [row["realized_pnl"] for row in rows if row["result"] == "loss"]
    flats = [row for row in rows if row["result"] == "flat"]
    total = sum(row["realized_pnl"] for row in rows)
    n = len(rows)
    win_n = len(wins)
    loss_n = len(losses)
    denom = abs(sum(losses)) if losses else 0.0
    return {
        "trades": n,
        "wins": win_n,
        "losses": loss_n,
        "flats": len(flats),
        "win_rate": (win_n / (win_n + loss_n)) if (win_n + loss_n) else None,
        "pnl": total,
        "avg_win": (sum(wins) / win_n) if win_n else None,
        "avg_loss": (sum(losses) / loss_n) if loss_n else None,
        "expectancy": (total / n) if n else None,
        "profit_factor": (sum(wins) / denom) if denom > 0 else None,
    }


def _breakdown(rows: list[dict], key: str) -> list[dict]:
    buckets: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        buckets[str(row.get(key) or "unknown")].append(row)
    out = []
    for name, group in buckets.items():
        stats = _group_stats(group)
        stats["key"] = name
        out.append(stats)
    out.sort(key=lambda item: abs(item["pnl"]), reverse=True)
    return out


def strategy_notes(rows: list[dict]) -> list[str]:
    if len(rows) < 5:
        return [
            f"Only {len(rows)} completed trades in the window. Need 5 before changing knobs.",
            "The slow sleeve should trade about once a month. Snap and Pulse will fill this tape first.",
        ]
    notes: list[str] = []
    by_sleeve = {item["key"]: item for item in _breakdown(rows, "sleeve")}
    pulse = by_sleeve.get("pulse")
    snap = by_sleeve.get("snap")
    slow = by_sleeve.get("slow")
    total = sum(row["realized_pnl"] for row in rows)
    if snap and abs(snap["pnl"]) > abs(total) * 0.5 and snap["trades"] >= 5:
        notes.append(
            "Snap is driving a lot of realized P&L. That sleeve is 8% of the book — do not retune Slow because QQQ bounced."
        )
    if pulse and abs(pulse["pnl"]) > abs(total) * 0.7 and pulse["trades"] >= 5:
        notes.append(
            "Pulse is driving almost all realized P&L. That sleeve is 12% of the book on purpose — "
            "do not retune Slow because a Bitcoin breakout felt exciting."
        )
    if pulse and pulse["losses"] >= 4 and (pulse["win_rate"] or 0) < 0.35:
        notes.append(
            "Pulse is losing often. Trend breakouts are supposed to have a low hit rate and fat winners. "
            "Only worry if average loss exceeds the 1% risk cap."
        )
    if slow and slow["trades"] >= 3 and slow["pnl"] < 0:
        notes.append(
            "Slow lost money over a few monthly trades. Dual momentum has long flat or ugly years. "
            "Do not add more ETFs to 'fix' three data points."
        )
    exits = _breakdown(rows, "exit_reason")
    stop_rows = next((item for item in exits if item["key"] == "stop"), None)
    if stop_rows and stop_rows["trades"] >= 5 and (stop_rows["pnl"] or 0) < 0:
        notes.append("Most Pulse pain is the ATR stop. That is the point — cut the loser, let the trail work.")
    if not notes:
        notes.append("Sample is large enough to look at, not large enough to reinvent the rules. Leave the knobs.")
    return notes


def analyze_trades(rows: list[dict], *, window: int | None = None) -> dict:
    ordered = list(rows)
    if window is not None:
        ordered = ordered[:window]
    return {
        "window": len(ordered),
        "scope": "all",
        "analyzed": len(ordered),
        "summary": _group_stats(ordered),
        "by_sleeve": _breakdown(ordered, "sleeve"),
        "by_symbol": _breakdown(ordered, "symbol"),
        "by_exit": _breakdown(ordered, "exit_reason"),
        "notes": strategy_notes(ordered),
        "trades": ordered,
    }
