export function money(value: number, digits = 2): string {
  const sign = value < 0 ? "-" : "";
  return `${sign}$${Math.abs(value).toFixed(digits)}`;
}

export function pct(value: number | null | undefined, digits = 1): string {
  if (value == null || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

export function px(value: number | null | undefined, digits = 2): string {
  if (value == null || Number.isNaN(value)) return "—";
  if (Math.abs(value) >= 1000) return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  if (Math.abs(value) >= 1) return value.toFixed(digits);
  return value.toPrecision(4);
}

export function clsx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

export function tone(value: number): string {
  if (value > 0.0001) return "text-emerald-400";
  if (value < -0.0001) return "text-rose-400";
  return "text-zinc-400";
}

export function formatClock(iso: string | null | undefined): string {
  if (!iso) return "—";
  const stamp = new Date(iso);
  if (Number.isNaN(stamp.getTime())) return iso.slice(11, 19);
  return stamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export function holdLabel(hours: number | null | undefined): string {
  if (hours == null) return "—";
  if (hours < 24) return `${hours.toFixed(1)}h`;
  return `${(hours / 24).toFixed(1)}d`;
}
