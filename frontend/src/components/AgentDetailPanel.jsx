const ACTION_STYLE = {
  LIKE: "border-node-blue text-node-blue",
  SHARE: "border-thread-red text-thread-red",
  COMMENT: "border-node-blue text-node-blue",
  FOLLOW: "border-node-blue text-node-blue",
  WATCH: "border-line text-muted",
  SKIP: "border-line text-muted",
  NONE: "border-line text-muted",
};

export default function AgentDetailPanel({ persona, node, onClose }) {
  if (!persona) return null;

  const cohortLabel = node.cohort === "in-target" ? "ENGAGED" : "SKIPPED";

  return (
    <div className="flex h-full w-full flex-col overflow-y-auto border-t border-line p-4 sm:border-l sm:border-t-0 sm:w-[280px] sm:shrink-0">
      <div className="flex items-start justify-between">
        <div>
          <div className="font-mono text-[10px] text-muted">
            {node.id.toUpperCase()} · {cohortLabel} · ROUND {node.round}
          </div>
          <div className="mt-1 text-[14px] font-bold text-ink">{persona.name}</div>
          <div className="text-[11px] leading-snug text-muted">
            {persona.ageRange !== "—" ? `age ${persona.ageRange}` : "archetype"}
            {persona.behavior ? ` · ${persona.behavior}` : ""}
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-[13px] leading-none text-muted hover:text-ink"
          aria-label="Close"
        >
          ×
        </button>
      </div>

      {persona.interests?.length > 0 && (
        <div className="mt-4">
          <div className="label-micro">Interests</div>
          <div className="mt-1 text-[11.5px] leading-snug text-ink">
            {persona.interests.join(", ")}
          </div>
        </div>
      )}

      {persona.personality && (
        <div className="mt-3">
          <div className="label-micro">Persona</div>
          <p className="mt-1 text-[11px] leading-snug text-ink/80">{persona.personality}</p>
        </div>
      )}

      <div className="mt-3">
        <div className="label-micro">Action</div>
        <div
          className={`mt-1 inline-block rounded-[3px] border px-2 py-0.5 text-[10.5px] font-semibold uppercase tracking-wider ${
            ACTION_STYLE[persona.action] ?? ACTION_STYLE.NONE
          }`}
        >
          {persona.action}
        </div>
      </div>

      <div className="mt-3">
        <div className="flex items-center justify-between">
          <span className="label-micro">Completion</span>
          <span className="text-[10.5px] font-mono text-ink">{persona.watched}%</span>
        </div>
        <div className="mt-1 h-[3px] w-full bg-line">
          <div className="h-full bg-node-blue" style={{ width: `${persona.watched}%` }} />
        </div>
      </div>

      {persona.quote && (
        <p className="mt-3 border-l-2 border-line pl-2 text-[11px] italic leading-snug text-ink/80">
          &ldquo;{persona.quote}&rdquo;
        </p>
      )}

      <div className="mt-3">
        <div className="label-micro">Why (AI reasoning)</div>
        <p className="mt-1 text-[11px] leading-snug text-ink/80">{persona.why}</p>
      </div>
    </div>
  );
}
