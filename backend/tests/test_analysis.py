from app.analysis import analyze_trades, classify, strategy_notes


def test_classify():
    assert classify(12) == "win"
    assert classify(-3) == "loss"
    assert classify(0.1) == "flat"


def test_refuses_to_retune_small_sample():
    notes = strategy_notes([{"realized_pnl": 1, "sleeve": "pulse", "exit_reason": "stop", "result": "win"}])
    assert any("5" in note for note in notes)


def test_pulse_dominance_note():
    rows = [
        {"realized_pnl": 40, "sleeve": "pulse", "exit_reason": "trail", "result": "win"}
        for _ in range(6)
    ] + [{"realized_pnl": 1, "sleeve": "slow", "exit_reason": "rebalance", "result": "win"}]
    for row in rows:
        row.setdefault("symbol", "X")
    notes = strategy_notes(rows)
    assert any("Pulse is driving" in note for note in notes)


def test_analyze_shape():
    rows = [
        {
            "realized_pnl": 10,
            "sleeve": "slow",
            "symbol": "SPY",
            "exit_reason": "rebalance",
            "result": "win",
        }
        for _ in range(6)
    ]
    out = analyze_trades(rows)
    assert out["analyzed"] == 6
    assert out["summary"]["wins"] == 6
    assert out["by_sleeve"]
