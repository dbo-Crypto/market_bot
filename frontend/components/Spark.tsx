export function Spark({ values, className = "" }: { values: number[]; className?: string }) {
  if (values.length < 2) {
    return <div className={`h-10 ${className}`} />;
  }
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const w = 120;
  const h = 40;
  const points = values
    .map((value, i) => {
      const x = (i / (values.length - 1)) * w;
      const y = h - ((value - min) / span) * (h - 4) - 2;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  const up = values[values.length - 1] >= values[0];
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className={`h-10 w-28 ${className}`} aria-hidden>
      <polyline fill="none" stroke={up ? "#3ee08f" : "#ff5d73"} strokeWidth="1.6" points={points} />
    </svg>
  );
}
