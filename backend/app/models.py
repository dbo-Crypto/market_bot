from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cash: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("1000"))
    equity: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("1000"))
    bankroll_start: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("1000"))
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0"))
    day_start_equity: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("1000"))
    day_anchor: Mapped[date] = mapped_column(Date, default=date.today)
    worker_state: Mapped[str] = mapped_column(String(16), default="running")
    killed: Mapped[bool] = mapped_column(Boolean, default=False)
    halted: Mapped[bool] = mapped_column(Boolean, default=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text)


class Instrument(Base):
    __tablename__ = "instruments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    sleeve: Mapped[str] = mapped_column(String(16), index=True)
    kind: Mapped[str] = mapped_column(String(16))
    venue: Mapped[str] = mapped_column(String(16))
    feed_symbol: Mapped[str] = mapped_column(String(32))
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    lot_size: Mapped[Decimal] = mapped_column(Numeric(18, 8), default=Decimal("0.0001"))
    last_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    last_quote_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_bar_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_history_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    features: Mapped[dict] = mapped_column(JSONB, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    bars: Mapped[list[Bar]] = relationship(back_populates="instrument", cascade="all, delete-orphan")


class Bar(Base):
    __tablename__ = "bars"
    __table_args__ = (UniqueConstraint("instrument_id", "timeframe", "ts"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"), index=True)
    timeframe: Mapped[str] = mapped_column(String(8), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    open: Mapped[Decimal] = mapped_column(Numeric(18, 8))
    high: Mapped[Decimal] = mapped_column(Numeric(18, 8))
    low: Mapped[Decimal] = mapped_column(Numeric(18, 8))
    close: Mapped[Decimal] = mapped_column(Numeric(18, 8))
    volume: Mapped[Decimal] = mapped_column(Numeric(24, 8), default=Decimal("0"))

    instrument: Mapped[Instrument] = relationship(back_populates="bars")


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"), index=True)
    sleeve: Mapped[str] = mapped_column(String(16), index=True)
    side: Mapped[str] = mapped_column(String(8), default="long")
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 8), default=Decimal("0"))
    avg_price: Mapped[Decimal] = mapped_column(Numeric(18, 8), default=Decimal("0"))
    stop_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    fees: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0"))
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0"))
    status: Mapped[str] = mapped_column(String(16), default="open")
    exit_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    instrument: Mapped[Instrument] = relationship()


class Fill(Base):
    __tablename__ = "fills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"), index=True)
    position_id: Mapped[int | None] = mapped_column(ForeignKey("positions.id"), nullable=True)
    sleeve: Mapped[str] = mapped_column(String(16), default="slow")
    side: Mapped[str] = mapped_column(String(8))
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 8))
    price: Mapped[Decimal] = mapped_column(Numeric(18, 8))
    fee: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    reason: Mapped[str] = mapped_column(String(64), default="")
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    instrument: Mapped[Instrument] = relationship()


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instrument_id: Mapped[int | None] = mapped_column(ForeignKey("instruments.id"), nullable=True)
    sleeve: Mapped[str] = mapped_column(String(16), default="slow")
    action: Mapped[str] = mapped_column(String(16))
    price: Mapped[float | None] = mapped_column(nullable=True)
    qty: Mapped[float] = mapped_column(default=0)
    score: Mapped[float | None] = mapped_column(nullable=True)
    reason: Mapped[str] = mapped_column(Text)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    instrument: Mapped[Instrument | None] = relationship()


class EquityPoint(Base):
    __tablename__ = "equity_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    equity: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    cash: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    mtm: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    daily_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 6))


class Cooldown(Base):
    __tablename__ = "cooldowns"

    symbol: Mapped[str] = mapped_column(String(24), primary_key=True)
    last_exit_bar_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_handled_bar_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    armed: Mapped[bool] = mapped_column(Boolean, default=True)
