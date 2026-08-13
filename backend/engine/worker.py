from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import httpx
from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import db as database
from app.bus import publish
from app.config import Settings
from app.models import Account, Bar, Cooldown, Decision, EquityPoint, Fill, Instrument, Position, Setting
from app.services import compute_equity, load_settings
from engine.ingest.binance import fetch_klines, fetch_last as binance_last
from engine.ingest.stooq import fetch_daily as stooq_daily
from engine.ingest.types import RawBar
from engine.ingest.yahoo import fetch_daily as yahoo_daily
from engine.ingest.yahoo import fetch_last as yahoo_last
from engine.paper.broker import plan_buy, plan_sell, pulse_qty, realized_pnl
from engine.strategy.momentum import MomentumScore, pick_winner, score_closes
from engine.strategy.pulse import entry_blocked, evaluate_bar, should_rearm, stop_hit
from engine.strategy.snap import evaluate_snap
from engine.timeutil import as_utc, is_forming_daily, last_closed_4h
log = logging.getLogger("worker")


def _dec(value: object, default: str = "0") -> Decimal:
    if value is None:
        return Decimal(default)
    return Decimal(str(value))


def _setting_int(settings: dict[str, str], key: str, default: int) -> int:
    try:
        return int(float(settings.get(key, default)))
    except (TypeError, ValueError):
        return default


def _setting_float(settings: dict[str, str], key: str, default: float) -> float:
    try:
        return float(settings.get(key, default))
    except (TypeError, ValueError):
        return default


async def _bars(session: AsyncSession, instrument: Instrument, timeframe: str, limit: int = 400) -> list[Bar]:
    rows = (
        await session.execute(
            select(Bar)
            .where(Bar.instrument_id == instrument.id, Bar.timeframe == timeframe)
            .order_by(Bar.ts)
        )
    ).scalars().all()
    return list(rows[-limit:])


async def _upsert_bars(session: AsyncSession, instrument: Instrument, raw: list[RawBar]) -> int:
    if not raw:
        return 0
    existing_rows = (
        await session.execute(
            select(Bar).where(
                Bar.instrument_id == instrument.id,
                Bar.timeframe == raw[0].timeframe,
                Bar.ts >= raw[0].ts,
            )
        )
    ).scalars().all()
    have = {row.ts: row for row in existing_rows}
    changed = 0
    latest = instrument.last_bar_at
    for bar in raw:
        row = have.get(bar.ts)
        if row is None:
            session.add(
                Bar(
                    instrument_id=instrument.id,
                    timeframe=bar.timeframe,
                    ts=bar.ts,
                    open=bar.open,
                    high=bar.high,
                    low=bar.low,
                    close=bar.close,
                    volume=bar.volume,
                )
            )
            changed += 1
        elif row.close != bar.close or row.high != bar.high or row.low != bar.low:
            row.open = bar.open
            row.high = bar.high
            row.low = bar.low
            row.close = bar.close
            row.volume = bar.volume
            changed += 1
        if latest is None or bar.ts > latest:
            latest = bar.ts
            instrument.last_bar_at = bar.ts
            if instrument.kind != "crypto":
                instrument.last_price = bar.close
    return changed


async def _local_daily_count(session: AsyncSession, instrument: Instrument) -> int:
    rows = (
        await session.execute(select(Bar.id).where(Bar.instrument_id == instrument.id, Bar.timeframe == "1d"))
    ).all()
    return len(rows)


async def refresh_etf(
    session: AsyncSession,
    client: httpx.AsyncClient,
    instrument: Instrument,
    *,
    now: datetime,
    quote_every: int,
    boot: bool,
) -> None:
    count = await _local_daily_count(session, instrument)
    fetched = instrument.last_history_at
    fetch_age = None if fetched is None else (now - fetched).total_seconds()
    need_history = boot or fetched is None or count < 220
    if not need_history and fetch_age is not None and fetch_age >= 12 * 3600:
        need_history = True
    if fetch_age is not None and fetch_age < 3 * 3600 and count >= 220:
        need_history = False

    if need_history:
        bars: list[RawBar] = []
        try:
            bars = await stooq_daily(client, instrument.feed_symbol)
        except Exception as exc:
            log.warning("stooq %s failed: %s", instrument.symbol, exc)
        if len(bars) < 200:
            try:
                bars = await yahoo_daily(client, instrument.symbol)
            except Exception as exc:
                log.warning("yahoo %s failed: %s", instrument.symbol, exc)
                if not bars:
                    return
        await _upsert_bars(session, instrument, bars)
        instrument.last_history_at = now

    quote_age = None if instrument.last_quote_at is None else (now - instrument.last_quote_at).total_seconds()
    if boot or quote_age is None or quote_age >= quote_every:
        quote = await yahoo_last(client, instrument.symbol)
        if quote:
            instrument.last_price = quote
            instrument.last_quote_at = now


