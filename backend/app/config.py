from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    paper_bankroll: float = 1000
    slow_symbols: str = "SPY,EZU"
    slow_sleeve_fraction: float = 0.80
    slow_lookback: int = 252
    slow_skip: int = 21
    slow_sma: int = 210
    snap_symbols: str = "QQQ"
    snap_sleeve_fraction: float = 0.08
    snap_rsi: int = 2
    snap_rsi_buy: float = 10.0
    snap_sma_filter: int = 200
    snap_sma_exit: int = 5
    snap_max_days: int = 5
    snap_atr: int = 20
    snap_stop_atr: float = 2.5
    snap_risk_fraction: float = 0.0075
    pulse_symbols: str = "BTCUSDT,ETHUSDT"
    pulse_sleeve_fraction: float = 0.12
    pulse_risk_fraction: float = 0.01
    pulse_donchian: int = 20
    pulse_exit_channel: int = 10
    pulse_atr: int = 14
    pulse_stop_atr: float = 2.5
    pulse_trail_atr: float = 3.0
    daily_loss_halt: float = 0.05
    poll_interval_seconds: int = 30
    etf_refresh_seconds: int = 3600
    crypto_bar_seconds: int = 60
    slow_fee_bps: float = 5
    slow_slip_bps: float = 2
    pulse_fee_bps: float = 10
    pulse_slip_bps: float = 5
    min_trade_notional: float = 15

    database_url: str = "postgresql+asyncpg://bot:bot@localhost:5432/market_bot"
    redis_url: str = "redis://localhost:6379/0"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3001"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


def get_settings() -> Settings:
    return Settings()
