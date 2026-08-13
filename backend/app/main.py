from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal

from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.bus import CHANNEL, get_redis, init_redis
from app.config import Settings, get_settings
from app.db import get_session, init_db, init_engine, seed_instruments
from app.models import Account, Decision, EquityPoint, Fill, Instrument, Position, Setting
from app.services import (
    build_overview,
    latest_sparks,
    load_analysis,
    load_equity_curve,
    load_instruments,
    load_settings,
    open_positions_by_instrument,
    serialize_decision,
    serialize_fill,
    serialize_instrument,
    serialize_position,
)
from engine.universe import parse_symbols

log = logging.getLogger("api")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    init_engine(settings)
    await init_db(settings)
    await init_redis(settings.redis_url)
    yield


app = FastAPI(title="Market Bot", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "mode": "paper"}


@app.get("/api/overview")
async def overview(session: AsyncSession = Depends(get_session)) -> dict:
    return await build_overview(session)


@app.get("/api/instruments")
async def instruments(
    sleeve: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> dict:
    rows = await load_instruments(session, sleeve)
    positions = await open_positions_by_instrument(session)
    daily_ids = [row.id for row in rows if row.sleeve in {"slow", "snap"}]
    pulse_ids = [row.id for row in rows if row.sleeve == "pulse"]
    sparks = {}
    sparks.update(await latest_sparks(session, daily_ids, "1d"))
    sparks.update(await latest_sparks(session, pulse_ids, "4h"))
    return {
        "instruments": [
            serialize_instrument(row, position=positions.get(row.id), bars=sparks.get(row.id, []))
            for row in rows
        ]
    }


@app.get("/api/blotter")
async def blotter(session: AsyncSession = Depends(get_session)) -> dict:
    fills = (
        await session.execute(
            select(Fill, Instrument, Position)
            .join(Instrument, Fill.instrument_id == Instrument.id)
            .outerjoin(Position, Fill.position_id == Position.id)
            .order_by(desc(Fill.ts))
            .limit(200)
        )
    ).all()
    positions = (
        await session.execute(
            select(Position)
            .options(selectinload(Position.instrument))
            .order_by(desc(Position.opened_at))
        )
    ).scalars().all()
    decisions = (
        await session.execute(
            select(Decision, Instrument)
            .outerjoin(Instrument, Decision.instrument_id == Instrument.id)
            .order_by(desc(Decision.ts))
            .limit(80)
        )
    ).all()
    return {
        "fills": [serialize_fill(fill, inst, pos) for fill, inst, pos in fills],
        "positions": [serialize_position(row) for row in positions],
        "decisions": [serialize_decision(row, inst) for row, inst in decisions],
    }


@app.get("/api/analysis")
async def analysis(session: AsyncSession = Depends(get_session)) -> dict:
    from app.analysis import ANALYSIS_WINDOW

    return await load_analysis(session, ANALYSIS_WINDOW)


@app.get("/api/equity")
async def equity_curve(
    window: str = Query(default="today"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    if window not in {"today", "7d", "30d", "all"}:
        raise HTTPException(status_code=400, detail="window must be today, 7d, 30d, or all")
    return await load_equity_curve(session, window)


@app.post("/api/control/{action}")
async def control(action: str, session: AsyncSession = Depends(get_session)) -> dict:
    account = await session.get(Account, 1)
    assert account is not None
    if action == "start":
        account.killed = False
        account.halted = False
        account.worker_state = "running"
        account.last_error = None
    elif action == "pause":
        account.worker_state = "paused"
    elif action == "kill":
        account.killed = True
        account.worker_state = "halted"
    elif action == "reset":
        bankroll = Decimal(str(settings.paper_bankroll))
        for model in (Fill, Decision, Position, EquityPoint):
            await session.execute(model.__table__.delete())
        from app.models import Cooldown

        await session.execute(Cooldown.__table__.delete())
        month = await session.get(Setting, "last_slow_month")
        if month:
            month.value = ""
        account.cash = bankroll
        account.equity = bankroll
        account.bankroll_start = bankroll
        account.realized_pnl = Decimal("0")
        account.day_start_equity = bankroll
        account.day_anchor = date.today()
        account.killed = False
        account.halted = False
        account.worker_state = "running"
        account.last_error = None
    else:
        raise HTTPException(status_code=400, detail="Unknown action")
    await session.commit()
    return {"ok": True, "state": account.worker_state, "killed": account.killed}


class SettingsPatch(BaseModel):
    slow_symbols: str | None = None
    snap_symbols: str | None = None
    pulse_symbols: str | None = None
    slow_sleeve_fraction: float | None = Field(default=None, ge=0.2, le=0.95)
    snap_sleeve_fraction: float | None = Field(default=None, ge=0.02, le=0.2)
    snap_rsi_buy: float | None = Field(default=None, ge=2, le=25)
    snap_max_days: int | None = Field(default=None, ge=1, le=10)
    snap_stop_atr: float | None = Field(default=None, ge=1.0, le=5.0)
    snap_risk_fraction: float | None = Field(default=None, ge=0.002, le=0.02)
    pulse_sleeve_fraction: float | None = Field(default=None, ge=0.02, le=0.3)
    pulse_risk_fraction: float | None = Field(default=None, ge=0.002, le=0.03)
    pulse_donchian: int | None = Field(default=None, ge=10, le=55)
    pulse_exit_channel: int | None = Field(default=None, ge=5, le=30)
    pulse_atr: int | None = Field(default=None, ge=7, le=30)
    pulse_stop_atr: float | None = Field(default=None, ge=1.0, le=5.0)
    pulse_trail_atr: float | None = Field(default=None, ge=1.5, le=6.0)
    daily_loss_halt: float | None = Field(default=None, ge=0.01, le=0.5)
    poll_interval_seconds: int | None = Field(default=None, ge=15)
    etf_refresh_seconds: int | None = Field(default=None, ge=300)
    crypto_bar_seconds: int | None = Field(default=None, ge=15)
    slow_fee_bps: float | None = Field(default=None, ge=0, le=50)
    pulse_fee_bps: float | None = Field(default=None, ge=0, le=50)


@app.get("/api/settings")
async def get_settings_api(session: AsyncSession = Depends(get_session)) -> dict:
    return await load_settings(session)


@app.patch("/api/settings")
async def patch_settings(body: SettingsPatch, session: AsyncSession = Depends(get_session)) -> dict:
    updates = body.model_dump(exclude_none=True)
    if "slow_symbols" in updates:
        parse_symbols(updates["slow_symbols"], sleeve="slow")
    if "snap_symbols" in updates:
        parse_symbols(updates["snap_symbols"], sleeve="snap")
    if "pulse_symbols" in updates:
        parse_symbols(updates["pulse_symbols"], sleeve="pulse")
    for key, value in updates.items():
        row = await session.get(Setting, key)
        if row is None:
            session.add(Setting(key=key, value=str(value)))
        else:
            row.value = str(value)
    merged = Settings()
    db = await load_settings(session)
    merged.slow_symbols = db.get("slow_symbols", merged.slow_symbols)
    merged.snap_symbols = db.get("snap_symbols", merged.snap_symbols)
    merged.pulse_symbols = db.get("pulse_symbols", merged.pulse_symbols)
    await seed_instruments(session, merged)
    await session.commit()
    return await load_settings(session)


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    redis = get_redis()
    if redis is None:
        await ws.send_json({"type": "notice", "payload": {"message": "live bus offline; UI will poll"}})
        try:
            while True:
                await asyncio.sleep(30)
                await ws.send_json({"type": "ping", "payload": {}})
        except WebSocketDisconnect:
            return

    pubsub = redis.pubsub()
    await pubsub.subscribe(CHANNEL)
    try:
        await ws.send_json({"type": "hello", "payload": {"mode": "paper"}})
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=20.0)
            if message and message.get("type") == "message":
                data = message.get("data")
                if isinstance(data, str):
                    await ws.send_text(data)
                else:
                    await ws.send_json(json.loads(data))
            else:
                await ws.send_json({"type": "ping", "payload": {}})
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(CHANNEL)
        await pubsub.aclose()
