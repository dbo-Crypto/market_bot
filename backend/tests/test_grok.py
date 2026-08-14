from app.grok import ALLOWED_KEYS, empty_review, format_briefing, parse_cache


def test_empty_review_without_key():
    out = empty_review(available=False, error="missing")
    assert out["available"] is False
    assert out["review"] is None


def test_parse_cache_roundtrip():
    raw = '{"model":"grok-4.6","generated_at":"2026-08-14T00:00:00+00:00","review":{"headline":"ok"},"error":null}'
    out = parse_cache(raw, available=True)
    assert out["review"]["headline"] == "ok"
    assert parse_cache("not-json", available=True)["review"] is None


def test_briefing_lists_the_book():
    text = format_briefing(
        {
            "account": {"cash": 200, "equity": 998, "mtm": 798, "realized_pnl": 0, "bankroll_start": 1000},
            "settings": {"slow_sleeve_fraction": "0.8"},
            "summary": {"trades": 0, "wins": 0, "losses": 0, "win_rate": None, "pnl": 0, "expectancy": None},
            "completed_trades": [],
            "open_positions": [{"sleeve": "slow", "symbol": "SPY", "qty": 1.026, "avg_price": 779.35, "mark": 777.88}],
            "recent_decisions": [],
        }
    )
    assert "Market Bot" in text
    assert "SPY" in text
    assert "HOW TO USE THIS FILE" in text


def test_unknown_knobs_are_dropped():
    recs = [
        {"key": "pulse_stop_atr", "current": "2.5", "suggested": "3.0", "why": "stops", "confidence": "low"},
        {"key": "broker", "current": "", "suggested": "live", "why": "no", "confidence": "high"},
    ]
    kept = [item for item in recs if item["key"] in ALLOWED_KEYS]
    assert {item["key"] for item in kept} == {"pulse_stop_atr"}
