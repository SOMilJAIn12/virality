export default function PopulationControl({ seed, onSeedChange, disabled, run }) {
  const roundSizes = run?.report?.rounds?.length
    ? run.report.rounds.map((r) => r.cohort_size).join(" → ")
    : "15 → 30 → 60";

  return (
    <div className="flex h-full flex-col p-4">
      <div>
        <div className="label-micro mb-2">Cohort per round</div>
        <div className="rounded-[3px] border border-line bg-paper/40 px-2 py-1 text-[12.5px] font-mono text-ink">
          {roundSizes}
        </div>
        <p className="mt-2 text-[10.5px] leading-snug text-muted">
          fixed by the engine · velocity-gated PUSH/STOP between rounds
        </p>
      </div>

      <div className="mt-3">
        <div className="flex items-center justify-between">
          <span className="label-micro">Seed</span>
        </div>
        <input
          type="number"
          value={seed}
          disabled={disabled}
          onChange={(e) => onSeedChange(e.target.value)}
          placeholder="optional, e.g. 42"
          className="mt-1.5 w-full rounded-[3px] border border-line bg-panel px-2 py-1 text-[12.5px] text-ink outline-none disabled:opacity-60"
        />
        <p className="mt-1 text-[10.5px] leading-snug text-muted">
          reproducible run — same seed, same simulation
        </p>
      </div>
    </div>
  );
}
