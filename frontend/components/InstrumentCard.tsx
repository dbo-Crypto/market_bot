import type { Instrument } from "@/lib/types";
import { money, pct, px, tone } from "@/lib/format";
import { Spark } from "./Spark";

export function InstrumentCard({ row }: { row: Instrument }) {
  const pos = row.position;
  const feat = row.features || {};
  const slow = row.sleeve === "slow";
  return (
    <div className="hairline rounded-2xl bg-ink-850/80 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.18em] text-zinc-500">{row.name}</div>
          <div className="mt-1 font-mono text-lg">{row.symbol}</div>
        </div>
        <Spark values={row.spark} />
      </div>
      <div className="mt-3 flex items-end justify-between">
        <div>
          <div className="font-mono text-2xl">{px(row.last, 2)}</div>
          {slow ? (
            <div className={`mt-1 text-xs ${feat.eligible ? "text-emerald-300" : "text-zinc-500"}`}>
              12−1 {pct(feat.ret_12_1)} · {feat.above_sma ? "above SMA" : "below SMA"}
            </div>
          ) : row.sleeve === "snap" ? (
            <div className="mt-1 text-xs text-zinc-500">
              RSI {feat.rsi != null ? feat.rsi.toFixed(0) : "—"}
              {feat.action ? ` · ${feat.action}` : ""}
            </div>
          ) : (
            <div className="mt-1 text-xs text-zinc-500">
              {feat.action ?? "—"}
              {feat.channel_high != null ? ` · ch ${px(feat.channel_high)}` : ""}
            </div>
          )}
        </div>
        {pos ? (
          <div className="text-right">
            <div className={`font-mono text-sm ${tone(pos.latent_pnl)}`}>{money(pos.latent_pnl)}</div>
            <div className="text-[11px] text-zinc-500">
              {pos.qty} @ {px(pos.avg_price)}
            </div>
            {pos.stop ? <div className="text-[11px] text-amber-200/80">stop {px(pos.stop)}</div> : null}
          </div>
        ) : (
          <div className="text-xs text-zinc-600">flat</div>
        )}
      </div>
      {feat.reason ? <div className="mt-3 text-xs leading-relaxed text-zinc-500">{feat.reason}</div> : null}
    </div>
  );
}

export function InstrumentGrid({ rows }: { rows: Instrument[] }) {
  if (!rows.length) {
    return <div className="text-sm text-zinc-500">No instruments yet. The worker seeds them on first tick.</div>;
  }
  return (
    <div className="grid gap-3 md:grid-cols-2">
      {rows.map((row) => (
        <InstrumentCard key={row.id} row={row} />
      ))}
    </div>
  );
}
