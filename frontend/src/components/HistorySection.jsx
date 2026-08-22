import SectionHeader from "./SectionHeader";
import { formatDate } from "../lib/api.js";

const STATUS_STYLE = {
  COMPLETED: "text-node-blue border-node-blue",
  FAILED: "text-thread-red border-thread-red",
  PENDING: "text-muted border-line",
  PROCESSING: "text-muted border-line",
};

export default function HistorySection({ history, onSelect }) {
  return (
    <section>
      <SectionHeader
        number="04"
        title="History"
        caption="Every simulation persisted in Postgres — click one to reload it"
      />
      <div className="mx-4 rounded-[3px] border border-line bg-panel sm:mx-6">
        {history.length === 0 ? (
          <div className="p-4 text-[11.5px] text-muted">No simulations have been saved yet.</div>
        ) : (
          <div className="divide-y divide-line">
            {history.map((item) => (
              <button
                key={item.simulationId}
                onClick={() => onSelect(item.simulationId)}
                className="flex w-full items-center justify-between px-4 py-2.5 text-left hover:bg-ink/5"
              >
                <div>
                  <div className="font-mono text-[11px] text-ink">{item.simulationId}</div>
                  <div className="text-[10.5px] text-muted">{formatDate(item.createdAt)}</div>
                </div>
                <div className="flex items-center gap-3">
                  <span
                    className={`rounded-[3px] border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${
                      STATUS_STYLE[item.status] || STATUS_STYLE.PENDING
                    }`}
                  >
                    {item.status}
                  </span>
                  {item.viralityScore !== null && item.viralityScore !== undefined && (
                    <strong className="text-[12px] text-ink">
                      {Math.round(item.viralityScore)}/100
                    </strong>
                  )}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
