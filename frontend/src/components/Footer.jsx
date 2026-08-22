export default function Footer({ population, replayInput, onReplayInputChange, onLoad, loadError }) {
  return (
    <div className="flex flex-col gap-2 border-t border-line px-4 py-3 text-[10.5px] text-muted sm:flex-row sm:items-center sm:justify-between sm:px-6">
      <span>
        {population ? `${population} reactions in last run` : "no run yet"} · 3-round cap ·
        velocity-gated
      </span>
      <div className="flex items-center gap-2">
        <span>Replay run:</span>
        <input
          value={replayInput}
          onChange={(e) => onReplayInputChange(e.target.value)}
          placeholder="sim_xxxxxxxx"
          className="w-40 rounded-[3px] border border-line bg-panel px-2 py-1 font-mono text-[10.5px] text-ink outline-none"
        />
        <button
          onClick={onLoad}
          className="rounded-[3px] border border-line px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-ink hover:bg-ink/5"
        >
          Load
        </button>
      </div>
      {loadError && <span className="text-thread-red">{loadError}</span>}
    </div>
  );
}
