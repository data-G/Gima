"use client";

import { useEffect, useMemo, useState } from "react";
import { PlayCircle } from "lucide-react";
import { SafetyNotice } from "@/components/SafetyNotice";
import { Shell } from "@/components/Shell";
import { StatusBadge } from "@/components/StatusBadge";
import { api } from "@/lib/api";
import { money, percent, shortDate } from "@/lib/format";
import type { BacktestResult, BacktestRunRequest } from "@/types/api";

const strategies = [
  { value: "moving_average_crossover", label: "Moving Average Crossover" },
  { value: "rsi_mean_reversion", label: "RSI Mean Reversion" },
  { value: "breakout", label: "Breakout Strategy" }
] as const;

function dateDaysAgo(days: number): string {
  const date = new Date();
  date.setDate(date.getDate() - days);
  return date.toISOString().slice(0, 10);
}

function EquityCurve({ result }: { result: BacktestResult }) {
  const points = result.equity_curve_json.slice(-120);
  if (points.length < 2) return <div className="rounded-md bg-slate-50 p-6 text-sm text-black/60">No equity curve points available.</div>;
  const values = points.map((point) => point.equity);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const width = 720;
  const height = 220;
  const path = points
    .map((point, index) => {
      const x = (index / (points.length - 1)) * width;
      const y = height - ((point.equity - min) / Math.max(max - min, 1)) * height;
      return `${index === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
  return (
    <div className="overflow-x-auto">
      <svg className="min-w-[720px]" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Equity curve">
        <rect width={width} height={height} fill="#f8fafc" rx="8" />
        <path d={path} fill="none" stroke="#2f5d50" strokeWidth="3" />
      </svg>
    </div>
  );
}

export default function BacktestsPage() {
  const [results, setResults] = useState<BacktestResult[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState<BacktestRunRequest>({
    symbol: "SPY",
    start_date: dateDaysAgo(180),
    end_date: dateDaysAgo(1),
    strategy_name: "breakout",
    initial_capital: 100000,
    fees_percent: 0.05,
    slippage_percent: 0.05,
    stop_loss_percent: 3,
    position_size_percent: 20,
    max_allowed_drawdown_percent: 20
  });

  async function load() {
    const rows = await api.backtests();
    setResults(rows);
    setSelectedId((current) => current ?? rows[0]?.id ?? null);
  }

  async function runBacktest() {
    setBusy(true);
    try {
      const result = await api.runBacktest({
        ...form,
        start_date: new Date(form.start_date).toISOString(),
        end_date: new Date(form.end_date).toISOString()
      });
      await load();
      setSelectedId(result.id);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    load().catch(console.error);
  }, []);

  const selected = useMemo(() => results.find((result) => result.id === selectedId) ?? results[0], [results, selectedId]);

  function update<K extends keyof BacktestRunRequest>(key: K, value: BacktestRunRequest[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  return (
    <Shell>
      <div className="mb-4">
        <h2 className="text-2xl font-semibold">Backtests</h2>
        <p className="text-sm font-medium text-red-700">Backtests are historical simulations. Past performance does not guarantee future results.</p>
      </div>

      <div className="mb-4">
        <SafetyNotice />
      </div>

      <section className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
        <div className="panel p-4">
          <h3 className="font-semibold">Run New Backtest</h3>
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-1">
            <label className="text-sm font-medium">Symbol<input className="mt-1 w-full rounded-md border border-black/15 px-3 py-2 uppercase" value={form.symbol} onChange={(event) => update("symbol", event.target.value)} /></label>
            <label className="text-sm font-medium">Strategy<select className="mt-1 w-full rounded-md border border-black/15 px-3 py-2" value={form.strategy_name} onChange={(event) => update("strategy_name", event.target.value as BacktestRunRequest["strategy_name"])}>
              {strategies.map((strategy) => <option value={strategy.value} key={strategy.value}>{strategy.label}</option>)}
            </select></label>
            <label className="text-sm font-medium">Start Date<input className="mt-1 w-full rounded-md border border-black/15 px-3 py-2" type="date" value={form.start_date.slice(0, 10)} onChange={(event) => update("start_date", event.target.value)} /></label>
            <label className="text-sm font-medium">End Date<input className="mt-1 w-full rounded-md border border-black/15 px-3 py-2" type="date" value={form.end_date.slice(0, 10)} onChange={(event) => update("end_date", event.target.value)} /></label>
            <label className="text-sm font-medium">Initial Capital<input className="mt-1 w-full rounded-md border border-black/15 px-3 py-2" type="number" value={form.initial_capital} onChange={(event) => update("initial_capital", Number(event.target.value))} /></label>
            <label className="text-sm font-medium">Fees %<input className="mt-1 w-full rounded-md border border-black/15 px-3 py-2" type="number" step="0.01" value={form.fees_percent} onChange={(event) => update("fees_percent", Number(event.target.value))} /></label>
            <label className="text-sm font-medium">Slippage %<input className="mt-1 w-full rounded-md border border-black/15 px-3 py-2" type="number" step="0.01" value={form.slippage_percent} onChange={(event) => update("slippage_percent", Number(event.target.value))} /></label>
            <label className="text-sm font-medium">Stop-loss %<input className="mt-1 w-full rounded-md border border-black/15 px-3 py-2" type="number" step="0.1" value={form.stop_loss_percent} onChange={(event) => update("stop_loss_percent", Number(event.target.value))} /></label>
            <label className="text-sm font-medium">Position Size %<input className="mt-1 w-full rounded-md border border-black/15 px-3 py-2" type="number" step="1" value={form.position_size_percent} onChange={(event) => update("position_size_percent", Number(event.target.value))} /></label>
            <label className="text-sm font-medium">Max Drawdown Limit %<input className="mt-1 w-full rounded-md border border-black/15 px-3 py-2" type="number" step="1" value={form.max_allowed_drawdown_percent} onChange={(event) => update("max_allowed_drawdown_percent", Number(event.target.value))} /></label>
          </div>
          <button className="mt-4 inline-flex items-center gap-2 rounded-md bg-moss px-4 py-2 font-medium text-white disabled:opacity-50" onClick={runBacktest} disabled={busy}>
            <PlayCircle size={17} aria-hidden />
            Run Backtest
          </button>
        </div>

        <div className="grid gap-4">
          {selected ? (
            <>
              <div className="panel p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h3 className="font-semibold">{selected.symbol} · {strategies.find((item) => item.value === selected.strategy_name)?.label}</h3>
                    <p className="text-sm text-black/60">{shortDate(selected.start_date)} to {shortDate(selected.end_date)}</p>
                  </div>
                  <StatusBadge value={selected.status} />
                </div>
                {selected.rejection_reason ? <p className="mt-3 rounded-md bg-red-50 p-3 text-sm text-red-800">{selected.rejection_reason}</p> : null}
                <div className="mt-4 grid gap-3 md:grid-cols-3">
                  <div className="metric"><p className="text-xs text-black/50">Total Return</p><strong>{percent(selected.total_return_percent)}</strong></div>
                  <div className="metric"><p className="text-xs text-black/50">Max Drawdown</p><strong className="text-red-700">{percent(selected.max_drawdown_percent)}</strong></div>
                  <div className="metric"><p className="text-xs text-black/50">Trades</p><strong>{selected.number_of_trades}</strong></div>
                  <div className="metric"><p className="text-xs text-black/50">Win Rate</p><strong>{percent(selected.win_rate)}</strong></div>
                  <div className="metric"><p className="text-xs text-black/50">Profit Factor</p><strong>{selected.profit_factor.toFixed(2)}</strong></div>
                  <div className="metric"><p className="text-xs text-black/50">Sharpe</p><strong>{selected.sharpe_ratio.toFixed(2)}</strong></div>
                </div>
              </div>
              <div className="panel p-4">
                <h3 className="font-semibold">Equity Curve</h3>
                <div className="mt-3"><EquityCurve result={selected} /></div>
              </div>
            </>
          ) : (
            <div className="panel p-4 text-sm text-black/60">No backtests yet.</div>
          )}
        </div>
      </section>

      <section className="mt-4 grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
        <div className="panel p-4">
          <h3 className="font-semibold">Results</h3>
          <div className="mt-3 grid gap-2">
            {results.map((result) => (
              <button className="rounded-md border border-black/10 bg-white p-3 text-left text-sm hover:bg-mint" key={result.id} onClick={() => setSelectedId(result.id)}>
                <div className="flex items-center justify-between gap-3"><strong>{result.symbol}</strong><StatusBadge value={result.status} /></div>
                <p className="mt-1 text-black/60">{result.strategy_name} · {percent(result.total_return_percent)}</p>
              </button>
            ))}
          </div>
        </div>

        <div className="panel overflow-x-auto p-4">
          <h3 className="font-semibold">Trade List</h3>
          <table className="mt-3 w-full min-w-[760px] text-left text-sm">
            <thead className="border-b border-black/10 text-black/60">
              <tr><th className="py-2">Entry</th><th>Exit</th><th>Qty</th><th>Entry Price</th><th>Exit Price</th><th>P/L</th><th>Reason</th></tr>
            </thead>
            <tbody>
              {(selected?.trades ?? []).map((trade) => (
                <tr className="border-b border-black/5" key={trade.id}>
                  <td className="py-3">{shortDate(trade.entry_time)}</td>
                  <td>{shortDate(trade.exit_time)}</td>
                  <td>{trade.quantity}</td>
                  <td>{money(trade.entry_price)}</td>
                  <td>{money(trade.exit_price)}</td>
                  <td className={trade.pnl < 0 ? "text-red-700" : "text-green-700"}>{money(trade.pnl)}</td>
                  <td>{trade.exit_reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </Shell>
  );
}
