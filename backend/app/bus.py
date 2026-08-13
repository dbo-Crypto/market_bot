from __future__ import annotations

import json
from typing import Any

import redis.asyncio as redis

CHANNEL = "market.events"

_client: redis.Redis | None = None


async def init_redis(url: str) -> redis.Redis | None:
    global _client
    try:
        _client = redis.from_url(url, decode_responses=True)
        await _client.ping()
        return _client
    except Exception:
        _client = None
        return None


def get_redis() -> redis.Redis | None:
    return _client


async def publish(event_type: str, payload: dict[str, Any] | None = None) -> None:
    if _client is None:
        return
    message = json.dumps({"type": event_type, "payload": payload or {}})
    try:
        await _client.publish(CHANNEL, message)
    except Exception:
        return
