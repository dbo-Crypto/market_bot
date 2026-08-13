"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Blotter } from "@/lib/types";
import { money, px, tone } from "@/lib/format";
import { DecisionTape, FillTape } from "@/components/TradeTape";

export default function TradesPage() {
  const [data, setData] = useState<Blotter | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    async function load() {
      try {
        const next = await api.blotter();
        if (alive) setData(next);
      } catch (err) {
        if (alive) setError(err instanceof Error ? err.message : "failed");
      }
    }
    void load();
    const id = setInterval(() => void load(), 5000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  if (error) return <p className="text-zinc-500">{error}</p>;
  if (!data) return <p className="text-zinc-500">Loading trades…</p>;

  const current = data.positions.filter((row) => row.status === "open");
  const done = data.positions.filter((row) => row.status !== "open");

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl tracking-tight">Trades</h1>
        <p className="mt-1 text-sm text-zinc-500">Every paper position and fill — Slow and Pulse — current first.</p>
      </div>
      <PositionTable title="Current" rows={current} empty="No open positions." />
      <PositionTable title="Done" rows={done} empty="No closed trades yet." done />
      <div className="grid gap-4 lg:grid-cols-2">
        <DecisionTape decisions={data.decisions.slice(0, 20)} />
        <FillTape fills={data.fills} />
      </div>
    </div>
  );
}

function PositionTable({
  title,
  rows,
  empty,
  done = false,
}: {
  title: string;
  rows: Blotter["positions"];
  empty: string;
  done?: boolean;
}) {
  return (
    <section className="hairline overflow-hidden rounded-2xl bg-ink-850/80">
      <div className="border-b border-white/5 px-4 py-3 text-base font-medium tracking-tight text-zinc-200">
        {title}
        <span className="ml-2 font-mono text-xs text-zinc-500">{rows.length}</span>
      </div>
      {rows.length === 0 ? <div className="px-4 py-6 text-sm text-zinc-500">{empty}</div> : null}
      {rows.length > 0 ? (
        <table className="w-full text-sm">
          <thead className="text-left text-[11px] uppercase tracking-wider text-zinc-500">
            <tr>
              {["Symbol", "Sleeve", "Qty", "Avg", done ? "Exit" : "Mark", "Value", done ? "Realized" : "Latent", "Stop"].map(
                (col) => (
                  <th key={col} className="px-4 py-2 font-medium">
                    {col}
                  </th>
                ),
              )}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const pnl = done ? row.realized_pnl : (row.latent_pnl ?? 0);
              return (
                <tr key={row.id} className="border-t border-white/5">
                  <td className="px-4 py-2 font-mono">{row.symbol}</td>
                  <td className="px-4 py-2 text-zinc-400">{row.sleeve}</td>
                  <td className="px-4 py-2 font-mono">{row.qty}</td>
                  <td className="px-4 py-2 font-mono">{px(row.avg_price)}</td>
                  <td className="px-4 py-2 font-mono">{px(row.mark)}</td>
                  <td className="px-4 py-2 font-mono">{money(row.market_value)}</td>
                  <td className={`px-4 py-2 font-mono ${tone(pnl)} ${!done && pnl < 0 ? "text-rose-400" : ""}`}>
                    {money(pnl)}
                  </td>
                  <td className="px-4 py-2 font-mono text-zinc-400">{row.stop ? px(row.stop) : "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      ) : null}
    </section>
  );
}
