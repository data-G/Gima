"use client";

import { useEffect, useState } from "react";
import { Save, ShieldOff, ShieldCheck } from "lucide-react";
import { SafetyNotice } from "@/components/SafetyNotice";
import { Shell } from "@/components/Shell";
import { StatusBadge } from "@/components/StatusBadge";
import { api } from "@/lib/api";
import type { RiskSettings, SafetyState } from "@/types/api";

type RiskForm = Pick<
  RiskSettings,
  "max_risk_per_trade_percent" | "max_daily_loss_percent" | "max_weekly_loss_percent" | "max_position_concentration_percent"
> & {
  live_trading_enabled: false;
};

export default function RiskSettingsPage() {
  const [settings, setSettings] = useState<RiskSettings | null>(null);
  const [safety, setSafety] = useState<SafetyState | null>(null);
  const [form, setForm] = useState<RiskForm>({
    max_risk_per_trade_percent: 0.5,
    max_daily_loss_percent: 2,
    max_weekly_loss_percent: 5,
    max_position_concentration_percent: 10,
    live_trading_enabled: false
  });
  const [busy, setBusy] = useState(false);

  async function load() {
    const [risk, safe] = await Promise.all([api.riskSettings(1), api.safety()]);
    setSettings(risk);
    setSafety(safe);
    setForm({
      max_risk_per_trade_percent: risk.max_risk_per_trade_percent,
      max_daily_loss_percent: risk.max_daily_loss_percent,
      max_weekly_loss_percent: risk.max_weekly_loss_percent,
      max_position_concentration_percent: risk.max_position_concentration_percent,
      live_trading_enabled: false
    });
  }

  async function save() {
    setBusy(true);
    try {
      await api.updateRiskSettings(1, form);
      await load();
    } finally {
      setBusy(false);
    }
  }

  async function toggleKillSwitch() {
    setBusy(true);
    try {
      await api.setKillSwitch(!safety?.kill_switch_active, "Risk settings operator action");
      await load();
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    load().catch(console.error);
  }, []);

  function updateNumber(key: keyof RiskForm, value: string) {
    setForm((current) => ({ ...current, [key]: Number(value) }));
  }

  return (
    <Shell>
      <div className="mb-4">
        <h2 className="text-2xl font-semibold">Risk Settings</h2>
        <p className="text-sm text-black/60">Controls apply to paper trading workflows. Live trading remains disabled unless explicitly enabled in backend environment and user settings.</p>
      </div>

      <div className="mb-4">
        <SafetyNotice />
      </div>

      <section className="grid gap-4 lg:grid-cols-[1fr_0.8fr]">
        <div className="panel p-4">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="text-sm font-medium">
              Max risk per trade %
              <input className="mt-1 w-full rounded-md border border-black/15 bg-white px-3 py-2" type="number" step="0.1" value={form.max_risk_per_trade_percent} onChange={(event) => updateNumber("max_risk_per_trade_percent", event.target.value)} />
            </label>
            <label className="text-sm font-medium">
              Max daily loss %
              <input className="mt-1 w-full rounded-md border border-black/15 bg-white px-3 py-2" type="number" step="0.1" value={form.max_daily_loss_percent} onChange={(event) => updateNumber("max_daily_loss_percent", event.target.value)} />
            </label>
            <label className="text-sm font-medium">
              Max weekly loss %
              <input className="mt-1 w-full rounded-md border border-black/15 bg-white px-3 py-2" type="number" step="0.1" value={form.max_weekly_loss_percent} onChange={(event) => updateNumber("max_weekly_loss_percent", event.target.value)} />
            </label>
            <label className="text-sm font-medium">
              Max position concentration %
              <input className="mt-1 w-full rounded-md border border-black/15 bg-white px-3 py-2" type="number" step="0.1" value={form.max_position_concentration_percent} onChange={(event) => updateNumber("max_position_concentration_percent", event.target.value)} />
            </label>
          </div>

          <div className="mt-5 rounded-md border border-red-200 bg-red-50 p-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <h3 className="font-semibold text-red-900">Live Trading Toggle</h3>
                <p className="text-sm text-red-800">Disabled in v1. The backend rejects attempts to enable this flag.</p>
              </div>
              <label className="inline-flex items-center gap-2 text-sm font-medium text-red-900">
                <input type="checkbox" checked={false} disabled readOnly />
                User live flag
              </label>
            </div>
          </div>

          <button className="mt-5 inline-flex items-center gap-2 rounded-md bg-moss px-4 py-2 font-medium text-white disabled:opacity-50" onClick={save} disabled={busy}>
            <Save size={17} aria-hidden />
            Save Risk Settings
          </button>
        </div>

        <aside className="grid gap-4">
          <div className="panel p-4">
            <h3 className="font-semibold">Kill Switch Status</h3>
            <div className="mt-3"><StatusBadge value={safety?.kill_switch_active ? "ACTIVE" : "INACTIVE"} /></div>
            <p className="mt-2 text-sm text-black/60">{safety?.reason ?? "Kill switch blocks all order execution."}</p>
            <button className={`mt-4 inline-flex items-center gap-2 rounded-md px-4 py-2 font-medium text-white ${safety?.kill_switch_active ? "bg-moss" : "bg-red-700"}`} onClick={toggleKillSwitch} disabled={busy}>
              {safety?.kill_switch_active ? <ShieldCheck size={17} aria-hidden /> : <ShieldOff size={17} aria-hidden />}
              {safety?.kill_switch_active ? "Deactivate" : "Activate"}
            </button>
          </div>
          <div className="panel p-4">
            <h3 className="font-semibold">Current Limits</h3>
            <dl className="mt-3 grid gap-2 text-sm">
              <div className="flex justify-between gap-3"><dt>Trade risk</dt><dd>{settings?.max_risk_per_trade_percent ?? 0}%</dd></div>
              <div className="flex justify-between gap-3"><dt>Daily loss</dt><dd>{settings?.max_daily_loss_percent ?? 0}%</dd></div>
              <div className="flex justify-between gap-3"><dt>Weekly loss</dt><dd>{settings?.max_weekly_loss_percent ?? 0}%</dd></div>
              <div className="flex justify-between gap-3"><dt>Concentration</dt><dd>{settings?.max_position_concentration_percent ?? 0}%</dd></div>
            </dl>
          </div>
        </aside>
      </section>
    </Shell>
  );
}
