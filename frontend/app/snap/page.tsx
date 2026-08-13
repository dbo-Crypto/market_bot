"use client";

import { InstrumentGrid } from "@/components/InstrumentCard";
import { DecisionTape } from "@/components/TradeTape";
import { useDesk } from "@/components/useDesk";

export default function SnapPage() {
  const { data, error } = useDesk();
  if (error && !data) return <p className="text-zinc-500">{error}</p>;
  if (!data) return <p className="text-zinc-500">Loading snap book…</p>;
  const rows = data.instruments.filter((row) => row.sleeve === "snap");
  const decisions = data.recent_decisions.filter((row) => row.sleeve === "snap");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl tracking-tight">Snap</h1>
        <p className="mt-1 max-w-2xl text-sm text-zinc-500">
          Small, faster stock book. QQQ only. Buys a 2-day washout (RSI very low) only if Nasdaq is still
          above its 200-day average. Sells when it bounces back to the 5-day average, after 5 sessions, or
          at the ATR stop. About 8% of the paper book. This is the aggressive traditional sleeve — not Slow.
        </p>
      </div>
      <InstrumentGrid rows={rows} />
      <DecisionTape decisions={decisions} />
    </div>
  );
}
