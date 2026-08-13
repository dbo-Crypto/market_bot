"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useDesk } from "@/components/useDesk";

const FIELDS: { key: string; label: string; hint: string; step?: string }[] = [
  { key: "slow_sleeve_fraction", label: "Slow sleeve", hint: "Share of equity for the monthly ETF book", step: "0.01" },
  { key: "snap_sleeve_fraction", label: "Snap sleeve", hint: "Share of equity for QQQ washouts", step: "0.01" },
  { key: "snap_rsi_buy", label: "Snap RSI buy", hint: "Enter when RSI(2) is at or below this", step: "1" },
  { key: "snap_max_days", label: "Snap max days", hint: "Force exit after this many sessions", step: "1" },
  { key: "snap_stop_atr", label: "Snap stop × ATR", hint: "Initial stop distance on QQQ", step: "0.1" },
  { key: "snap_risk_fraction", label: "Snap risk / trade", hint: "Equity at risk to the Snap stop", step: "0.001" },
  { key: "pulse_sleeve_fraction", label: "Pulse sleeve", hint: "Share of equity for crypto, hard cap", step: "0.01" },
  { key: "pulse_risk_fraction", label: "Pulse risk / trade", hint: "Equity at risk to the ATR stop", step: "0.001" },
  { key: "pulse_donchian", label: "Donchian length", hint: "4h bars for the breakout high", step: "1" },
  { key: "pulse_exit_channel", label: "Exit channel", hint: "4h bars for the breakdown low", step: "1" },
  { key: "pulse_atr", label: "ATR length", hint: "4h bars", step: "1" },
  { key: "pulse_stop_atr", label: "Stop × ATR", hint: "Initial stop distance", step: "0.1" },
  { key: "pulse_trail_atr", label: "Trail × ATR", hint: "Ratcheting stop", step: "0.1" },
  { key: "daily_loss_halt", label: "Daily loss halt", hint: "Pause the worker at this drawdown", step: "0.01" },
  { key: "poll_interval_seconds", label: "Loop", hint: "Worker cycle, seconds", step: "5" },
];

export default function ControlPage() {
  const { data, refresh } = useDesk(8000);
  const [form, setForm] = useState<Record<string, string>>({});
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    if (data?.settings) setForm(data.settings);
  }, [data]);

  async function save() {
    const body: Record<string, string | number> = {};
    for (const field of FIELDS) {
      if (form[field.key] != null) body[field.key] = Number(form[field.key]);
    }
    if (form.slow_symbols) body.slow_symbols = form.slow_symbols;
    if (form.snap_symbols) body.snap_symbols = form.snap_symbols;
    if (form.pulse_symbols) body.pulse_symbols = form.pulse_symbols;
    await api.patchSettings(body);
    setStatus("Saved. The worker picks this up on the next cycle.");
    await refresh();
  }

  async function act(action: string) {
    await api.control(action);
    setStatus(`Issued ${action}.`);
    await refresh();
  }

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl tracking-tight">Control</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Paper only. These knobs never place a live broker order. Reset wipes the virtual ledger back to $1,000.
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        <button className={btn()} onClick={() => void act("start")}>
          Start
        </button>
        <button className={btn()} onClick={() => void act("pause")}>
          Pause
        </button>
        <button className={btn("border-rose-500/40 text-rose-300")} onClick={() => void act("kill")}>
          Kill
        </button>
        <button className={btn("border-amber-500/40 text-amber-200")} onClick={() => void act("reset")}>
          Reset bankroll
        </button>
      </div>
      <div className="hairline space-y-4 rounded-2xl bg-ink-850/80 p-5">
        {FIELDS.map((field) => (
          <label key={field.key} className="grid grid-cols-[14rem_1fr] items-center gap-4">
            <span>
              <span className="block text-sm">{field.label}</span>
              <span className="block text-xs text-zinc-500">{field.hint}</span>
            </span>
            <input
              className="rounded-lg border border-white/10 bg-black/30 px-3 py-2 font-mono text-sm outline-none focus:border-emerald-400/40"
              type="number"
              step={field.step}
              value={form[field.key] ?? ""}
              onChange={(event) => setForm({ ...form, [field.key]: event.target.value })}
            />
          </label>
        ))}
        <label className="grid grid-cols-[14rem_1fr] items-center gap-4">
          <span>
            <span className="block text-sm">Slow symbols</span>
            <span className="block text-xs text-zinc-500">SPY, EZU, QQQ, IWM, VGK</span>
          </span>
          <input
            className="rounded-lg border border-white/10 bg-black/30 px-3 py-2 font-mono text-sm outline-none focus:border-emerald-400/40"
            value={form.slow_symbols ?? "SPY,EZU"}
            onChange={(event) => setForm({ ...form, slow_symbols: event.target.value })}
          />
        </label>
        <label className="grid grid-cols-[14rem_1fr] items-center gap-4">
          <span>
            <span className="block text-sm">Snap symbols</span>
            <span className="block text-xs text-zinc-500">QQQ (Nasdaq 100)</span>
          </span>
          <input
            className="rounded-lg border border-white/10 bg-black/30 px-3 py-2 font-mono text-sm outline-none focus:border-emerald-400/40"
            value={form.snap_symbols ?? "QQQ"}
            onChange={(event) => setForm({ ...form, snap_symbols: event.target.value })}
          />
        </label>
        <label className="grid grid-cols-[14rem_1fr] items-center gap-4">
          <span>
            <span className="block text-sm">Pulse symbols</span>
            <span className="block text-xs text-zinc-500">BTCUSDT, ETHUSDT, SOLUSDT</span>
          </span>
          <input
            className="rounded-lg border border-white/10 bg-black/30 px-3 py-2 font-mono text-sm outline-none focus:border-emerald-400/40"
            value={form.pulse_symbols ?? "BTCUSDT,ETHUSDT"}
            onChange={(event) => setForm({ ...form, pulse_symbols: event.target.value })}
          />
        </label>
        <button className={btn("border-emerald-400/30 bg-emerald-400/10 text-emerald-200")} onClick={() => void save()}>
          Save settings
        </button>
        {status ? <div className="text-sm text-zinc-400">{status}</div> : null}
      </div>
    </div>
  );
}

function btn(extra = "") {
  return `rounded-full border border-white/10 px-4 py-2 text-sm hover:bg-white/5 ${extra}`;
}
