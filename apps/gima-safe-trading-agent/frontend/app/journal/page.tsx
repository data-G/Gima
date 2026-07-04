"use client";

import { useEffect, useMemo, useState } from "react";
import { Download } from "lucide-react";
import { Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import { csvEscape, money, percent, shortDate } from "@/lib/format";
import type { Signal, TradeJournal, TradeOrder } from "@/types/api";

export default function JournalPage() {
  const [rows, setRows] = useState<TradeJournal[]>([]);
  const [orders, setOrders] = useState<TradeOrder[]>([]);
  const [signals, setSignals] = useState<Signal[]>([]);

  async function load() {
    const [journalRows, orderRows, signalRows] = await Promise.all([api.journal(), api.orders(), api.signals()]);
    setRows(journalRows);
    setOrders(orderRows);
    setSignals(signalRows);
  }

  useEffect(() => {
    load().catch(console.error);
  }, []);

  const orderById = useMemo(() => new Map(orders.map((order) => [order.id, order])), [orders]);
  const signalById = useMemo(() => new Map(signals.map((signal) => [signal.id, signal])), [signals]);

  function exportCsv() {
    const header = ["created_at", "symbol", "entry_price", "exit_price", "quantity", "pnl", "pnl_percent", "strategy_name", "notes"];
    const lines = rows.map((row) => {
      const order = row.order_id ? orderById.get(row.order_id) : undefined;
      const signal = order ? signalById.get(order.signal_id) : undefined;
      return [
        row.created_at,
        row.symbol,
        row.entry_price ?? "",
        row.exit_price ?? "",
        row.quantity ?? "",
        row.pnl,
        row.pnl_percent,
        signal?.strategy_name ?? "",
        row.notes
      ].map(csvEscape).join(",");
    });
    const blob = new Blob([[header.join(","), ...lines].join("\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "gima-trade-journal.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <Shell>
      <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Trade Journal</h2>
          <p className="text-sm text-black/60">History, P/L, notes, and strategy context for paper trading activity.</p>
        </div>
        <button className="inline-flex items-center gap-2 rounded-md border border-black/10 bg-white px-3 py-2 text-sm" onClick={exportCsv}>
          <Download size={16} aria-hidden />
          Export CSV
        </button>
      </div>

      <section className="panel overflow-x-auto p-4">
        <table className="w-full min-w-[960px] text-left text-sm">
          <thead className="border-b border-black/10 text-black/60">
            <tr><th className="py-2">Time</th><th>Symbol</th><th>Entry</th><th>Exit</th><th>Qty</th><th>P/L</th><th>P/L %</th><th>Strategy</th><th>Notes</th></tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const order = row.order_id ? orderById.get(row.order_id) : undefined;
              const signal = order ? signalById.get(order.signal_id) : undefined;
              const pnlTone = row.pnl < 0 ? "text-red-700" : "text-green-700";
              return (
                <tr className="border-b border-black/5 align-top" key={row.id}>
                  <td className="py-3">{shortDate(row.created_at)}</td>
                  <td className="font-semibold">{row.symbol}</td>
                  <td>{row.entry_price == null ? "-" : money(row.entry_price)}</td>
                  <td>{row.exit_price == null ? "-" : money(row.exit_price)}</td>
                  <td>{row.quantity ?? "-"}</td>
                  <td className={pnlTone}>{money(row.pnl)}</td>
                  <td className={pnlTone}>{percent(row.pnl_percent)}</td>
                  <td>{signal?.strategy_name ?? "-"}</td>
                  <td className="max-w-lg text-black/70">{row.notes}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>
    </Shell>
  );
}
