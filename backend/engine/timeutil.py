from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")


def as_utc(stamp: datetime) -> datetime:
    if stamp.tzinfo is None:
        return stamp.replace(tzinfo=timezone.utc)
    return stamp.astimezone(timezone.utc)


def ny_date(now: datetime | None = None) -> datetime:
    stamp = as_utc(now or datetime.now(timezone.utc))
    return stamp.astimezone(NY)


def last_closed_4h(now: datetime) -> datetime:
    stamp = as_utc(now).replace(minute=0, second=0, microsecond=0)
    hour = (stamp.hour // 4) * 4
    current_open = stamp.replace(hour=hour)
    return current_open - timedelta(hours=4)


def is_forming_daily(bar_ts: datetime, now: datetime) -> bool:
    """True if this daily bar is still the in-progress US cash session.

    Stooq/Yahoo daily stamps are the trading date at 00:00 UTC. The cash
    session is treated as closed from 16:05 America/New_York.
    """
    ny_now = ny_date(now)
    bar_day = as_utc(bar_ts).date()
    session = ny_now.date()
    if bar_day > session:
        return True
    if bar_day < session:
        return False
    closed = ny_now.hour > 16 or (ny_now.hour == 16 and ny_now.minute >= 5)
    return not closed