async def refresh_crypto(
    session: AsyncSession,
    client: httpx.AsyncClient,
    instrument: Instrument,
    *,
    now: datetime,
    boot: bool,
) -> None:
    last = await binance_last(client, instrument.feed_symbol)
    if last:
        instrument.last_price = last
        instrument.last_quote_at = now
    closed = last_closed_4h(now)
    have_closed = instrument.last_bar_at is not None and instrument.last_bar_at >= closed
    if not boot and have_closed:
        return
    try:
        rows = await fetch_klines(client, instrument.feed_symbol, interval="4h", limit=500)
    except Exception as exc:
        log.warning("binance klines %s failed: %s", instrument.symbol, exc)
        return
    if len(rows) >= 2:
        rows = rows[:-1]
    await _upsert_bars(session, instrument, rows)
    instrument.last_history_at = now


async def apply_fill(
    session: AsyncSession,
    account: Account,
    instrument: Instrument,
    fill,
    *,
    sleeve: str,
    position: Position | None,
    stop: Decimal | None = None,
    exit_reason: str | None = None,
) -> Position:
    now = datetime.now(timezone.utc)
    if fill.side == "buy":
        account.cash -= fill.price * fill.qty + fill.fee
        if position is None:
            position = Position(
                instrument_id=instrument.id,
                sleeve=sleeve,
                side="long",
                qty=fill.qty,
                avg_price=fill.price,
                stop_price=stop,
                fees=fill.fee,
                status="open",
                opened_at=now,
            )
            session.add(position)
            await session.flush()
        else:
            total = position.qty + fill.qty
            position.avg_price = (position.avg_price * position.qty + fill.price * fill.qty) / total
            position.qty = total
            position.fees += fill.fee
            if stop is not None:
                position.stop_price = stop
    else:
        account.cash += fill.price * fill.qty - fill.fee
        assert position is not None
        pnl = realized_pnl(
            avg_price=position.avg_price,
            qty=fill.qty,
            sell_price=fill.price,
            sell_fee=fill.fee,
            buy_fees=position.fees,
        )
        account.realized_pnl += pnl
        position.realized_pnl += pnl
        position.fees += fill.fee
        position.qty -= fill.qty
        if position.qty <= Decimal("0.00000001"):
            position.qty = Decimal("0")
            position.status = "closed"
            position.closed_at = now
            position.exit_reason = exit_reason or fill.reason[:32]
    row = Fill(
        instrument_id=instrument.id,
        position_id=position.id,
        sleeve=sleeve,
        side=fill.side,
        qty=fill.qty,
        price=fill.price,
        fee=fill.fee,
        reason=fill.reason,
        ts=now,
    )
    session.add(row)
    await publish("fill", {"symbol": instrument.symbol, "side": fill.side, "qty": float(fill.qty)})
    return position


def _note(session: AsyncSession, *, instrument: Instrument | None, sleeve: str, action: str, reason: str, price=None, qty=0.0, score=None) -> None:
    session.add(
        Decision(
            instrument_id=instrument.id if instrument else None,
            sleeve=sleeve,
            action=action,
            price=float(price) if price is not None else None,
            qty=float(qty),
            score=float(score) if score is not None else None,
            reason=reason,
        )
    )


