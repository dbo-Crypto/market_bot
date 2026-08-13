"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Analysis, AnalysisBucket } from "@/lib/types";
import { holdLabel, money, pct, tone } from "@/lib/format";

export default function AnalysisPage() {
  const [data, setData] = useState<Analysis | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    async function load() {
      try {
        const next = await api.analysis();
        if (alive) setData(next);
      } catch (err) {
        if (alive) setError(err instanceof Error ? err.message : "failed");
      }
    }
    void load();
    const id = setInterval(() => void load(), 15000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  if (error) return <p className="text-zinc-500">{error}</p>;
  if (!data) return <p className="text-zinc-500">Loading analysis…</p>;
  const s = data.summary;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl tracking-tight">Analysis</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Last {data.window} completed trades. {data.analyzed} in this window. Notes only fire when the sample
          actually supports a change.
        </p>
      </div>
      <div className="grid gap-3 md:grid-cols-4">
        <Box label="Win rate" value={s.win_rate == null ? "—" : pct(s.win_rate, 0)} hint={`${s.wins}W / ${s.losses}L / ${s.flats} flat`} />
        <Box label="Net P&L" value={money(s.pnl)} hint="realized" raw={s.pnl} />
        <Box label="Expectancy" value={s.expectancy == null ? "—" : money(s.expectancy)} hint="per completed trade" raw={s.expectancy ?? 0} />
        <Box
          label="Avg win / loss"
          value={
            s.avg_win == null && s.avg_loss == null
              ? "—"
              : `${s.avg_win == null ? "—" : money(s.avg_win)} / ${s.avg_loss == null ? "—" : money(s.avg_loss)}`
          }
        />
      </div>
      <section className="hairline rounded-2xl bg-ink-850/80 p-5">
        <h2 className="text-base font-medium tracking-tight text-zinc-200">What to change</h2>
        <ul className="mt-3 space-y-2">
          {data.notes.map((note) => (
            <li key={note} className="text-sm leading-relaxed text-zinc-300">
              {note}
            </li>
          ))}
        </ul>
      </section>
      <div className="grid gap-4 lg:grid-cols-2">
        <BucketTable title="By sleeve" rows={data.by_sleeve} />
        <BucketTable title="By symbol" rows={data.by_symbol} />
        <BucketTable title="By exit" rows={data.by_exit} />
      </div>
      <section className="hairline overflow-hidden rounded-2xl bg-ink-850/80">
        <div className="border-b border-white/5 px-4 py-3 text-base font-medium tracking-tight text-zinc-200">
          The {data.analyzed} trades
        </div>
        <table className="w-full text-sm">
          <thead className="text-left text-[11px] uppercase tracking-wider text-zinc-500">
            <tr>
              {["Result", "Symbol", "Sleeve", "Exit", "P&L", "Hold"].map((col) => (
                <th key={col} className="px-4 py-2 font-medium">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.trades.map((row) => (
              <tr key={row.id} className="border-t border-white/5">
                <td className={`px-4 py-2 font-mono ${tone(row.realized_pnl)}`}>{row.result}</td>
                <td className="px-4 py-2 font-mono">{row.symbol}</td>
                <td className="px-4 py-2 text-zinc-400">{row.sleeve}</td>
                <td className="px-4 py-2 text-zinc-400">{row.exit_reason}</td>
                <td className={`px-4 py-2 font-mono ${tone(row.realized_pnl)}`}>{money(row.realized_pnl)}</td>
                <td className="px-4 py-2 font-mono text-zinc-400">{holdLabel(row.hold_hours)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

function Box({ label, value, hint, raw }: { label: string; value: string; hint?: string; raw?: number }) {
  return (
    <div className="hairline rounded-2xl bg-ink-850/80 p-4">
      <div className="text-[11px] uppercase tracking-[0.18em] text-zinc-500">{label}</div>
      <div className={`mt-2 font-mono text-2xl ${raw != null ? tone(raw) : ""}`}>{value}</div>
      {hint ? <div className="mt-1 text-xs text-zinc-500">{hint}</div> : null}
    </div>
  );
}

function BucketTable({ title, rows }: { title: string; rows: AnalysisBucket[] }) {
  return (
    <section className="hairline overflow-hidden rounded-2xl bg-ink-850/80">
      <div className="border-b border-white/5 px-4 py-3 text-sm text-zinc-300">{title}</div>
      <table className="w-full text-sm">
        <thead className="text-left text-[11px] uppercase tracking-wider text-zinc-500">
          <tr>
            {["Bucket", "N", "Win", "P&L"].map((col) => (
              <th key={col} className="px-4 py-2 font-medium">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.key} className="border-t border-white/5">
              <td className="px-4 py-2">{row.key}</td>
              <td className="px-4 py-2 font-mono">{row.trades}</td>
              <td className="px-4 py-2 font-mono">{row.win_rate == null ? "—" : pct(row.win_rate, 0)}</td>
              <td className={`px-4 py-2 font-mono ${tone(row.pnl)}`}>{money(row.pnl)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
