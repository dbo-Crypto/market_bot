from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings
from app.models import Account, Base, Instrument, Setting
from engine.universe import parse_symbols

engine = None
SessionLocal: async_sessionmaker[AsyncSession] | None = None

DEFAULT_KEYS = (
    "slow_symbols",
    "slow_sleeve_fraction",
    "slow_lookback",
    "slow_skip",
    "slow_sma",
    "snap_symbols",
    "snap_sleeve_fraction",
    "snap_rsi",
    "snap_rsi_buy",
    "snap_sma_filter",
    "snap_sma_exit",
    "snap_max_days",
    "snap_atr",
    "snap_stop_atr",
    "snap_risk_fraction",
    "pulse_symbols",
    "pulse_sleeve_fraction",
    "pulse_risk_fraction",
    "pulse_donchian",
    "pulse_exit_channel",
    "pulse_atr",
    "pulse_stop_atr",
    "pulse_trail_atr",
    "daily_loss_halt",
    "poll_interval_seconds",
    "etf_refresh_seconds",
    "crypto_bar_seconds",
    "slow_fee_bps",
    "slow_slip_bps",
    "pulse_fee_bps",
    "pulse_slip_bps",
    "min_trade_notional",
    "last_slow_month",
)


def init_engine(settings: Settings) -> None:
    global engine, SessionLocal
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    if SessionLocal is None:
        raise RuntimeError("Database is not initialized")
    async with SessionLocal() as session:
        yield session


async def seed_instruments(session: AsyncSession, settings: Settings) -> None:
    from sqlalchemy import select

    specs = []
    specs.extend(parse_symbols(settings.slow_symbols, sleeve="slow"))
    specs.extend(parse_symbols(settings.snap_symbols, sleeve="snap"))
    specs.extend(parse_symbols(settings.pulse_symbols, sleeve="pulse"))
    for spec in specs:
        row = (await session.execute(select(Instrument).where(Instrument.symbol == spec.symbol))).scalar_one_or_none()
        if row is None:
            session.add(
                Instrument(
                    symbol=spec.symbol,
                    name=spec.name,
                    sleeve=spec.sleeve,
                    kind=spec.kind,
                    venue=spec.venue,
                    feed_symbol=spec.feed_symbol,
                    lot_size=spec.lot_size,
                    features={},
                )
            )
        else:
            row.name = spec.name
            row.sleeve = spec.sleeve
            row.kind = spec.kind
            row.venue = spec.venue
            row.feed_symbol = spec.feed_symbol
            row.lot_size = spec.lot_size


async def init_db(settings: Settings) -> None:
    assert engine is not None
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("ALTER TABLE instruments ADD COLUMN IF NOT EXISTS last_history_at TIMESTAMPTZ"))
        await conn.execute(text("ALTER TABLE cooldowns ADD COLUMN IF NOT EXISTS last_handled_bar_at TIMESTAMPTZ"))
        await conn.execute(text("ALTER TABLE cooldowns ADD COLUMN IF NOT EXISTS armed BOOLEAN NOT NULL DEFAULT TRUE"))

    async with SessionLocal() as session:
        account = await session.get(Account, 1)
        if account is None:
            bankroll = Decimal(str(settings.paper_bankroll))
            session.add(
                Account(
                    id=1,
                    cash=bankroll,
                    equity=bankroll,
                    bankroll_start=bankroll,
                    day_start_equity=bankroll,
                    day_anchor=date.today(),
                    worker_state="running",
                )
            )
        defaults = {
            "slow_symbols": settings.slow_symbols,
            "slow_sleeve_fraction": str(settings.slow_sleeve_fraction),
            "slow_lookback": str(settings.slow_lookback),
            "slow_skip": str(settings.slow_skip),
            "slow_sma": str(settings.slow_sma),
            "snap_symbols": settings.snap_symbols,
            "snap_sleeve_fraction": str(settings.snap_sleeve_fraction),
            "snap_rsi": str(settings.snap_rsi),
            "snap_rsi_buy": str(settings.snap_rsi_buy),
            "snap_sma_filter": str(settings.snap_sma_filter),
            "snap_sma_exit": str(settings.snap_sma_exit),
            "snap_max_days": str(settings.snap_max_days),
            "snap_atr": str(settings.snap_atr),
            "snap_stop_atr": str(settings.snap_stop_atr),
            "snap_risk_fraction": str(settings.snap_risk_fraction),
            "pulse_symbols": settings.pulse_symbols,
            "pulse_sleeve_fraction": str(settings.pulse_sleeve_fraction),
            "pulse_risk_fraction": str(settings.pulse_risk_fraction),
            "pulse_donchian": str(settings.pulse_donchian),
            "pulse_exit_channel": str(settings.pulse_exit_channel),
            "pulse_atr": str(settings.pulse_atr),
            "pulse_stop_atr": str(settings.pulse_stop_atr),
            "pulse_trail_atr": str(settings.pulse_trail_atr),
            "daily_loss_halt": str(settings.daily_loss_halt),
            "poll_interval_seconds": str(settings.poll_interval_seconds),
            "etf_refresh_seconds": str(settings.etf_refresh_seconds),
            "crypto_bar_seconds": str(settings.crypto_bar_seconds),
            "slow_fee_bps": str(settings.slow_fee_bps),
            "slow_slip_bps": str(settings.slow_slip_bps),
            "pulse_fee_bps": str(settings.pulse_fee_bps),
            "pulse_slip_bps": str(settings.pulse_slip_bps),
            "min_trade_notional": str(settings.min_trade_notional),
            "last_slow_month": "",
        }
        for key, value in defaults.items():
            existing = await session.get(Setting, key)
            if existing is None:
                session.add(Setting(key=key, value=value))
        await seed_instruments(session, settings)
        await session.commit()
