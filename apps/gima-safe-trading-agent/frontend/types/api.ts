export type Health = {
  status: string;
  trading_mode: string;
  live_trading_enabled: boolean;
  safety_notice: string;
};

export type AccountSummary = {
  account_type?: string;
  net_liquidation?: number | string;
  available_funds?: number | string;
  currency?: string;
  [key: string]: string | number | undefined;
};

export type WatchlistItem = {
  id: number;
  user_id: number;
  symbol: string;
  asset_type: "stock" | "etf";
  exchange: string;
  active: boolean;
  created_at: string;
};

export type MarketData = {
  symbol: string;
  bid?: number;
  ask?: number;
  last?: number;
  source?: string;
  as_of?: string;
};

export type Signal = {
  id: number;
  symbol: string;
  signal_type: "BUY" | "SELL" | "WAIT";
  confidence: number;
  strategy_name: string;
  explanation: string;
  raw_features_json: Record<string, number | string>;
  created_at: string;
};

export type RiskCheck = {
  id: number;
  signal_id: number;
  status: "APPROVED" | "BLOCKED";
  reason: string;
  account_equity: number;
  proposed_position_size: number;
  risk_amount: number;
  stop_loss: number | null;
  max_loss_percent: number;
  created_at: string;
};

export type TradeOrder = {
  id: number;
  user_id: number;
  signal_id: number;
  symbol: string;
  side: "BUY" | "SELL";
  quantity: number;
  order_type: "MARKET" | "LIMIT";
  entry_price: number;
  stop_loss: number;
  take_profit: number | null;
  status: "PENDING_APPROVAL" | "APPROVED" | "REJECTED" | "PAPER_EXECUTED" | "CANCELLED";
  broker_order_id: string | null;
  is_live_trade: boolean;
  created_at: string;
  updated_at: string;
};

export type TradeJournal = {
  id: number;
  order_id: number | null;
  symbol: string;
  entry_price: number | null;
  exit_price: number | null;
  quantity: number | null;
  pnl: number;
  pnl_percent: number;
  notes: string;
  created_at: string;
};

export type RiskSettings = {
  id: number;
  user_id: number;
  max_risk_per_trade_percent: number;
  max_daily_loss_percent: number;
  max_weekly_loss_percent: number;
  max_position_concentration_percent: number;
  live_trading_enabled: boolean;
  kill_switch_enabled: boolean;
  updated_at: string;
};

export type RiskSettingsUpdate = Partial<
  Pick<
    RiskSettings,
    | "max_risk_per_trade_percent"
    | "max_daily_loss_percent"
    | "max_weekly_loss_percent"
    | "max_position_concentration_percent"
    | "kill_switch_enabled"
  >
> & {
  live_trading_enabled?: false;
};

export type SafetyState = {
  kill_switch_active: boolean;
  reason: string;
};

export type DailyReport = {
  date: string;
  realized_pl: number;
  daily_loss_limit: number;
  weekly_loss_limit: number;
  trading_mode: string;
  live_trading_enabled: boolean;
};

export type BacktestTrade = {
  id: number;
  backtest_id: number;
  entry_time: string;
  exit_time: string;
  side: string;
  quantity: number;
  entry_price: number;
  exit_price: number;
  pnl: number;
  pnl_percent: number;
  exit_reason: string;
};

export type BacktestResult = {
  id: number;
  symbol: string;
  strategy_name: "moving_average_crossover" | "rsi_mean_reversion" | "breakout";
  start_date: string;
  end_date: string;
  initial_capital: number;
  final_equity: number;
  total_return_percent: number;
  max_drawdown_percent: number;
  win_rate: number;
  loss_rate: number;
  profit_factor: number;
  sharpe_ratio: number;
  number_of_trades: number;
  average_win: number;
  average_loss: number;
  fees_percent: number;
  slippage_percent: number;
  stop_loss_percent: number;
  position_size_percent: number;
  max_allowed_drawdown_percent: number;
  status: "ACCEPTED" | "REJECTED";
  rejection_reason: string | null;
  warning: string;
  equity_curve_json: Array<{ timestamp: string; equity: number; drawdown_percent: number }>;
  created_at: string;
  trades: BacktestTrade[];
};

export type BacktestRunRequest = {
  symbol: string;
  start_date: string;
  end_date: string;
  strategy_name: "moving_average_crossover" | "rsi_mean_reversion" | "breakout";
  initial_capital: number;
  fees_percent: number;
  slippage_percent: number;
  stop_loss_percent: number;
  position_size_percent: number;
  max_allowed_drawdown_percent: number;
};