async def run_slow(session: AsyncSession, account: Account, settings: dict[str, str], now: datetime) -> None:
    lookback = _setting_int(settings, "slow_lookback", 252)
    skip = _setting_int(settings, "slow_skip", 21)
    sma_len = _setting_int(settings, "slow_sma", 210)
    sleeve_frac = _dec(settings.get("slow_sleeve_fraction"), "0.85")
    fee_bps = _dec(settings.get("slow_fee_bps"), "5")
    slip_bps = _dec(settings.get("slow_slip_bps"), "2")
    min_notional = _dec(settings.get("min_trade_notional"), "15")
    month_key = now.strftime("%Y-%m")
    last_month = settings.get("last_slow_month") or ""

    instruments = (
        await session.execute(select(Instrument).where(Instrument.sleeve == "slow"))
    ).scalars().all()
    scores: list[MomentumScore] = []
    by_symbol = {row.symbol: row for row in instruments}
    for instrument in instruments:
        bars = await _bars(session, instrument, "1d", 400)
        closed = [bar for bar in bars if not is_forming_daily(bar.ts, now)]
        closes = [float(bar.close) for bar in closed]
        score = score_closes(instrument.symbol, closes, lookback=lookback, skip=skip, sma_len=sma_len)
        scores.append(score)
        instrument.features = {
            "ret_12_1": score.ret_12_1,
            "sma": score.sma,
            "above_sma": score.above_sma,
            "eligible": score.eligible,
            "reason": score.reason,
            "bars": len(closes),
        }

    winner = pick_winner(scores)
    target_symbol = winner.symbol if winner else None
    open_rows = (
        await session.execute(
            select(Position)
            .options(selectinload(Position.instrument))
            .where(Position.status == "open", Position.sleeve == "slow")
        )
    ).scalars().all()
    held = {row.instrument.symbol for row in open_rows}
    want = {target_symbol} if target_symbol else set()
    first_run = last_month == ""
    due = first_run or last_month != month_key
    if not due:
        return
    if held == want:
        row = await session.get(Setting, "last_slow_month")
        if row:
            row.value = month_key
        _note(
            session,
            instrument=by_symbol.get(target_symbol) if target_symbol else None,
            sleeve="slow",
            action="hold",
            reason="already in the dual-momentum winner" if target_symbol else "already in cash",
            score=winner.ret_12_1 if winner else None,
        )
        return

    equity, _ = await compute_equity(session, account)
    for position in open_rows:
        last = position.instrument.last_price or position.avg_price
        planned = plan_sell(
            last,
            position.qty,
            position.instrument.lot_size,
            slip_bps=slip_bps,
            fee_bps=fee_bps,
            reason="slow rebalance sell",
        )
        if planned:
            await apply_fill(
                session,
                account,
                position.instrument,
                planned,
                sleeve="slow",
                position=position,
                exit_reason="rebalance",
            )
            _note(
                session,
                instrument=position.instrument,
                sleeve="slow",
                action="exit",
                reason=f"leave {position.instrument.symbol} for {'cash' if not target_symbol else target_symbol}",
                price=planned.price,
                qty=float(planned.qty),
            )

    if target_symbol is None:
        row = await session.get(Setting, "last_slow_month")
        if row:
            row.value = month_key
        _note(session, instrument=None, sleeve="slow", action="cash", reason="no ETF above its 10-month average")
        return

    target = by_symbol[target_symbol]
    last = target.last_price
    if last is None or last <= 0:
        _note(session, instrument=target, sleeve="slow", action="skip", reason="no mark to buy")
        return
    budget = equity * sleeve_frac
    qty = budget / last
    planned = plan_buy(
        last,
        qty,
        target.lot_size,
        cash=account.cash,
        slip_bps=slip_bps,
        fee_bps=fee_bps,
        min_notional=min_notional,
        reason="slow dual momentum",
    )
    if planned is None:
        _note(session, instrument=target, sleeve="slow", action="skip", reason="size too small after cash/fees")
        return
    await apply_fill(session, account, target, planned, sleeve="slow", position=None)
    row = await session.get(Setting, "last_slow_month")
    if row:
        row.value = month_key
    _note(
        session,
        instrument=target,
        sleeve="slow",
        action="enter",
        reason=f"strongest eligible 12-1 {winner.ret_12_1:.1%}" if winner and winner.ret_12_1 is not None else "winner",
        price=planned.price,
        qty=float(planned.qty),
        score=winner.ret_12_1 if winner else None,
    )


