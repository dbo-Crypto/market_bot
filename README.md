# Market Bot — paper desk

Separate from the Polymarket weather/sports bot. Same shape: Docker, FastAPI, Next.js dark UI, virtual $1,000, kill switch.

Three sleeves, one ledger.

## Slow (core)

Dual momentum on two ETFs (`SPY` vs `EZU` by default).

- Rank 12-month return excluding the last month (12−1).
- Only hold a name if price is above its 10-month average.
- Else cash.
- Rebalance once a month. About **80%** of equity.

This is the boring book. It should trade rarely.

## Snap (aggressive stocks, small)

Nasdaq-100 ETF (`QQQ`). Buys a 2-day washout (RSI(2) ≤ 10) only if price is still above the 200-day average. Sells on a bounce back to the 5-day average, after 5 sessions, or at 2.5 × ATR. About **8%** of equity, ~0.75% risk to the stop.

This is the “faster traditional” book. It is allowed to trade often. It cannot empty Slow.

## Pulse (fun, small)

BTC and ETH on **4-hour** bars.

- Enter long when a closed 4h bar breaks the prior 20-bar high.
- Initial stop = 2.5 × ATR(14). Trail = 3 × ATR. Also exit if price closes under the 10-bar low.
- Size so that a stop is **1% of total equity**. Whole sleeve capped at **12%**.

This is the “are you a good trader” tape. It is supposed to lose often and win fat, or blow a few small holes. It cannot empty the Slow book.

Paper only. Prices from Stooq/Yahoo (ETFs) and Binance public API (crypto). No broker keys.

## Run

Ports **3001** (UI) and **8002** (API) so it can sit next to `prediction_bot` on 3000/8001.

```bash
cd "/Users/damien/Documents/02 - Dev/market_bot"
cp .env.example .env
docker compose up --build
```

Open http://localhost:3001

To run 24/7 on an OVH VPS instead of the Mac, see [DEPLOY.md](DEPLOY.md). Copy `.env.example` to `.env` on the server. Never commit `.env`.

Guides (same style as the Polymarket desk):

- `Market_Bot_Manual.pdf` — how the paper desk works
- `procedure_live.pdf` — what a real-money broker path would require (not a switch)

Reset the paper ledger from **Control**. Data lives in the `pgdata` volume (`docker compose down -v` wipes it).

## Tests

```bash
cd backend && pip install -e ".[dev]" && pytest
```
