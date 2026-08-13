"use client";

import { InstrumentGrid } from "@/components/InstrumentCard";
import { DecisionTape } from "@/components/TradeTape";
import { useDesk } from "@/components/useDesk";

export default function SlowPage() {
  const { data, error } = useDesk();
  if (error && !data) return <p className="text-zinc-500">{error}</p>;
  if (!data) return <p className="text-zinc-500">Loading slow book…</p>;
  const rows = data.instruments.filter((row) => row.sleeve === "slow");
  const decisions = data.recent_decisions.filter((row) => row.sleeve === "slow");
  const held = rows.find((row) => row.position);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl tracking-tight">Slow</h1>
        <p className="mt-1 max-w-2xl text-sm text-zinc-500">
          Dual momentum on two ETFs. Each month the bot holds the one with the better 12−1 return, but only if
          price is above its 10-month average. Otherwise it sits in cash. This sleeve uses about 85% of the
          paper book and should barely move.
        </p>
      </div>
      <div className="hairline rounded-2xl bg-ink-850/80 px-4 py-3 text-sm text-zinc-300">
        Now holding <span className="font-mono text-white">{held?.symbol ?? "CASH"}</span>
        {held?.features.ret_12_1 != null ? (
          <span className="text-zinc-500"> · 12−1 {(held.features.ret_12_1 * 100).toFixed(1)}%</span>
        ) : null}
      </div>
      <InstrumentGrid rows={rows} />
      <DecisionTape decisions={decisions} />
    </div>
  );
}