async def _cooldown(session: AsyncSession, symbol: str) -> Cooldown:
    row = await session.get(Cooldown, symbol)
    if row is None:
        row = Cooldown(symbol=symbol, armed=True)
        session.add(row)
        await session.flush()
    return row


def _sessions_held(opened_at, bars) -> int:
    if opened_at is None:
        return 0
    start = opened_at.date() if hasattr(opened_at, "date") else opened_at
    return sum(1 for bar in bars if bar.ts.date() > start)


async def run_snap(session: AsyncSession, account: Account, settings: dict[str, str], now: datetime) -> None:
    rsi_len = _setting_int(settings, "snap_rsi", 2)
    rsi_buy = _setting_float(settings, "snap_rsi_buy", 10.0)
    sma_filter = _setting_int(settings, "snap_sma_filter", 200)
    sma_exit = _setting_int(settings, "snap_sma_exit", 5)
    max_days = _setting_int(settings, "snap_max_days", 5)
    atr_len = _setting_int(settings, "snap_atr", 20)
    stop_atr = _setting_float(settings, "snap_stop_atr", 2.5)
    sleeve_frac = _dec(settings.get("snap_sleeve_fraction"), "0.08")
    risk_frac = _dec(settings.get("snap_risk_fraction"), "0.0075")
    fee_bps = _dec(settings.get("slow_fee_bps"), "5")
    slip_bps = _dec(settings.get("slow_slip_bps"), "2")
    min_notional = _dec(settings.get("min_trade_notional"), "15")

    instruments = (
        await session.execute(select(Instrument).where(Instrument.sleeve == "snap"))
    ).scalars().all()
    open_rows = (
        await session.execute(
            select(Position)
            .options(selectinload(Position.instrument))
            .where(Position.status == "open", Position.sleeve == "snap")
        )
    ).scalars().all()
    open_by_id = {row.instrument_id: row for row in open_rows}
    equity, _ = await compute_equity(session, account)
    used = sum((row.qty * (row.instrument.last_price or row.avg_price) for row in open_rows), Decimal("0"))

    for instrument in instruments:
        bars = await _bars(session, instrument, "1d", 400)
        closed = [bar for bar in bars if not is_forming_daily(bar.ts, now)]
        if not closed:
            continue
        highs = [float(bar.high) for bar in closed]
        lows = [float(bar.low) for bar in closed]
        closes = [float(bar.close) for bar in closed]
        last_px = float(instrument.last_price or closes[-1])
        position = open_by_id.get(instrument.id)
        days = _sessions_held(position.opened_at, closed) if position else 0
        signal = evaluate_snap(
            closes,
            highs,
            lows,
            rsi_len=rsi_len,
            rsi_buy=rsi_buy,
            sma_filter=sma_filter,
            sma_exit=sma_exit,
            atr_len=atr_len,
            stop_atr=stop_atr,
            max_days=max_days,
            days_held=days,
            open_stop=float(position.stop_price) if position and position.stop_price else None,
            has_position=position is not None,
        )
        instrument.features = {
            "rsi": signal.rsi,
            "sma_long": signal.sma_long,
            "sma_exit": signal.sma_exit,
            "atr": signal.atr,
            "stop": float(position.stop_price) if position and position.stop_price else signal.stop,
            "action": signal.action,
            "reason": signal.reason,
            "days_held": days,
            "bars": len(closes),
        }

        if position is not None and stop_hit(last_px, float(position.stop_price) if position.stop_price else None):
            planned = plan_sell(
                _dec(instrument.last_price or position.avg_price),
                position.qty,
                instrument.lot_size,
                slip_bps=slip_bps,
                fee_bps=fee_bps,
                reason="snap stop",
            )
            if planned:
                await apply_fill(
                    session, account, instrument, planned, sleeve="snap", position=position, exit_reason="stop"
                )
                _note(session, instrument=instrument, sleeve="snap", action="exit", reason="live stop", price=planned.price, qty=float(planned.qty))
            continue

        cool = await _cooldown(session, f"snap:{instrument.symbol}")
        new_bar = cool.last_handled_bar_at is None or closed[-1].ts > cool.last_handled_bar_at
        if not new_bar:
            continue
        cool.last_handled_bar_at = closed[-1].ts

        if signal.action == "exit" and position is not None:
            planned = plan_sell(
                _dec(instrument.last_price or position.avg_price),
                position.qty,
                instrument.lot_size,
                slip_bps=slip_bps,
                fee_bps=fee_bps,
                reason="snap exit",
            )
            if planned:
                reason = "time" if "time" in signal.reason else ("stop" if "stop" in signal.reason else "bounce")
                await apply_fill(
                    session, account, instrument, planned, sleeve="snap", position=position, exit_reason=reason
                )
                _note(session, instrument=instrument, sleeve="snap", action="exit", reason=signal.reason, price=planned.price, qty=float(planned.qty))
            continue

        if signal.action == "enter" and position is None and signal.stop and signal.atr:
            if last_px <= signal.stop:
                _note(session, instrument=instrument, sleeve="snap", action="skip", reason="live price already through the stop")
                continue
            remaining = max(Decimal("0"), equity * sleeve_frac - used)
            qty = pulse_qty(
                equity,
                _dec(instrument.last_price),
                signal.atr,
                stop_atr,
                risk_fraction=risk_frac,
                lot=instrument.lot_size,
                sleeve_budget=remaining,
            )
            planned = plan_buy(
                _dec(instrument.last_price),
                qty,
                instrument.lot_size,
                cash=account.cash,
                slip_bps=slip_bps,
                fee_bps=fee_bps,
                min_notional=min_notional,
                reason="snap washout",
            )
            if planned is None:
                _note(session, instrument=instrument, sleeve="snap", action="skip", reason="snap size rounded to zero")
                continue
            await apply_fill(
                session,
                account,
                instrument,
                planned,
                sleeve="snap",
                position=None,
                stop=_dec(signal.stop),
            )
            used += planned.price * planned.qty
            _note(
                session,
                instrument=instrument,
                sleeve="snap",
                action="enter",
                reason=signal.reason,
                price=planned.price,
                qty=float(planned.qty),
                score=signal.rsi,
            )


