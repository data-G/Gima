"use client";

import { useEffect, useMemo, useState } from "react";
import { PlayCircle, Plus, Trash2 } from "lucide-react";
import { Shell } from "@/components/Shell";
import { StatusBadge } from "@/components/StatusBadge";
import { api } from "@/lib/api";
import { confidence, money } from "@/lib/format";
import type { MarketData, Signal, WatchlistItem } from "@/types/api";

export default function WatchlistPage() {
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [signals, setSignals] = useState<Signal[]>([]);
  const [prices, setPrices] = useState<Record<string, MarketData>>({});
  const [symbol, setSymbol] = useState("");
  const [assetType, setAssetType] = useState<"stock" | "etf">("stock");
  const [busySymbol, setBusySymbol] = useState<string | null>(null);

  async function load() {
    const [watchlist, signalRows] = await Promise.all([api.watchlist(), api.signals()]);
    setItems(watchlist);
    setSignals(signalRows);
    const activePrices = await Promise.all(
      watchlist.filter((item) => item.active).map((item) => api.brokerMarketData(item.symbol).catch(() => ({ symbol: item.symbol })))
    );
    setPrices(Object.fromEntries(activePrices.map((price) => [price.symbol, price])));
  }

  async function add() {
    if (!symbol.trim()) return;
    await api.addWatchlist(symbol, assetType);
    setSymbol("");
    await load();
  }

  async function runSignal(item: WatchlistItem) {
    setBusySymbol(item.symbol);
    try {
      await api.runSignal(item.symbol);
      await load();
    } finally {
      setBusySymbol(null);
    }
  }

  useEffect(() => {
    load().catch(console.error);
  }, []);

  const latestSignalBySymbol = useMemo(() => {
    const map = new Map<string, Signal>();
    for (const signal of signals) {
      if (!map.has(signal.symbol)) map.set(signal.symbol, signal);
    }
    return map;
  }, [signals]);

  return (
    <Shell>
      <div className="mb-4">
        <h2 className="text-2xl font-semibold">Watchlist</h2>
        <p className="text-sm text-black/60">Stocks and ETFs only for v1. Paper trading only.</p>
      </div>
      <div className="panel p-4">
        <div className="grid gap-3 md:grid-cols-[1fr_160px_auto]">
          <input className="rounded-md border border-black/15 bg-white px-3 py-2 uppercase" placeholder="AAPL" value={symbol} onChange={(event) => setSymbol(event.target.value)} />
          <select className="rounded-md border border-black/15 bg-white px-3 py-2" value={assetType} onChange={(event) => setAssetType(event.target.value as "stock" | "etf")}>
            <option value="stock">Stock</option>
            <option value="etf">ETF</option>
          </select>
          <button className="inline-flex items-center justify-center gap-2 rounded-md bg-moss px-4 py-2 font-medium text-white" onClick={add}>
            <Plus size={18} aria-hidden />
            Add
          </button>
        </div>

        <div className="mt-5 grid gap-3 lg:grid-cols-2">
          {items.map((item) => {
            const latest = latestSignalBySymbol.get(item.symbol);
            const price = prices[item.symbol];
            return (
              <article className="rounded-md border border-black/10 bg-white p-4" key={item.id}>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <strong className="text-lg">{item.symbol}</strong>
                      <StatusBadge value={item.active ? "ACTIVE" : "INACTIVE"} />
                    </div>
                    <p className="mt-1 text-sm text-black/60">{item.asset_type.toUpperCase()} · {item.exchange}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-black/60">Current Price</p>
                    <strong>{price?.last ? money(price.last) : "-"}</strong>
                  </div>
                </div>
                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  <div className="rounded-md bg-slate-50 p-3">
                    <p className="text-xs text-black/50">Latest Signal</p>
                    <div className="mt-2">{latest ? <StatusBadge value={`${latest.signal_type} · ${confidence(latest.confidence)}`} /> : <span className="text-sm text-black/50">No signal yet</span>}</div>
                    <p className="mt-2 line-clamp-2 text-sm text-black/65">{latest?.explanation ?? "Run a signal to generate a human-readable explanation."}</p>
                  </div>
                  <div className="flex flex-wrap items-end justify-end gap-2">
                    <button className="inline-flex items-center gap-2 rounded-md border border-black/10 px-3 py-2 text-sm" onClick={() => api.updateWatchlist(item.id, { active: !item.active }).then(load)}>
                      {item.active ? "Deactivate" : "Activate"}
                    </button>
                    <button className="inline-flex items-center gap-2 rounded-md bg-moss px-3 py-2 text-sm font-medium text-white disabled:opacity-50" onClick={() => runSignal(item)} disabled={!item.active || busySymbol === item.symbol}>
                      <PlayCircle size={16} aria-hidden />
                      Signal
                    </button>
                    <button aria-label={`Remove ${item.symbol}`} className="rounded-md bg-red-700 p-2 text-white" onClick={() => api.removeWatchlist(item.id).then(load)}>
                      <Trash2 size={16} aria-hidden />
                    </button>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      </div>
    </Shell>
  );
}
