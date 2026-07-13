"use client";

import { useEffect, useMemo, useState } from "react";
import { Check, X } from "lucide-react";
import { SafetyNotice } from "@/components/SafetyNotice";
import { Shell } from "@/components/Shell";
import { StatusBadge } from "@/components/StatusBadge";
import { api } from "@/lib/api";
import { money, shortDate } from "@/lib/format";
import type { RiskCheck, Signal, TradeOrder } from "@/types/api";

export default function OrdersPage() {
  const [orders, setOrders] = useState<TradeOrder[]>([]);
  const [riskChecks, setRiskChecks] = useState<RiskCheck[]>([]);
  const [signals, setSignals] = useState<Signal[]>([]);
  const [busy, setBusy] = useState<number | null>(null);

  async function load() {
    const [orderRows, riskRows, signalRows] = await Promise.all([api.orders(), api.riskChecks(), api.signals()]);
    setOrders(orderRows);
    setRiskChecks(riskRows);
    setSignals(signalRows);
  }

  async function decide(id: number, approved: boolean) {
    setBusy(id);
    try {
      await api.approveOrder(id, approved);
      await load();
    } finally {
      setBusy(null);
    }
  }

  useEffect(() => {
    load().catch(console.error);
  }, []);

  const signalById = useMemo(() => new Map(signals.map((signal) => [signal.id, signal])), [signals]);
  const blockedRisks = riskChecks.filter((risk) => risk.status === "BLOCKED");
  const pending = orders.filter((order) => order.status === "PENDING_APPROVAL");
  const executed = orders.filter((order) => order.status === "PAPER_EXECUTED");

  return (
    <Shell>
      <div className="mb-4">
        <h2 className="text-2xl font-semibold">Orders</h2>
        <p className="text-sm text-black/60">Manual approval is required before any paper order execution.</p>
      </div>

      <div className="mb-4">
        <SafetyNotice />
      </div>

      <section className="panel overflow-x-auto p-4">
        <h3 className="font-semibold">Pending Approval</h3>
        <table className="mt-3 w-full min-w-[880px] text-left text-sm">
          <thead className="border-b border-black/10 text-black/60">
            <tr><th className="py-2">Order</th><th>Symbol</th><th>Side</th><th>Qty</th><th>Entry</th><th>Stop</th><th>Status</th><th>Decision</th></tr>
          </thead>
          <tbody>
            {pending.map((order) => (
              <tr className="border-b border-black/5" key={order.id}>
                <td className="py-3">#{order.id}</td>
                <td className="font-semibold">{order.symbol}</td>
                <td>{order.side}</td>
                <td>{order.quantity}</td>
                <td>{money(order.entry_price)}</td>
                <td>{money(order.stop_loss)}</td>
                <td><StatusBadge value={order.status} /></td>
                <td className="flex gap-2 py-2">
                  <button aria-label="Approve" className="rounded-md bg-moss p-2 text-white disabled:opacity-40" disabled={busy === order.id} onClick={() => decide(order.id, true)}>
                    <Check size={18} aria-hidden />
                  </button>
                  <button aria-label="Reject" className="rounded-md bg-red-700 p-2 text-white disabled:opacity-40" disabled={busy === order.id} onClick={() => decide(order.id, false)}>
                    <X size={18} aria-hidden />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="mt-4 grid gap-4 xl:grid-cols-2">
        <div className="panel overflow-x-auto p-4">
          <h3 className="font-semibold">Paper Executed</h3>
          <table className="mt-3 w-full min-w-[620px] text-left text-sm">
            <thead className="border-b border-black/10 text-black/60">
              <tr><th className="py-2">Order</th><th>Symbol</th><th>Qty</th><th>Broker ID</th><th>Updated</th></tr>
            </thead>
            <tbody>
              {executed.map((order) => (
                <tr className="border-b border-black/5" key={order.id}>
                  <td className="py-3">#{order.id}</td>
                  <td className="font-semibold">{order.symbol}</td>
                  <td>{order.quantity}</td>
                  <td>{order.broker_order_id ?? "-"}</td>
                  <td>{shortDate(order.updated_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="panel overflow-x-auto p-4">
          <h3 className="font-semibold">Blocked Trades</h3>
          <table className="mt-3 w-full min-w-[620px] text-left text-sm">
            <thead className="border-b border-black/10 text-black/60">
              <tr><th className="py-2">Symbol</th><th>Signal</th><th>Reason</th><th>Time</th></tr>
            </thead>
            <tbody>
              {blockedRisks.map((risk) => {
                const signal = signalById.get(risk.signal_id);
                return (
                  <tr className="border-b border-black/5 align-top" key={risk.id}>
                    <td className="py-3 font-semibold">{signal?.symbol ?? "-"}</td>
                    <td>{signal ? <StatusBadge value={signal.signal_type} /> : "-"}</td>
                    <td className="max-w-md text-red-800">{risk.reason}</td>
                    <td>{shortDate(risk.created_at)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </Shell>
  );
}