async def run_pulse(session: AsyncSession, account: Account, settings: dict[str, str], now: datetime) -> None:
    donchian = _setting_int(settings, "pulse_donchian", 20)
    exit_ch = _setting_int(settings, "pulse_exit_channel", 10)
    atr_len = _setting_int(settings, "pulse_atr", 14)
    stop_atr = _setting_float(settings, "pulse_stop_atr", 2.5)
    trail_atr = _setting_float(settings, "pulse_trail_atr", 3.0)
    sleeve_frac = _dec(settings.get("pulse_sleeve_fraction"), "0.12")
    risk_frac = _dec(settings.get("pulse_risk_fraction"), "0.01")
    fee_bps = _dec(settings.get("pulse_fee_bps"), "10")
    slip_bps = _dec(settings.get("pulse_slip_bps"), "5")
    min_notional = _dec(settings.get("min_trade_notional"), "15")

    instruments = (
        await session.execute(select(Instrument).where(Instrument.sleeve == "pulse"))
    ).scalars().all()
    open_rows = (
        await session.execute(
            select(Position)
            .options(selectinload(Position.instrument))
            .where(Position.status == "open", Position.sleeve == "pulse")
        )
    ).scalars().all()
    open_by_id = {row.instrument_id: row for row in open_rows}
    equity, _ = await compute_equity(session, account)
    used = sum((row.qty * (row.instrument.last_price or row.avg_price) for row in open_rows), Decimal("0"))

    for instrument in instruments:
        bars = await _bars(session, instrument, "4h", 400)
        highs = [float(bar.high) for bar in bars]
        lows = [float(bar.low) for bar in bars]
        closes = [float(bar.close) for bar in bars]
        last_px = float(instrument.last_price or (closes[-1] if closes else 0))
        position = open_by_id.get(instrument.id)
        cool = await _cooldown(session, instrument.symbol)
        signal = evaluate_bar(
            highs,
            lows,
            closes,
            donchian=donchian,
            exit_channel=exit_ch,
            atr_len=atr_len,
            stop_atr=stop_atr,
            trail_atr=trail_atr,
            open_stop=float(position.stop_price) if position and position.stop_price else None,
            has_position=position is not None,
        )
        instrument.features = {
            "atr": signal.atr,
            "channel_high": signal.channel_high,
            "channel_low": signal.channel_low,
            "stop": float(position.stop_price) if position and position.stop_price else signal.stop,
            "action": signal.action,
            "reason": signal.reason,
            "armed": cool.armed,
            "bars": len(closes),
        }

        if position is not None and stop_hit(last_px, float(position.stop_price) if position.stop_price else None):
            planned = plan_sell(
                _dec(instrument.last_price or position.avg_price),
                position.qty,
                instrument.lot_size,
                slip_bps=slip_bps,
                fee_bps=fee_bps,
                reason="pulse stop",
            )
            if planned:
                await apply_fill(
                    session, account, instrument, planned, sleeve="pulse", position=position, exit_reason="stop"
                )
                cool.last_exit_bar_at = instrument.last_bar_at
                cool.armed = False
                _note(session, instrument=instrument, sleeve="pulse", action="exit", reason="live stop", price=planned.price, qty=float(planned.qty))
            continue

        new_bar = bars and (cool.last_handled_bar_at is None or bars[-1].ts > cool.last_handled_bar_at)
        if not new_bar:
            continue
        cool.last_handled_bar_at = bars[-1].ts

        if position is None and should_rearm(closes[-1], signal.channel_high):
            cool.armed = True

        if signal.action == "exit" and position is not None:
            planned = plan_sell(
                _dec(instrument.last_price or position.avg_price),
                position.qty,
                instrument.lot_size,
                slip_bps=slip_bps,
                fee_bps=fee_bps,
                reason="pulse exit",
            )
            if planned:
                reason = "channel" if "low" in signal.reason else "stop"
                await apply_fill(
                    session, account, instrument, planned, sleeve="pulse", position=position, exit_reason=reason
                )
                cool.last_exit_bar_at = instrument.last_bar_at
                cool.armed = False
                _note(session, instrument=instrument, sleeve="pulse", action="exit", reason=signal.reason, price=planned.price, qty=float(planned.qty))
            continue

        if signal.action == "trail" and position is not None and signal.stop:
            position.stop_price = _dec(signal.stop)
            _note(session, instrument=instrument, sleeve="pulse", action="trail", reason=signal.reason, price=signal.stop)
            continue

        if signal.action == "enter" and position is None and signal.atr and signal.stop:
            blocked = entry_blocked(
                armed=cool.armed,
                live=last_px,
                channel_high=signal.channel_high,
                stop=signal.stop,
            )
            if blocked:
                _note(session, instrument=instrument, sleeve="pulse", action="skip", reason=blocked)
                continue
            remaining = max(Decimal("0"), equity * sleeve_frac - used)
            qty = pulse_qty(
                equity,
                _dec(instrument.last_price),
                signal.atr,
                stop_atr,
                risk_fraction=risk_frac,
                lot=instrument.lot_size,
                sleeve_budget=remaining,
            )
            planned = plan_buy(
                _dec(instrument.last_price),
                qty,
                instrument.lot_size,
                cash=account.cash,
                slip_bps=slip_bps,
                fee_bps=fee_bps,
                min_notional=min_notional,
                reason="pulse breakout",
            )
            if planned is None:
                _note(session, instrument=instrument, sleeve="pulse", action="skip", reason="pulse size rounded to zero")
                continue
            await apply_fill(
                session,
                account,
                instrument,
                planned,
                sleeve="pulse",
                position=None,
                stop=_dec(signal.stop),
            )
            used += planned.price * planned.qty
            _note(
                session,
                instrument=instrument,
                sleeve="pulse",
                action="enter",
                reason=signal.reason,
                price=planned.price,
                qty=float(planned.qty),
                score=signal.atr,
            )


