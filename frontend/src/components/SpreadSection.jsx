import SectionHeader from "./SectionHeader";
import NetworkGraph from "./NetworkGraph";
import GraphLegend from "./GraphLegend";
import Timeline from "./Timeline";
import AgentDetailPanel from "./AgentDetailPanel";
import NodeTooltip from "./NodeTooltip";

export default function SpreadSection({
  phase,
  round,
  roundCount,
  run,
  visibleIds,
  selectedId,
  onSelect,
  onReplay,
  progressText,
  error,
}) {
  const selectedNode = run?.nodes.find((n) => n.id === selectedId);
  const selectedPersona = selectedNode?.personaId && run?.personaById[selectedNode.personaId];

  return (
    <section>
      <SectionHeader
        number="02"
        title="Spread"
        caption="Every simulated reaction plotted — red solid = shared directly · grey dashed = shown by the algorithm"
      />
      <div className="mx-4 rounded-[3px] border border-line bg-panel sm:mx-6">
        {phase === "idle" && (
          <div className="p-4">
            <div className="text-[13px] font-bold text-ink">No simulation yet.</div>
            <p className="mt-1 max-w-md text-[11.5px] leading-snug text-muted">
              Drop a video above, then Run — the real persona pipeline analyzes it and the
              spread animates here round by round. Or replay a past run from the footer below.
            </p>
          </div>
        )}

        {(phase === "uploading" || phase === "processing") && (
          <div className="p-4">
            <div className="text-[13px] font-bold text-ink">
              {phase === "uploading" ? "Uploading video…" : "Running the persona simulation…"}
            </div>
            <p className="mt-1 max-w-md text-[11.5px] leading-snug text-muted">
              {progressText ||
                "Whisper transcript → vision content profile → viewer personas → rounds 1–3."}
            </p>
          </div>
        )}

        {phase === "error" && (
          <div className="p-4">
            <div className="text-[13px] font-bold text-thread-red">Simulation failed.</div>
            <p className="mt-1 max-w-md text-[11.5px] leading-snug text-muted">{error}</p>
          </div>
        )}

        {(phase === "revealing" || phase === "done") && run && (
          <>
            <div className="flex flex-col sm:flex-row">
              <div className="relative min-w-0 flex-1 p-2 sm:p-3">
                <NetworkGraph
                  run={run}
                  visibleIds={visibleIds}
                  selectedId={selectedId}
                  onSelect={onSelect}
                />
                {selectedPersona && (
                  <NodeTooltip persona={selectedPersona} node={selectedNode} />
                )}
              </div>
              {selectedPersona && (
                <AgentDetailPanel
                  persona={selectedPersona}
                  node={selectedNode}
                  onClose={() => onSelect(selectedId)}
                />
              )}
            </div>
            <Timeline phase={phase} round={round} roundCount={roundCount} onReplay={onReplay} />
            <GraphLegend />
          </>
        )}
      </div>
    </section>
  );
}
