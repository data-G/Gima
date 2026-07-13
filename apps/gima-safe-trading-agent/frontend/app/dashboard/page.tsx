"use client";

import { useEffect, useMemo, useState } from "react";
import { Power, RefreshCcw } from "lucide-react";
import { SafetyNotice } from "@/components/SafetyNotice";
import { Shell } from "@/components/Shell";
import { StatusBadge } from "@/components/StatusBadge";
import { api } from "@/lib/api";
import { confidence, money, shortDate } from "@/lib/format";
import type { AccountSummary, DailyReport, RiskCheck, SafetyState, Signal, TradeOrder, WatchlistItem } from "@/types/api";

export default function DashboardPage() {
  const [account, setAccount] = useState<AccountSummary | null>(null);
  const [report, setReport] = useState<DailyReport | null>(null);
  const [safety, setSafety] = useState<SafetyState | null>(null);
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [signals, setSignals] = useState<Signal[]>([]);
  const [riskChecks, setRiskChecks] = useState<RiskCheck[]>([]);
  const [orders, setOrders] = useState<TradeOrder[]>([]);
  const [busy, setBusy] = useState(false);

  async function load() {
    const [accountData, reportData, safetyData, watchlistData, signalData, riskData, orderData] = await Promise.all([
      api.accountSummary().catch(() => ({ account_type: "Unavailable" })),
      api.report(),
      api.safety(),
      api.watchlist(),
      api.signals(),
      api.riskChecks(),
      api.orders()
    ]);
    setAccount(accountData);
    setReport(reportData);
    setSafety(safetyData);
    setWatchlist(watchlistData);
    setSignals(signalData);
    setRiskChecks(riskData);
    setOrders(orderData);
  }

  async function toggleKillSwitch() {
    setBusy(true);
    try {
      await api.setKillSwitch(!safety?.kill_switch_active, "Dashboard operator action");
      await load();
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    load().catch(console.error);
  }, []);

  const weeklyPl = useMemo(() => orders.filter((order) => order.status === "PAPER_EXECUTED").length * 0, [orders]);
  const latestRisk = riskChecks[0];

  return (
    <Shell>
      <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Dashboard</h2>
          <p className="text-sm text-black/60">Operational view for paper trading, approvals, risk, and latest agent decisions.</p>
        </div>
        <button className="inline-flex items-center justify-center gap-2 rounded-md border border-black/10 bg-white px-3 py-2 text-sm" onClick={() => load()}>
          <RefreshCcw size={16} aria-hidden />
          Refresh
        </button>
      </div>

      <div className="mb-4">
        <SafetyNotice />
      </div>

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <div className="metric">
          <p className="text-sm text-black/60">Net Liquidation</p>
          <strong className="mt-2 block text-2xl">{money(account?.net_liquidation ?? account?.NetLiquidation)}</strong>
          <p className="mt-1 text-xs text-black/50">{account?.account_type ?? "Broker account"}</p>
        </div>
        <div className="metric">
          <p className="text-sm text-black/60">Today P/L</p>
          <strong className="mt-2 block text-2xl">{money(report?.realized_pl)}</strong>
          <p className="mt-1 text-xs text-black/50">Daily limit {money(report?.daily_loss_limit)}</p>
        </div>
        <div className="metric">
          <p className="text-sm text-black/60">Weekly P/L</p>
          <strong className="mt-2 block text-2xl">{money(weeklyPl)}</strong>
          <p className="mt-1 text-xs text-black/50">Weekly limit {money(report?.weekly_loss_limit)}</p>
        </div>
        <div className="metric">
          <p className="text-sm text-black/60">Risk Status</p>
          <div className="mt-2"><StatusBadge value={safety?.kill_switch_active ? "KILL SWITCH ACTIVE" : latestRisk?.status ?? "READY"} /></div>
          <p className="mt-2 text-xs text-black/60">{latestRisk?.reason ?? "Risk checks required before paper orders."}</p>
        </div>
      </section>

      <section className="mt-4 grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
        <div className="panel p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h3 className="font-semibold">Kill Switch</h3>
              <p className="text-sm text-black/60">{safety?.reason}</p>
            </div>
            <button className={`inline-flex items-center gap-2 rounded-md px-4 py-2 font-medium text-white ${safety?.kill_switch_active ? "bg-moss" : "bg-red-700"}`} onClick={toggleKillSwitch} disabled={busy}>
              <Power size={17} aria-hidden />
              {safety?.kill_switch_active ? "Deactivate" : "Activate"}
            </button>
          </div>
        </div>
        <div className="panel p-4">
          <h3 className="font-semibold">Active Watchlist</h3>
          <div className="mt-3 flex flex-wrap gap-2">
            {watchlist.filter((item) => item.active).map((item) => (
              <span className="rounded-md border border-black/10 bg-white px-3 py-2 text-sm" key={item.id}>{item.symbol} · {item.asset_type.toUpperCase()}</span>
            ))}
          </div>
        </div>
      </section>

      <section className="panel mt-4 overflow-x-auto p-4">
        <h3 className="font-semibold">Latest Signals</h3>
        <table className="mt-3 w-full min-w-[760px] text-left text-sm">
          <thead className="border-b border-black/10 text-black/60">
            <tr><th className="py-2">Symbol</th><th>Signal</th><th>Confidence</th><th>Risk</th><th>Explanation</th><th>Time</th></tr>
          </thead>
          <tbody>
            {signals.slice(0, 8).map((signal) => {
              const risk = riskChecks.find((item) => item.signal_id === signal.id);
              return (
                <tr className="border-b border-black/5 align-top" key={signal.id}>
                  <td className="py-3 font-semibold">{signal.symbol}</td>
                  <td><StatusBadge value={signal.signal_type} /></td>
                  <td>{confidence(signal.confidence)}</td>
                  <td>{risk ? <StatusBadge value={risk.status} /> : "-"}</td>
                  <td className="max-w-lg text-black/70">{signal.explanation}</td>
                  <td>{shortDate(signal.created_at)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>
    </Shell>
  );
}
