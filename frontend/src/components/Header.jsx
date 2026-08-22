const PHASE_LABEL = {
  idle: "Live",
  uploading: "Uploading…",
  processing: "Processing…",
  revealing: "Streaming…",
  done: "Done",
  error: "Error",
};

export default function Header({ runId, population, phase, progressText }) {
  const rightText =
    phase === "idle"
      ? "Live"
      : runId
        ? `${runId} · ${PHASE_LABEL[phase] || phase}${population ? ` · ${population} reactions` : ""}`
        : progressText || PHASE_LABEL[phase] || phase;

  return (
    <header className="flex items-baseline justify-between border-b border-line px-4 py-3 sm:px-6">
      <div className="flex items-baseline gap-2">
        <h1 className="text-[15px] font-bold tracking-tight text-ink">
          AI Virality Simulator
        </h1>
        <span className="text-[13px] text-muted">Run report</span>
      </div>
      <div className="font-mono text-[11px] text-muted truncate max-w-[55%] text-right">
        {rightText}
      </div>
    </header>
  );
}
