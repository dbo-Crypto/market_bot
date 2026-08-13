from datetime import datetime, timezone

from engine.timeutil import is_forming_daily, last_closed_4h


def test_last_closed_4h_rolls_on_the_boundary():
    now = datetime(2026, 8, 13, 13, 10, tzinfo=timezone.utc)
    closed = last_closed_4h(now)
    assert closed == datetime(2026, 8, 13, 8, 0, tzinfo=timezone.utc)


def test_forming_daily_excludes_open_us_session():
    # 18:00 UTC = 14:00 New York in August
    now = datetime(2026, 8, 13, 18, 0, tzinfo=timezone.utc)
    today = datetime(2026, 8, 13, 0, 0, tzinfo=timezone.utc)
    yesterday = datetime(2026, 8, 12, 0, 0, tzinfo=timezone.utc)
    assert is_forming_daily(today, now)
    assert not is_forming_daily(yesterday, now)


def test_forming_daily_keeps_yesterday_after_ny_midnight():
    # 02:00 UTC Aug 13 = 22:00 New York Aug 12
    now = datetime(2026, 8, 13, 2, 0, tzinfo=timezone.utc)
    yesterday = datetime(2026, 8, 12, 0, 0, tzinfo=timezone.utc)
    assert not is_forming_daily(yesterday, now)
