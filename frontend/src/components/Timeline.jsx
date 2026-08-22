export default function Timeline({ phase, round, roundCount, onReplay }) {
  const label =
    phase === "done"
      ? `round ${roundCount} / ${roundCount}`
      : phase === "revealing"
        ? `streaming round ${round}…`
        : "";

  const progress =
    phase === "done" ? 1 : phase === "revealing" && roundCount ? round / roundCount : 0;

  const canReplay = phase === "revealing" || phase === "done";

  return (
    <div className="flex items-center gap-3 border-t border-line px-4 py-2 sm:px-6">
      <button
        onClick={onReplay}
        disabled={!canReplay}
        className="rounded-[3px] border border-line px-2.5 py-1 text-[10.5px] font-semibold uppercase tracking-wider text-ink hover:bg-ink/5 disabled:opacity-40"
      >
        Replay
      </button>
      <div className="relative h-[2px] flex-1 bg-line">
        <div
          className="absolute inset-y-0 left-0 bg-ink transition-all duration-500"
          style={{ width: `${progress * 100}%` }}
        />
      </div>
      <span className="whitespace-nowrap text-[10.5px] text-muted">{label}</span>
    </div>
  );
}
