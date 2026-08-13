from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.analysis import analyze_trades, classify, hold_hours
from app.models import Account, Bar, Decision, EquityPoint, Fill, Instrument, Position, Setting


def _f(value: object) -> float | None:
    if value is None:
        return None
    return float(value)


def _dec(value: object, default: str = "0") -> Decimal:
    if value is None:
        return Decimal(default)
    return Decimal(str(value))


async def load_settings(session: AsyncSession) -> dict[str, str]:
    rows = (await session.execute(select(Setting))).scalars().all()
    return {row.key: row.value for row in rows}


async def compute_equity(session: AsyncSession, account: Account) -> tuple[Decimal, Decimal]:
    positions = (
        await session.execute(
            select(Position)
            .options(selectinload(Position.instrument))
            .where(Position.status == "open")
        )
    ).scalars().all()
    mtm = Decimal("0")
    for position in positions:
        mark = position.instrument.last_price or position.avg_price
        mtm += position.qty * mark
    equity = account.cash + mtm
    return equity, mtm


def latent_pnl(position: Position) -> float:
    mark = position.instrument.last_price or position.avg_price
    return float((mark - position.avg_price) * position.qty)


def serialize_instrument(row: Instrument, *, position: Position | None = None, bars: list[float] | None = None) -> dict:
    features = row.features or {}
    mark = _f(row.last_price)
    pos = None
    if position is not None:
        pos = {
            "id": position.id,
            "qty": float(position.qty),
            "avg_price": float(position.avg_price),
            "stop": _f(position.stop_price),
            "fees": float(position.fees),
            "latent_pnl": latent_pnl(position),
            "market_value": float(position.qty * (row.last_price or position.avg_price)),
            "opened_at": position.opened_at.isoformat() if position.opened_at else None,
        }
    return {
        "id": row.id,
        "symbol": row.symbol,
        "name": row.name,
        "sleeve": row.sleeve,
        "kind": row.kind,
        "venue": row.venue,
        "currency": row.currency,
        "last": mark,
        "last_quote_at": row.last_quote_at.isoformat() if row.last_quote_at else None,
        "last_bar_at": row.last_bar_at.isoformat() if row.last_bar_at else None,
        "features": features,
        "position": pos,
        "spark": bars or [],
    }


def serialize_position(position: Position) -> dict:
    instrument = position.instrument
    mark = instrument.last_price or position.avg_price
    return {
        "id": position.id,
        "symbol": instrument.symbol,
        "name": instrument.name,
        "sleeve": position.sleeve,
        "side": position.side,
        "qty": float(position.qty),
        "avg_price": float(position.avg_price),
        "mark": float(mark),
        "stop": _f(position.stop_price),
        "market_value": float(position.qty * mark),
        "fees": float(position.fees),
        "latent_pnl": latent_pnl(position) if position.status == "open" else None,
        "realized_pnl": float(position.realized_pnl),
        "status": position.status,
        "exit_reason": position.exit_reason,
        "opened_at": position.opened_at.isoformat() if position.opened_at else None,
        "closed_at": position.closed_at.isoformat() if position.closed_at else None,
    }


def serialize_fill(fill: Fill, instrument: Instrument, position: Position | None) -> dict:
    mark = _f(instrument.last_price)
    notional = float(fill.price * fill.qty)
    if fill.side == "buy":
        pnl = None if mark is None else (mark - float(fill.price)) * float(fill.qty)
        kind = "latent"
    else:
        pnl = float(position.realized_pnl) if position and position.status != "open" else None
        kind = "realized"
    return {
        "id": fill.id,
        "symbol": instrument.symbol,
        "name": instrument.name,
        "sleeve": fill.sleeve,
        "side": fill.side,
        "qty": float(fill.qty),
        "price": float(fill.price),
        "fee": float(fill.fee),
        "notional": notional,
        "reason": fill.reason,
        "mark": mark,
        "pnl": pnl,
        "pnl_kind": kind,
        "position_status": position.status if position else None,
        "position_pnl": float(position.realized_pnl) if position else None,
        "ts": fill.ts.isoformat() if fill.ts else None,
    }


def serialize_decision(row: Decision, instrument: Instrument | None) -> dict:
    return {
        "id": row.id,
        "symbol": instrument.symbol if instrument else None,
        "name": instrument.name if instrument else "Cash",
        "sleeve": row.sleeve,
        "action": row.action,
        "price": row.price,
        "qty": row.qty,
        "score": row.score,
        "reason": row.reason,
        "ts": row.ts.isoformat() if row.ts else None,
    }


async def latest_sparks(session: AsyncSession, instrument_ids: list[int], timeframe: str, n: int = 40) -> dict[int, list[float]]:
    if not instrument_ids:
        return {}
    buckets: dict[int, list[float]] = {}
    for instrument_id in instrument_ids:
        rows = (
            await session.execute(
                select(Bar.close)
                .where(Bar.instrument_id == instrument_id, Bar.timeframe == timeframe)
                .order_by(desc(Bar.ts))
                .limit(n)
            )
        ).scalars().all()
        buckets[instrument_id] = list(reversed([float(value) for value in rows]))
    return buckets


async def load_instruments(session: AsyncSession, sleeve: str | None = None) -> list[Instrument]:
    stmt = select(Instrument).order_by(Instrument.sleeve, Instrument.symbol)
    if sleeve:
        stmt = stmt.where(Instrument.sleeve == sleeve)
    return list((await session.execute(stmt)).scalars().all())


async def open_positions_by_instrument(session: AsyncSession) -> dict[int, Position]:
    rows = (
        await session.execute(
            select(Position)
            .options(selectinload(Position.instrument))
            .where(Position.status == "open")
        )
    ).scalars().all()
    return {row.instrument_id: row for row in rows}


