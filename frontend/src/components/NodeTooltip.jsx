export default function NodeTooltip({ persona, node }) {
  if (!persona) return null;

  const left = `${(node.x / 1000) * 100}%`;
  const top = `${(node.y / 520) * 100}%`;
  const cohortLabel = node.cohort === "in-target" ? "ENGAGED" : "SKIPPED";

  return (
    <div
      className="pointer-events-none absolute z-10 w-[190px] -translate-y-full rounded-[3px] border border-line bg-panel p-2.5 shadow-[0_2px_8px_rgba(23,20,15,0.12)]"
      style={{ left, top: `calc(${top} - 10px)` }}
    >
      <div className="font-mono text-[9px] text-muted">
        {node.id.toUpperCase()} · {cohortLabel} · ROUND {node.round}
      </div>
      <div className="mt-0.5 text-[12px] font-bold text-ink">{persona.name}</div>
      {persona.interests?.length > 0 && (
        <div className="mt-1 text-[10px] leading-snug text-ink/70 line-clamp-2">
          {persona.interests.slice(0, 3).join(" · ")}
        </div>
      )}
      <div className="mt-1 text-[10px] text-ink">
        completed {persona.watched}% · {persona.action.toLowerCase()}
      </div>
      <div className="mt-1 text-[9px] uppercase tracking-wide text-muted">
        Click for reaction + AI reasoning
      </div>
    </div>
  );
}
