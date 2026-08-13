from engine.strategy.momentum import pick_winner, score_closes


def _series(*, last: float, old: float, mid: float, body: float) -> list[float]:
    bars = [old] * 231 + [mid] * 21 + [last]
    assert len(bars) == 253
    for i in range(1, 231):
        bars[i] = body
    bars[0] = old
    bars[-22] = mid
    bars[-1] = last
    return bars


KW = {"lookback": 252, "skip": 21, "sma_len": 5}


def test_eligible_when_above_sma_and_ranked():
    closes = _series(last=120, old=80, mid=110, body=100)
    score = score_closes("SPY", closes, **KW)
    assert score.above_sma
    assert score.eligible
    assert score.ret_12_1 is not None
    assert abs(score.ret_12_1 - (110 / 80 - 1)) < 1e-9


def test_not_eligible_below_sma():
    closes = _series(last=70, old=80, mid=95, body=100)
    score = score_closes("EZU", closes, **KW)
    assert not score.above_sma
    assert not score.eligible


def test_needs_history():
    score = score_closes("SPY", [100.0] * 50)
    assert not score.eligible
    assert "bars" in score.reason


def test_pick_stronger_of_two():
    strong = score_closes("SPY", _series(last=130, old=70, mid=120, body=100), **KW)
    weak = score_closes("EZU", _series(last=105, old=95, mid=102, body=100), **KW)
    winner = pick_winner([strong, weak])
    assert winner is not None
    assert winner.symbol == "SPY"


def test_cash_when_none_eligible():
    a = score_closes("SPY", _series(last=70, old=110, mid=95, body=100), **KW)
    b = score_closes("EZU", _series(last=72, old=120, mid=92, body=100), **KW)
    assert pick_winner([a, b]) is None