async def build_overview(session: AsyncSession) -> dict:
    account = await session.get(Account, 1)
    assert account is not None
    equity, mtm = await compute_equity(session, account)
    account.equity = equity
    settings = await load_settings(session)
    instruments = await load_instruments(session)
    positions = await open_positions_by_instrument(session)
    daily_ids = [row.id for row in instruments if row.sleeve in {"slow", "snap"}]
    pulse_ids = [row.id for row in instruments if row.sleeve == "pulse"]
    sparks = {}
    sparks.update(await latest_sparks(session, daily_ids, "1d"))
    sparks.update(await latest_sparks(session, pulse_ids, "4h"))

    closed = (
        await session.execute(select(Position).where(Position.status != "open"))
    ).scalars().all()
    wins = sum(1 for row in closed if row.realized_pnl > 0)
    losses = sum(1 for row in closed if row.realized_pnl < 0)

    fills = (
        await session.execute(
            select(Fill, Instrument, Position)
            .join(Instrument, Fill.instrument_id == Instrument.id)
            .outerjoin(Position, Fill.position_id == Position.id)
            .order_by(desc(Fill.ts))
            .limit(12)
        )
    ).all()
    decisions = (
        await session.execute(
            select(Decision, Instrument)
            .outerjoin(Instrument, Decision.instrument_id == Instrument.id)
            .order_by(desc(Decision.ts))
            .limit(16)
        )
    ).all()
    equity_rows = (
        await session.execute(select(EquityPoint).order_by(desc(EquityPoint.ts)).limit(400))
    ).scalars().all()
    equity_rows = list(reversed(equity_rows))

    latent = sum(latent_pnl(pos) for pos in positions.values())
    daily = float(equity - account.day_start_equity)
    start = float(account.day_start_equity) or 1.0

    return {
        "account": {
            "cash": float(account.cash),
            "equity": float(equity),
            "mtm": float(mtm),
            "latent_pnl": latent,
            "bankroll_start": float(account.bankroll_start),
            "realized_pnl": float(account.realized_pnl),
            "daily_pnl": daily,
            "daily_pnl_pct": daily / start,
            "worker_state": account.worker_state,
            "killed": account.killed,
            "halted": account.halted,
            "last_error": account.last_error,
        },
        "settings": settings,
        "stats": {
            "open_positions": len(positions),
            "wins": wins,
            "losses": losses,
            "win_rate": (wins / (wins + losses)) if (wins + losses) else None,
        },
        "instruments": [
            serialize_instrument(row, position=positions.get(row.id), bars=sparks.get(row.id, []))
            for row in instruments
        ],
        "equity": [
            {
                "ts": row.ts.isoformat(),
                "equity": float(row.equity),
                "cash": float(row.cash),
                "mtm": float(row.mtm),
                "daily_pnl": float(row.daily_pnl),
            }
            for row in equity_rows
        ],
        "recent_fills": [serialize_fill(fill, inst, pos) for fill, inst, pos in fills],
        "recent_decisions": [serialize_decision(row, inst) for row, inst in decisions],
        "server_time": datetime.now(timezone.utc).isoformat(),
    }


async def load_analysis(session: AsyncSession, window: int) -> dict:
    rows = (
        await session.execute(
            select(Position)
            .options(selectinload(Position.instrument))
            .where(Position.status != "open")
            .order_by(desc(Position.closed_at))
            .limit(window)
        )
    ).scalars().all()
    payload = []
    for row in rows:
        pnl = float(row.realized_pnl)
        payload.append(
            {
                "id": row.id,
                "symbol": row.instrument.symbol,
                "name": row.instrument.name,
                "sleeve": row.sleeve,
                "qty": float(row.qty),
                "avg_price": float(row.avg_price),
                "fees": float(row.fees),
                "realized_pnl": pnl,
                "result": classify(pnl),
                "status": row.status,
                "exit_reason": row.exit_reason or row.status,
                "opened_at": row.opened_at.isoformat() if row.opened_at else None,
                "closed_at": row.closed_at.isoformat() if row.closed_at else None,
                "hold_hours": hold_hours(row.opened_at, row.closed_at),
            }
        )
    return analyze_trades(payload)


def downsample_points(points: list[EquityPoint], cap: int = 360) -> list[EquityPoint]:
    if len(points) <= cap:
        return points
    step = max(1, len(points) // cap)
    picked = points[::step]
    if picked[-1] is not points[-1]:
        picked.append(points[-1])
    return picked


async def load_equity_curve(session: AsyncSession, window: str) -> dict:
    now = datetime.now(timezone.utc)
    if window == "today":
        start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    elif window == "7d":
        start = now - timedelta(days=7)
    elif window == "30d":
        start = now - timedelta(days=30)
    else:
        start = None
    if window == "today":
        stmt = select(EquityPoint).where(EquityPoint.ts >= start).order_by(EquityPoint.ts)
        rows = list((await session.execute(stmt)).scalars().all())
    else:
        stmt = select(EquityPoint)
        if start is not None:
            stmt = stmt.where(EquityPoint.ts >= start)
        stmt = stmt.order_by(desc(EquityPoint.ts)).limit(8000)
        rows = list(reversed((await session.execute(stmt)).scalars().all()))
    rows = downsample_points(rows)
    return {
        "window": window,
        "points": [
            {
                "ts": row.ts.isoformat(),
                "equity": float(row.equity),
                "cash": float(row.cash),
                "mtm": float(row.mtm),
                "daily_pnl": float(row.daily_pnl),
            }
            for row in rows
        ],
    }