async def snapshot_equity(session: AsyncSession) -> None:
    account = await session.get(Account, 1)
    assert account is not None
    equity, mtm = await compute_equity(session, account)
    account.equity = equity
    today = date.today()
    if account.day_anchor != today:
        account.day_anchor = today
        account.day_start_equity = equity
        account.halted = False
        if account.worker_state == "halted" and not account.killed:
            account.worker_state = "running"
    daily = equity - account.day_start_equity
    halt_pct = float((await load_settings(session)).get("daily_loss_halt", "0.05"))
    if account.day_start_equity > 0 and daily / account.day_start_equity <= -halt_pct:
        account.halted = True
        account.worker_state = "halted"
    last_point = (
        await session.execute(select(EquityPoint).order_by(desc(EquityPoint.ts)).limit(1))
    ).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if (
        last_point is not None
        and last_point.ts is not None
        and (now - as_utc(last_point.ts)).total_seconds() < 50
        and last_point.equity == equity
        and last_point.cash == account.cash
    ):
        return
    session.add(EquityPoint(equity=equity, cash=account.cash, mtm=mtm, daily_pnl=daily))


async def prune_history(session: AsyncSession) -> None:
    now = datetime.now(timezone.utc)
    await session.execute(delete(EquityPoint).where(EquityPoint.ts < now - timedelta(days=40)))
    await session.execute(
        delete(Decision).where(
            Decision.ts < now - timedelta(days=7),
            Decision.action.in_(("skip", "hold")),
        )
    )


