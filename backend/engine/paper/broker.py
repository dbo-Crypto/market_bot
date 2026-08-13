from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN


def _dec(value: object, default: str = "0") -> Decimal:
    if value is None:
        return Decimal(default)
    return Decimal(str(value))


def round_qty(qty: Decimal, lot: Decimal) -> Decimal:
    if lot <= 0:
        return qty
    steps = (qty / lot).to_integral_value(rounding=ROUND_DOWN)
    return steps * lot


def fill_price(last: Decimal, side: str, slip_bps: Decimal) -> Decimal:
    slip = last * slip_bps / Decimal("10000")
    if side == "buy":
        return last + slip
    return max(last - slip, Decimal("0.00000001"))


def commission(notional: Decimal, fee_bps: Decimal) -> Decimal:
    return abs(notional) * fee_bps / Decimal("10000")


@dataclass(frozen=True, slots=True)
class PaperFill:
    side: str
    qty: Decimal
    price: Decimal
    fee: Decimal
    reason: str

    @property
    def notional(self) -> Decimal:
        return self.price * self.qty


def plan_buy(
    last: Decimal,
    qty: Decimal,
    lot: Decimal,
    *,
    cash: Decimal,
    slip_bps: Decimal,
    fee_bps: Decimal,
    min_notional: Decimal,
    reason: str,
) -> PaperFill | None:
    qty = round_qty(qty, lot)
    if qty <= 0:
        return None
    price = fill_price(last, "buy", slip_bps)
    fee = commission(price * qty, fee_bps)
    cost = price * qty + fee
    if cost > cash:
        affordable = (cash / (price * (Decimal("1") + fee_bps / Decimal("10000"))))
        qty = round_qty(affordable, lot)
        if qty <= 0:
            return None
        price = fill_price(last, "buy", slip_bps)
        fee = commission(price * qty, fee_bps)
        cost = price * qty + fee
        if cost > cash:
            return None
    if price * qty < min_notional:
        return None
    return PaperFill("buy", qty, price, fee, reason)


def plan_sell(
    last: Decimal,
    qty: Decimal,
    lot: Decimal,
    *,
    slip_bps: Decimal,
    fee_bps: Decimal,
    reason: str,
) -> PaperFill | None:
    qty = round_qty(qty, lot)
    if qty <= 0:
        return None
    price = fill_price(last, "sell", slip_bps)
    fee = commission(price * qty, fee_bps)
    return PaperFill("sell", qty, price, fee, reason)


def realized_pnl(
    *,
    avg_price: Decimal,
    qty: Decimal,
    sell_price: Decimal,
    sell_fee: Decimal,
    buy_fees: Decimal,
) -> Decimal:
    """Full-exit P&L: price move minus this sell fee minus buy fees still on the lot."""
    return (sell_price - avg_price) * qty - sell_fee - buy_fees


def pulse_qty(
    equity: Decimal,
    last: Decimal,
    atr_value: float,
    stop_atr: float,
    *,
    risk_fraction: Decimal,
    lot: Decimal,
    sleeve_budget: Decimal,
) -> Decimal:
    if last <= 0 or atr_value <= 0 or stop_atr <= 0:
        return Decimal("0")
    risk = equity * risk_fraction
    stop_dist = _dec(atr_value) * _dec(stop_atr)
    if stop_dist <= 0:
        return Decimal("0")
    raw = risk / stop_dist
    cap = sleeve_budget / last if last else Decimal("0")
    return round_qty(min(raw, cap), lot)
