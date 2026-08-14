"use client";

import { useState } from "react";
import type { GrokBlock, GrokRecommendation } from "@/lib/types";
import { api } from "@/lib/api";

const CONFIDENCE: Record<string, string> = {
  high: "text-emerald-300",
  medium: "text-amber-300",
  low: "text-zinc-500",
};

export function GrokReview({
  grok,
  onRefresh,
}: {
  grok: GrokBlock | null | undefined;
  onRefresh: (next: GrokBlock) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [applied, setApplied] = useState<string | null>(null);
  const review = grok?.review;

  async function run() {
    setBusy(true);
    setError(null);
    try {
      const next = await api.grokAnalysis();
      onRefresh(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Grok review failed");
    } finally {
      setBusy(false);
    }
  }

  async function apply(item: GrokRecommendation) {
    setApplied(null);
    setError(null);
    try {
      const numeric = Number(item.suggested);
      await api.patchSettings({
        [item.key]: Number.isFinite(numeric) && item.suggested.trim() !== "" ? numeric : item.suggested,
      });
      setApplied(item.key);
    } catch (err) {
      setError(err instanceof Error ? err.message : "could not apply setting");
    }
  }

  return (
    <section className="hairline rounded-2xl bg-ink-850/80 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-medium tracking-tight text-zinc-200">Grok desk review</h2>
          <p className="mt-1 text-sm text-zinc-500">
            Reads every completed trade, open names, knobs, and recent decisions. Suggests specific setting
            changes — does not trade.
          </p>
          {grok?.generated_at ? (
            <p className="mt-1 text-[11px] uppercase tracking-wider text-zinc-600">
              Last run {grok.generated_at.replace("T", " ").slice(0, 19)} UTC · {grok.model}
            </p>
          ) : null}
        </div>
        <button
          type="button"
          onClick={() => void run()}
          disabled={busy || grok?.available === false}
          className="rounded-full border border-white/10 px-4 py-2 text-sm text-zinc-200 hover:border-white/25 disabled:opacity-40"
        >
          {busy ? "Reading the book…" : review ? "Run again" : "Ask Grok"}
        </button>
      </div>

      {grok?.available === false ? (
        <p className="mt-4 text-sm text-amber-300/90">
          Set <span className="font-mono">XAI_API_KEY</span> on the server to enable Grok reviews.
        </p>
      ) : null}
      {error ? <p className="mt-3 text-sm text-rose-300">{error}</p> : null}

      {review ? (
        <div className="mt-5 space-y-5">
          <div>
            <div className="text-lg text-zinc-100">{review.headline}</div>
            <p className="mt-2 text-sm leading-relaxed text-zinc-300">{review.thesis}</p>
            {review.sample_caveat ? <p className="mt-2 text-sm text-zinc-500">{review.sample_caveat}</p> : null}
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <List title="Working" items={review.working} empty="Nothing stands out yet." />
            <List title="Broken" items={review.broken} empty="No clear leak in this sample." />
          </div>
          <div>
            <h3 className="text-sm text-zinc-200">What to change</h3>
            {review.recommendations.length === 0 ? (
              <p className="mt-2 text-sm text-zinc-500">No knob changes. Leave the desk as it is.</p>
            ) : (
              <ul className="mt-2 space-y-3">
                {review.recommendations.map((item) => (
                  <li key={`${item.key}-${item.suggested}`} className="rounded-xl border border-white/5 p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="font-mono text-sm text-zinc-200">
                        {item.key}{" "}
                        <span className="text-zinc-500">
                          {item.current} → {item.suggested}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={`text-[11px] uppercase tracking-wider ${CONFIDENCE[item.confidence] ?? "text-zinc-500"}`}>
                          {item.confidence}
                        </span>
                        <button
                          type="button"
                          onClick={() => void apply(item)}
                          className="rounded-full border border-white/10 px-3 py-1 text-[11px] uppercase tracking-wider text-zinc-300 hover:border-white/25"
                        >
                          {applied === item.key ? "Applied" : "Apply"}
                        </button>
                      </div>
                    </div>
                    <p className="mt-2 text-sm leading-relaxed text-zinc-400">{item.why}</p>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <List title="Leave these alone" items={review.do_not_change} empty="" />
        </div>
      ) : grok?.available ? (
        <p className="mt-4 text-sm text-zinc-500">No review yet. Ask Grok to read the full book.</p>
      ) : null}
    </section>
  );
}

function List({ title, items, empty }: { title: string; items: string[]; empty: string }) {
  if (!items.length && !empty) return null;
  return (
    <div>
      <h3 className="text-sm text-zinc-200">{title}</h3>
      {items.length === 0 ? (
        <p className="mt-2 text-sm text-zinc-500">{empty}</p>
      ) : (
        <ul className="mt-2 space-y-2">
          {items.map((item) => (
            <li key={item} className="text-sm leading-relaxed text-zinc-300">
              {item}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