async def run_cycle(settings: Settings, *, boot: bool = False) -> None:
    if database.SessionLocal is None:
        raise RuntimeError("Database is not initialized")
    async with database.SessionLocal() as session:
        account = await session.get(Account, 1)
        if account is None:
            return
        if account.worker_state == "paused" or account.killed:
            await snapshot_equity(session)
            await session.commit()
            return

        db_settings = await load_settings(session)
        now = datetime.now(timezone.utc)
        cycle_ok = True
        headers = {"User-Agent": "market-bot/0.1 (paper desk)", "Accept": "*/*"}
        async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
            instruments = (await session.execute(select(Instrument))).scalars().all()
            etf_every = _setting_int(db_settings, "etf_refresh_seconds", 3600)
            for instrument in instruments:
                try:
                    if instrument.kind == "etf":
                        await refresh_etf(
                            session,
                            client,
                            instrument,
                            now=now,
                            quote_every=etf_every,
                            boot=boot,
                        )
                    else:
                        await refresh_crypto(session, client, instrument, now=now, boot=boot)
                except Exception as exc:
                    log.exception("refresh %s", instrument.symbol)
                    account.last_error = f"{instrument.symbol}: {exc}"
                    cycle_ok = False

        await session.flush()
        if not account.halted:
            try:
                await run_slow(session, account, db_settings, now)
            except Exception as exc:
                log.exception("slow sleeve")
                account.last_error = str(exc)
                cycle_ok = False
            try:
                await run_snap(session, account, db_settings, now)
            except Exception as exc:
                log.exception("snap sleeve")
                account.last_error = str(exc)
                cycle_ok = False
            try:
                await run_pulse(session, account, db_settings, now)
            except Exception as exc:
                log.exception("pulse sleeve")
                account.last_error = str(exc)
                cycle_ok = False

        await snapshot_equity(session)
        await prune_history(session)
        if cycle_ok:
            account.last_error = None
        await session.commit()
        await publish("tick", {"ts": now.isoformat()})


async def worker_loop(settings: Settings) -> None:
    log.info("worker starting (paper only; slow monthly, pulse 4h)")
    first = True
    while True:
        started = datetime.now(timezone.utc)
        try:
            await run_cycle(settings, boot=first)
            first = False
        except Exception:
            log.exception("worker cycle failed")
            if database.SessionLocal is not None:
                async with database.SessionLocal() as session:
                    account = await session.get(Account, 1)
                    if account is not None:
                        account.last_error = "worker cycle failed"
                        await session.commit()
        db_settings = {}
        if database.SessionLocal is not None:
            async with database.SessionLocal() as session:
                db_settings = await load_settings(session)
        wait = max(5, _setting_int(db_settings, "poll_interval_seconds", settings.poll_interval_seconds))
        elapsed = (datetime.now(timezone.utc) - started).total_seconds()
        await asyncio.sleep(max(1.0, wait - elapsed))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    settings = Settings()
    database.init_engine(settings)

    async def _boot() -> None:
        await database.init_db(settings)
        await worker_loop(settings)

    asyncio.run(_boot())


if __name__ == "__main__":
    main()
