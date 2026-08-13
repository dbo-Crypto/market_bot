import Link from "next/link";
import type { DecisionRow, FillRow } from "@/lib/types";
import { formatClock, money, px, tone } from "@/lib/format";

export function DecisionTape({ decisions }: { decisions: DecisionRow[] }) {
  return (
    <div className="hairline rounded-2xl bg-ink-850/80 p-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="text-base font-medium tracking-tight text-zinc-200">Decisions</div>
        <Link href="/trades" className="text-[11px] text-zinc-500 hover:text-zinc-300">
          All trades
        </Link>
      </div>
      {decisions.length === 0 ? <div className="text-sm text-zinc-600">No decisions yet.</div> : null}
      <div className="space-y-2">
        {decisions.map((row) => (
          <div key={row.id} className="rounded-xl border border-white/5 bg-black/20 px-3 py-2">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <span className={`font-mono text-[11px] uppercase ${actionTone(row.action)}`}>{row.action}</span>
                <span className="font-mono text-sm">{row.symbol ?? "CASH"}</span>
                <span className="text-[10px] uppercase tracking-wider text-zinc-600">{row.sleeve}</span>
              </div>
              <span className="font-mono text-[11px] text-zinc-500">{formatClock(row.ts)}</span>
            </div>
            <div className="mt-1 text-xs text-zinc-500">{row.reason}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function FillTape({ fills }: { fills: FillRow[] }) {
  const running = fills.filter((row) => row.side === "buy" && row.position_status === "open");
  const closed = fills.filter((row) => !(row.side === "buy" && row.position_status === "open"));
  return (
    <div className="hairline rounded-2xl bg-ink-850/80 p-4">
      <div className="mb-3 text-base font-medium tracking-tight text-zinc-200">Fills</div>
      {fills.length === 0 ? <div className="text-sm text-zinc-600">No paper fills yet.</div> : null}
      {running.length > 0 ? (
        <Group title="Running" count={running.length}>
          {running.map((fill) => (
            <FillCard key={fill.id} fill={fill} />
          ))}
        </Group>
      ) : fills.length > 0 ? (
        <div className="text-sm text-zinc-600">No running fills.</div>
      ) : null}
      {closed.length > 0 ? (
        <Group title="Closed" count={closed.length} inset>
          {closed.map((fill) => (
            <FillCard key={fill.id} fill={fill} />
          ))}
        </Group>
      ) : null}
    </div>
  );
}

function Group({
  title,
  count,
  inset = false,
  children,
}: {
  title: string;
  count: number;
  inset?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className={inset ? "mt-4 border-t border-white/10 pt-3" : ""}>
      <div className="mb-2 flex items-center justify-between">
        <div className="text-[10px] uppercase tracking-[0.18em] text-zinc-500">{title}</div>
        <div className="font-mono text-[10px] text-zinc-600">{count}</div>
      </div>
      <div className={`space-y-2 ${inset ? "border-l border-white/10 pl-2" : ""}`}>{children}</div>
    </div>
  );
}

function FillCard({ fill }: { fill: FillRow }) {
  const pnl = fill.pnl_kind === "realized" ? fill.position_pnl : fill.pnl;
  return (
    <div className="rounded-xl border border-white/5 bg-black/20 px-3 py-2.5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className={`font-mono text-[11px] uppercase ${fill.side === "buy" ? "text-emerald-300" : "text-rose-300"}`}>
              {fill.side}
            </span>
            <span className="font-mono text-sm text-white">{fill.symbol}</span>
            <span className="text-[10px] uppercase tracking-wider text-zinc-600">{fill.sleeve}</span>
          </div>
          <div className="mt-1 font-mono text-xs text-zinc-400">
            {fill.qty} @ {px(fill.price)} · fee {money(fill.fee)}
          </div>
          <div className="mt-0.5 text-[11px] text-zinc-600">{fill.reason}</div>
        </div>
        <div className="text-right">
          <div className={`font-mono text-sm ${pnl == null ? "text-zinc-500" : tone(pnl)}`}>
            {pnl == null ? "—" : money(pnl)}
          </div>
          <div className="text-[10px] text-zinc-600">{fill.pnl_kind}</div>
        </div>
      </div>
    </div>
  );
}

function actionTone(action: string): string {
  if (action === "enter") return "text-emerald-300";
  if (action === "exit" || action === "kill") return "text-rose-300";
  if (action === "trail") return "text-amber-200";
  if (action === "cash") return "text-sky-300";
  return "text-zinc-400";
}
