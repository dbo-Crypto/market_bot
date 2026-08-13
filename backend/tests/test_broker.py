from decimal import Decimal

from engine.paper.broker import commission, fill_price, plan_buy, plan_sell, pulse_qty, realized_pnl, round_qty


def test_buy_pays_slip_and_fee():
    fill = plan_buy(
        Decimal("100"),
        Decimal("10"),
        Decimal("0.001"),
        cash=Decimal("2000"),
        slip_bps=Decimal("2"),
        fee_bps=Decimal("5"),
        min_notional=Decimal("15"),
        reason="test",
    )
    assert fill is not None
    assert fill.price == Decimal("100.02")
    assert fill.fee == Decimal("0.5001")
    assert fill.notional + fill.fee < Decimal("2000")


def test_buy_shrinks_to_cash():
    fill = plan_buy(
        Decimal("100"),
        Decimal("100"),
        Decimal("1"),
        cash=Decimal("250"),
        slip_bps=Decimal("0"),
        fee_bps=Decimal("0"),
        min_notional=Decimal("15"),
        reason="test",
    )
    assert fill is not None
    assert fill.qty == Decimal("2")


def test_sell_haircut():
    fill = plan_sell(
        Decimal("50"),
        Decimal("3"),
        Decimal("1"),
        slip_bps=Decimal("10"),
        fee_bps=Decimal("10"),
        reason="stop",
    )
    assert fill is not None
    assert fill.price < Decimal("50")
    assert fill.fee > 0


def test_min_notional_blocks():
    fill = plan_buy(
        Decimal("10"),
        Decimal("0.5"),
        Decimal("0.1"),
        cash=Decimal("1000"),
        slip_bps=Decimal("0"),
        fee_bps=Decimal("0"),
        min_notional=Decimal("15"),
        reason="tiny",
    )
    assert fill is None


def test_pulse_qty_risk_and_sleeve_cap():
    qty = pulse_qty(
        Decimal("1000"),
        Decimal("100"),
        4.0,
        2.5,
        risk_fraction=Decimal("0.01"),
        lot=Decimal("0.001"),
        sleeve_budget=Decimal("120"),
    )
    # risk $10 / $10 stop = 1 unit, sleeve cap 1.2 → 1
    assert qty == Decimal("1.000")
    assert round_qty(Decimal("1.2345"), Decimal("0.001")) == Decimal("1.234")
    assert commission(Decimal("1000"), Decimal("10")) == Decimal("1")
    assert fill_price(Decimal("100"), "buy", Decimal("10")) == Decimal("100.10")


def test_realized_includes_buy_fees():
    pnl = realized_pnl(
        avg_price=Decimal("100"),
        qty=Decimal("10"),
        sell_price=Decimal("110"),
        sell_fee=Decimal("1"),
        buy_fees=Decimal("2"),
    )
    assert pnl == Decimal("97")
