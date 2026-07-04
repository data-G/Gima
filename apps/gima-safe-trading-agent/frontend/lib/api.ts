import type {
  AccountSummary,
  BacktestResult,
  BacktestRunRequest,
  DailyReport,
  Health,
  MarketData,
  RiskCheck,
  RiskSettings,
  RiskSettingsUpdate,
  SafetyState,
  Signal,
  TradeJournal,
  TradeOrder,
  WatchlistItem
} from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    },
    cache: "no-store"
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<Health>("/health"),
  accountSummary: () => request<AccountSummary>("/broker/account-summary"),
  brokerMarketData: (symbol: string) => request<MarketData>(`/broker/market-data/${symbol}`),
  watchlist: () => request<WatchlistItem[]>("/watchlist"),
  addWatchlist: (symbol: string, assetType: "stock" | "etf") =>
    request<WatchlistItem>("/watchlist", { method: "POST", body: JSON.stringify({ symbol, asset_type: assetType, user_id: 1 }) }),
  updateWatchlist: (id: number, payload: Partial<Pick<WatchlistItem, "active" | "asset_type" | "exchange">>) =>
    request<WatchlistItem>(`/watchlist/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  removeWatchlist: (id: number) => request<{ status: string; id: number }>(`/watchlist/${id}`, { method: "DELETE" }),
  runSignal: (symbol: string) => request<Signal>("/signals/run", { method: "POST", body: JSON.stringify({ symbol }) }),
  signals: () => request<Signal[]>("/signals"),
  riskChecks: (signalId?: number) => request<RiskCheck[]>(signalId ? `/risk-checks?signal_id=${signalId}` : "/risk-checks"),
  orders: () => request<TradeOrder[]>("/orders"),
  createOrder: (payload: {
    signal_id: number;
    symbol: string;
    side: "BUY" | "SELL";
    quantity: number;
    entry_price: number;
    stop_loss: number;
    order_type?: "MARKET" | "LIMIT";
  }) =>
    request<TradeOrder>("/orders", {
      method: "POST",
      body: JSON.stringify({ user_id: 1, order_type: "MARKET", is_live_trade: false, ...payload })
    }),
  approveOrder: (id: number, approved: boolean) =>
    request<TradeOrder>(`/orders/${id}/approval`, {
      method: "POST",
      body: JSON.stringify({ approved, note: approved ? "Approved in dashboard." : "Rejected in dashboard." })
    }),
  safety: () => request<SafetyState>("/safety"),
  setKillSwitch: (active: boolean, reason: string) =>
    request<SafetyState>("/safety/kill-switch", { method: "POST", body: JSON.stringify({ active, reason }) }),
  report: () => request<DailyReport>("/reports/daily-pl"),
  journal: () => request<TradeJournal[]>("/journal"),
  riskSettings: (userId = 1) => request<RiskSettings>(`/risk-settings/${userId}`),
  updateRiskSettings: (userId: number, payload: RiskSettingsUpdate) =>
    request<RiskSettings>(`/risk-settings/${userId}`, { method: "PUT", body: JSON.stringify(payload) }),
  runBacktest: (payload: BacktestRunRequest) =>
    request<BacktestResult>("/backtests/run", { method: "POST", body: JSON.stringify(payload) }),
  backtests: () => request<BacktestResult[]>("/backtests"),
  backtest: (id: number) => request<BacktestResult>(`/backtests/${id}`)
};
