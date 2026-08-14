from app.grok import ALLOWED_KEYS, empty_review, parse_cache


def test_empty_review_without_key():
    out = empty_review(available=False, error="missing")
    assert out["available"] is False
    assert out["review"] is None


def test_parse_cache_roundtrip():
    raw = '{"model":"grok-4.6","generated_at":"2026-08-14T00:00:00+00:00","review":{"headline":"ok"},"error":null}'
    out = parse_cache(raw, available=True)
    assert out["review"]["headline"] == "ok"
    assert parse_cache("not-json", available=True)["review"] is None


def test_unknown_knobs_are_dropped():
    recs = [
        {"key": "pulse_stop_atr", "current": "2.5", "suggested": "3.0", "why": "stops", "confidence": "low"},
        {"key": "broker", "current": "", "suggested": "live", "why": "no", "confidence": "high"},
    ]
    kept = [item for item in recs if item["key"] in ALLOWED_KEYS]
    assert {item["key"] for item in kept} == {"pulse_stop_atr"}
