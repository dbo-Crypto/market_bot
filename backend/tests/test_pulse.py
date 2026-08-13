from engine.strategy.pulse import entry_blocked, evaluate_bar, should_rearm, stop_hit


def _channel(n: int = 40, *, last_close: float, last_high: float | None = None) -> tuple[list[float], list[float], list[float]]:
    highs = [100.0 + i * 0.1 for i in range(n - 1)]
    lows = [90.0 + i * 0.1 for i in range(n - 1)]
    closes = [95.0 + i * 0.1 for i in range(n - 1)]
    highs.append(last_high if last_high is not None else last_close)
    lows.append(last_close - 2)
    closes.append(last_close)
    return highs, lows, closes


def test_enter_on_breakout():
    highs, lows, closes = _channel(last_close=130, last_high=131)
    signal = evaluate_bar(highs, lows, closes)
    assert signal.action == "enter"
    assert signal.stop is not None
    assert signal.stop < 130


def test_skip_inside_channel():
    highs, lows, closes = _channel(last_close=96)
    signal = evaluate_bar(highs, lows, closes)
    assert signal.action == "skip"


def test_exit_on_channel_low():
    highs, lows, closes = _channel(last_close=80)
    signal = evaluate_bar(highs, lows, closes, open_stop=70.0, has_position=True)
    assert signal.action == "exit"


def test_trail_raises_stop():
    highs, lows, closes = _channel(last_close=120)
    signal = evaluate_bar(highs, lows, closes, open_stop=80.0, has_position=True)
    assert signal.action in {"trail", "hold"}
    assert signal.stop is not None
    assert signal.stop >= 80.0


def test_intrabar_stop():
    assert stop_hit(99.0, 100.0)
    assert not stop_hit(101.0, 100.0)
    assert not stop_hit(101.0, None)


def test_rearm_only_inside_channel():
    assert should_rearm(100.0, 110.0)
    assert not should_rearm(120.0, 110.0)
    assert not should_rearm(100.0, None)


def test_no_chase_after_stop():
    assert entry_blocked(armed=False, live=130, channel_high=120, stop=125) is not None
    assert entry_blocked(armed=True, live=120, channel_high=128, stop=118) is not None
    assert entry_blocked(armed=True, live=110, channel_high=120, stop=112) is not None
    assert entry_blocked(armed=True, live=130, channel_high=120, stop=118) is None
