"use client";

import { useEffect, useMemo, useState } from "react";
import { FilePlus2, PlayCircle } from "lucide-react";
import { Shell } from "@/components/Shell";
import { StatusBadge } from "@/components/StatusBadge";
import { api } from "@/lib/api";
import { confidence, money, shortDate } from "@/lib/format";
import type { RiskCheck, Signal, TradeOrder } from "@/types/api";

export default function SignalsPage() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [riskChecks, setRiskChecks] = useState<RiskCheck[]>([]);
  const [orders, setOrders] = useState<TradeOrder[]>([]);
  const [symbol, setSymbol] = useState("SPY");
  const [busy, setBusy] = useState<string | null>(null);

  async function load() {
    const [signalRows, riskRows, orderRows] = await Promise.all([api.signals(), api.riskChecks(), api.orders()]);
    setSignals(signalRows);
    setRiskChecks(riskRows);
    setOrders(orderRows);
  }

  async function runSignal() {
    setBusy("run");
    try {
      await api.runSignal(symbol);
      await load();
    } finally {
      setBusy(null);
    }
  }

  async function requestPaperTrade(signal: Signal, risk: RiskCheck) {
    setBusy(`order-${signal.id}`);
    try {
      const market = await api.brokerMarketData(signal.symbol).catch(() => ({ symbol: signal.symbol, last: 0 }));
      await api.createOrder({
        signal_id: signal.id,
        symbol: signal.symbol,
        side: signal.signal_type as "BUY" | "SELL",
        quantity: risk.proposed_position_size,
        entry_price: Number(market.last || 0),
        stop_loss: Number(risk.stop_loss || 0)
      });
      await load();
    } finally {
      setBusy(null);
    }
  }

  useEffect(() => {
    load().catch(console.error);
  }, []);

  const latestRiskBySignal = useMemo(() => {
    const map = new Map<number, RiskCheck>();
    for (const risk of riskChecks) {
      if (!map.has(risk.signal_id)) map.set(risk.signal_id, risk);
    }
    return map;
  }, [riskChecks]);

  const orderSignalIds = new Set(orders.map((order) => order.signal_id));

  return (
    <Shell>
      <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Signals</h2>
          <p className="text-sm text-black/60">BUY, SELL, and WAIT decisions with risk review. Paper trading only.</p>
        </div>
        <div className="flex gap-2">
          <input className="w-32 rounded-md border border-black/15 bg-white px-3 py-2 uppercase" value={symbol} onChange={(event) => setSymbol(event.target.value)} />
          <button className="inline-flex items-center gap-2 rounded-md bg-moss px-4 py-2 font-medium text-white" onClick={runSignal} disabled={busy === "run"}>
            <PlayCircle size={17} aria-hidden />
            Run
          </button>
        </div>
      </div>

      <section className="panel overflow-x-auto p-4">
        <table className="w-full min-w-[980px] text-left text-sm">
          <thead className="border-b border-black/10 text-black/60">
            <tr>
              <th className="py-2">Symbol</th>
              <th>Signal</th>
              <th>Confidence</th>
              <th>Risk</th>
              <th>Risk Amount</th>
              <th>Position</th>
              <th>Explanation</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {signals.map((signal) => {
              const risk = latestRiskBySignal.get(signal.id);
              const canRequest = signal.signal_type !== "WAIT" && risk?.status === "APPROVED" && !orderSignalIds.has(signal.id);
              return (
                <tr className="border-b border-black/5 align-top" key={signal.id}>
                  <td className="py-3 font-semibold">{signal.symbol}</td>
                  <td><StatusBadge value={signal.signal_type} /></td>
                  <td>{confidence(signal.confidence)}</td>
                  <td>{risk ? <StatusBadge value={risk.status} /> : "-"}</td>
                  <td>{money(risk?.risk_amount)}</td>
                  <td>{risk?.proposed_position_size ?? "-"}</td>
                  <td className="max-w-xl">
                    <p className="text-black/75">{signal.explanation}</p>
                    <p className="mt-1 text-xs text-black/45">{shortDate(signal.created_at)}</p>
                    {risk?.status === "BLOCKED" ? <p className="mt-2 rounded-md bg-red-50 p-2 text-red-800">{risk.reason}</p> : null}
                  </td>
                  <td>
                    <button className="inline-flex items-center gap-2 rounded-md bg-moss px-3 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-black/20" disabled={!canRequest || busy === `order-${signal.id}`} onClick={() => risk && requestPaperTrade(signal, risk)}>
                      <FilePlus2 size={16} aria-hidden />
                      Request Paper Trade
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>
    </Shell>
  );
}
