export type PositionLite = {
  id: number;
  qty: number;
  avg_price: number;
  stop: number | null;
  fees: number;
  latent_pnl: number;
  market_value: number;
  opened_at: string | null;
};

export type Instrument = {
  id: number;
  symbol: string;
  name: string;
  sleeve: "slow" | "pulse" | string;
  kind: string;
  venue: string;
  currency: string;
  last: number | null;
  last_quote_at: string | null;
  last_bar_at: string | null;
  features: {
    ret_12_1?: number | null;
    sma?: number | null;
    above_sma?: boolean;
    eligible?: boolean;
    reason?: string;
    atr?: number | null;
    channel_high?: number | null;
    channel_low?: number | null;
    stop?: number | null;
    action?: string;
    rsi?: number | null;
    bars?: number;
  };
  position: PositionLite | null;
  spark: number[];
};

export type FillRow = {
  id: number;
  symbol: string;
  name: string;
  sleeve: string;
  side: string;
  qty: number;
  price: number;
  fee: number;
  notional: number;
  reason: string;
  mark: number | null;
  pnl: number | null;
  pnl_kind: "latent" | "realized";
  position_status: string | null;
  position_pnl: number | null;
  ts: string | null;
};

export type DecisionRow = {
  id: number;
  symbol: string | null;
  name: string;
  sleeve: string;
  action: string;
  price: number | null;
  qty: number;
  score: number | null;
  reason: string;
  ts: string | null;
};

export type PositionRow = {
  id: number;
  symbol: string;
  name: string;
  sleeve: string;
  side: string;
  qty: number;
  avg_price: number;
  mark: number;
  stop: number | null;
  market_value: number;
  fees: number;
  latent_pnl: number | null;
  realized_pnl: number;
  status: string;
  exit_reason: string | null;
  opened_at: string | null;
  closed_at: string | null;
};

export type Overview = {
  account: {
    cash: number;
    equity: number;
    mtm: number;
    latent_pnl: number;
    bankroll_start: number;
    realized_pnl: number;
    daily_pnl: number;
    daily_pnl_pct: number;
    worker_state: string;
    killed: boolean;
    halted: boolean;
    last_error: string | null;
  };
  settings: Record<string, string>;
  stats: {
    open_positions: number;
    wins: number;
    losses: number;
    win_rate: number | null;
  };
  instruments: Instrument[];
  equity: { ts: string; equity: number; cash: number; mtm: number; daily_pnl: number }[];
  recent_fills: FillRow[];
  recent_decisions: DecisionRow[];
  server_time: string;
};

export type Blotter = {
  fills: FillRow[];
  positions: PositionRow[];
  decisions: DecisionRow[];
};

export type AnalysisBucket = {
  key?: string;
  trades: number;
  wins: number;
  losses: number;
  flats: number;
  win_rate: number | null;
  pnl: number;
  avg_win: number | null;
  avg_loss: number | null;
  expectancy: number | null;
  profit_factor: number | null;
};

export type AnalysisTrade = {
  id: number;
  symbol: string;
  name: string;
  sleeve: string;
  qty: number;
  avg_price: number;
  fees: number;
  realized_pnl: number;
  result: string;
  status: string;
  exit_reason: string;
  opened_at: string | null;
  closed_at: string | null;
  hold_hours: number | null;
};

export type Analysis = {
  window: number;
  analyzed: number;
  summary: AnalysisBucket;
  by_sleeve: AnalysisBucket[];
  by_symbol: AnalysisBucket[];
  by_exit: AnalysisBucket[];
  notes: string[];
  trades: AnalysisTrade[];
};
