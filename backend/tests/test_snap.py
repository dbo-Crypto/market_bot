from engine.strategy.indicators import rsi
from engine.strategy.snap import evaluate_snap


def _trend(n: int = 220, last: float = 100.0, dump: float = 0.0) -> tuple[list[float], list[float], list[float]]:
    closes = [80.0 + i * 0.1 for i in range(n - 1)]
    closes.append(last - dump)
    highs = [c + 1 for c in closes]
    lows = [c - 1 for c in closes]
    return closes, highs, lows


def test_rsi_washes_out_after_a_dump():
    closes = [100.0, 99.0, 90.0]
    value = rsi(closes, 2)
    assert value is not None
    assert value < 10


def test_enter_on_washout_in_uptrend():
    closes, highs, lows = _trend(last=100.0, dump=8.0)
    # force last two changes to be large down days
    closes[-3] = 108.0
    closes[-2] = 104.0
    closes[-1] = 96.0
    highs[-1] = 97.0
    lows[-1] = 95.0
    signal = evaluate_snap(closes, highs, lows)
    assert signal.action == "enter"
    assert signal.stop is not None
    assert signal.stop < closes[-1]


def test_no_entry_below_200dma():
    closes, highs, lows = _trend(last=50.0)
    closes[-1] = 50.0
    signal = evaluate_snap(closes, highs, lows)
    assert signal.action == "skip"
    assert "200-day" in signal.reason


def test_exit_on_sma5_or_time():
    closes, highs, lows = _trend(last=110.0)
    signal = evaluate_snap(closes, highs, lows, has_position=True, open_stop=80.0, days_held=1)
    assert signal.action == "exit"
    timed = evaluate_snap(closes, highs, lows, has_position=True, open_stop=80.0, days_held=5, sma_exit=200)
    # with sma_exit=200, a 110 close in an uptrend is above the 200dma so still an sma exit.
    # force a hold by putting sma_exit very high via a falling last print still above stop
    hold_closes = list(closes)
    hold_closes[-1] = 90.0
    hold_highs = [c + 1 for c in hold_closes]
    hold_lows = [c - 1 for c in hold_closes]
    hold = evaluate_snap(
        hold_closes,
        hold_highs,
        hold_lows,
        has_position=True,
        open_stop=80.0,
        days_held=2,
        sma_exit=5,
    )
    assert hold.action in {"hold", "exit"}
    time_exit = evaluate_snap(
        hold_closes,
        hold_highs,
        hold_lows,
        has_position=True,
        open_stop=80.0,
        days_held=5,
        sma_exit=5,
    )
    assert time_exit.action == "exit"
    assert "time" in time_exit.reason or "average" in time_exit.reason
