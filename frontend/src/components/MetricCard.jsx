export default function MetricCard({ label, value, unit, sub, bar }) {
  return (
    <div className="p-3.5">
      <div className="label-micro">{label}</div>
      <div className="mt-1.5 flex items-baseline gap-0.5">
        <span className="text-[22px] font-bold leading-none text-ink">
          {value}
        </span>
        {unit && (
          <span className="text-[11px] font-medium text-muted">{unit}</span>
        )}
      </div>
      {bar && (
        <div className="mt-2 flex h-[3px] w-full overflow-hidden rounded-full bg-line">
          <div
            className="h-full bg-node-blue"
            style={{ width: `${bar.inPct}%` }}
          />
          <div
            className="h-full bg-node-orange"
            style={{ width: `${bar.outPct}%` }}
          />
        </div>
      )}
      {sub && <p className="mt-1.5 text-[10px] leading-snug text-muted">{sub}</p>}
    </div>
  );
}
