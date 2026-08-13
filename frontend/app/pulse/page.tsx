"use client";

import { InstrumentGrid } from "@/components/InstrumentCard";
import { DecisionTape } from "@/components/TradeTape";
import { useDesk } from "@/components/useDesk";

export default function PulsePage() {
  const { data, error } = useDesk();
  if (error && !data) return <p className="text-zinc-500">{error}</p>;
  if (!data) return <p className="text-zinc-500">Loading pulse book…</p>;
  const rows = data.instruments.filter((row) => row.sleeve === "pulse");
  const decisions = data.recent_decisions.filter((row) => row.sleeve === "pulse");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl tracking-tight">Pulse</h1>
        <p className="mt-1 max-w-2xl text-sm text-zinc-500">
          Small, loud book. BTC and ETH, 4-hour Donchian breakout, ATR stop and trail. Risk is 1% of total
          equity per trade and the whole sleeve is capped at 12%. This is the “are you a good trader” tape —
          not the retirement engine.
        </p>
      </div>
      <InstrumentGrid rows={rows} />
      <DecisionTape decisions={decisions} />
    </div>
  );
}
