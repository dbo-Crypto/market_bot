"use client";

import { EquityChart } from "@/components/EquityChart";
import { InstrumentGrid } from "@/components/InstrumentCard";
import { Stat } from "@/components/Stat";
import { DecisionTape, FillTape } from "@/components/TradeTape";
import { useDesk } from "@/components/useDesk";
import { money, pct } from "@/lib/format";

export default function OverviewPage() {
  const { data, error } = useDesk();

  if (error && !data) return <Empty title="API offline" body={error} />;
  if (!data) return <Empty title="Connecting" body="Loading the paper desk…" />;

  const slow = data.instruments.filter((row) => row.sleeve === "slow");
  const snap = data.instruments.filter((row) => row.sleeve === "snap");
  const pulse = data.instruments.filter((row) => row.sleeve === "pulse");

  return (
    <div className="space-y-6">
      <div className="grid gap-3 md:grid-cols-5">
        <Stat label="Equity" value={money(data.account.equity)} hint={`${money(data.account.cash)} cash`} />
        <Stat label="Today" value={money(data.account.daily_pnl)} signed raw={data.account.daily_pnl} hint={pct(data.account.daily_pnl_pct)} />
        <Stat label="Latent" value={money(data.account.latent_pnl)} signed raw={data.account.latent_pnl} hint="Mark − avg" />
        <Stat label="Realized" value={money(data.account.realized_pnl)} signed raw={data.account.realized_pnl} />
        <Stat
          label="Hit rate"
          value={data.stats.win_rate == null ? "—" : pct(data.stats.win_rate, 0)}
          hint={`${data.stats.wins}W / ${data.stats.losses}L`}
        />
      </div>
      <EquityChart points={data.equity} />
      <section>
        <div className="mb-3 flex items-end justify-between">
          <h2 className="text-sm uppercase tracking-[0.2em] text-zinc-500">Slow</h2>
          <a href="/slow" className="text-xs text-zinc-500 hover:text-zinc-300">
            Dual momentum · {slow.length}
          </a>
        </div>
        <InstrumentGrid rows={slow} />
      </section>
      <section>
        <div className="mb-3 flex items-end justify-between">
          <h2 className="text-sm uppercase tracking-[0.2em] text-zinc-500">Snap</h2>
          <a href="/snap" className="text-xs text-zinc-500 hover:text-zinc-300">
            QQQ washout · {snap.length}
          </a>
        </div>
        <InstrumentGrid rows={snap} />
      </section>
      <section>
        <div className="mb-3 flex items-end justify-between">
          <h2 className="text-sm uppercase tracking-[0.2em] text-zinc-500">Pulse</h2>
          <a href="/pulse" className="text-xs text-zinc-500 hover:text-zinc-300">
            Crypto breakout · {pulse.length}
          </a>
        </div>
        <InstrumentGrid rows={pulse} />
      </section>
      <section className="grid gap-4 lg:grid-cols-2">
        <DecisionTape decisions={data.recent_decisions} />
        <FillTape fills={data.recent_fills} />
      </section>
      {data.account.last_error ? (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
          {data.account.last_error}
        </div>
      ) : null}
    </div>
  );
}

function Empty({ title, body }: { title: string; body: string }) {
  return (
    <div className="hairline rounded-2xl p-10 text-center">
      <div className="text-lg">{title}</div>
      <div className="mt-2 text-sm text-zinc-500">{body}</div>
    </div>
  );
}
