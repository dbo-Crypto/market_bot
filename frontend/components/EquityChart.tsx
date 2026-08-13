"use client";

import { memo, useEffect, useMemo, useState } from "react";
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "@/lib/api";

type Point = { ts: string; equity: number };
type WindowId = "today" | "7d" | "30d" | "all";

const WINDOWS: { id: WindowId; label: string }[] = [
  { id: "today", label: "Today" },
  { id: "7d", label: "7 days" },
  { id: "30d", label: "30 days" },
  { id: "all", label: "All" },
];

function utcDayStart(): Date {
  const now = new Date();
  return new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
}

function formatTick(ts: string, window: WindowId): string {
  const stamp = new Date(ts);
  if (window === "today") {
    return stamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }
  return stamp.toLocaleDateString([], { month: "short", day: "numeric" });
}

export const EquityChart = memo(function EquityChart({ points: seed }: { points: Point[] }) {
  const [window, setWindow] = useState<WindowId>("today");
  const [remote, setRemote] = useState<Point[] | null>(null);

  useEffect(() => {
    if (window === "today") {
      setRemote(null);
      return;
    }
    let alive = true;
    async function load() {
      try {
        const next = await api.equity(window);
        if (alive) setRemote(next.points);
      } catch {
        if (alive) setRemote([]);
      }
    }
    void load();
    const id = setInterval(() => void load(), 15000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [window]);

  const data = useMemo(() => {
    const source =
      window === "today"
        ? seed.filter((point) => new Date(point.ts).getTime() >= utcDayStart().getTime())
        : (remote ?? []);
    const step = source.length > 180 ? Math.ceil(source.length / 180) : 1;
    const slim = step === 1 ? source : [...source.filter((_, i) => i % step === 0), source[source.length - 1]];
    return slim.map((point) => ({
      ...point,
      t: formatTick(point.ts, window),
    }));
  }, [window, seed, remote]);

  return (
    <div className="hairline rounded-2xl bg-ink-850/80 p-4 h-80">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div className="text-[11px] uppercase tracking-[0.18em] text-zinc-500">Equity</div>
        <div className="flex flex-wrap gap-1">
          {WINDOWS.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setWindow(item.id)}
              className={`rounded-full border px-2.5 py-1 text-[11px] ${
                window === item.id
                  ? "border-emerald-400/40 bg-emerald-400/10 text-emerald-200"
                  : "border-white/10 text-zinc-400 hover:text-zinc-200"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>
      {data.length < 2 ? (
        <div className="flex h-56 items-center justify-center text-sm text-zinc-500">
          {window === "today"
            ? "The curve appears after the first worker ticks."
            : "No equity points in this range yet."}
        </div>
      ) : (
        <ResponsiveContainer width="100%" height="88%">
          <AreaChart data={data}>
            <defs>
              <linearGradient id="eq" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#3ee08f" stopOpacity={0.35} />
                <stop offset="100%" stopColor="#3ee08f" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis dataKey="t" tick={{ fill: "#6b7280", fontSize: 11 }} axisLine={false} tickLine={false} minTickGap={24} />
            <YAxis domain={["auto", "auto"]} tick={{ fill: "#6b7280", fontSize: 11 }} axisLine={false} tickLine={false} width={48} />
            <Tooltip
              contentStyle={{ background: "#11141b", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 12 }}
              labelStyle={{ color: "#9ca3af" }}
              formatter={(value: number) => [`$${Number(value).toFixed(2)}`, "equity"]}
              labelFormatter={(_, payload) => {
                const ts = payload?.[0]?.payload?.ts;
                return ts ? new Date(ts).toLocaleString() : "";
              }}
            />
            <Area type="monotone" dataKey="equity" stroke="#3ee08f" fill="url(#eq)" strokeWidth={1.6} />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  );
});
