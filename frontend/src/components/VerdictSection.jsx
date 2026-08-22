import SectionHeader from "./SectionHeader";
import MetricCard from "./MetricCard";

export default function VerdictSection({ phase, run, simulation, onDownload }) {
  const done = phase === "done" && run;
  const m = run?.metrics;
  const report = run?.report;
  const profile = report?.content_profile;

  return (
    <section>
      <SectionHeader number="03" title="Verdict" caption="Comparative, not predictive" />
      <div className="mx-4 rounded-[3px] border border-line bg-panel sm:mx-6">
        {!done && (
          <div className="p-4">
            <div className="text-[13px] font-bold text-ink">Verdict lands here.</div>
            <p className="mt-1 max-w-md text-[11.5px] leading-snug text-muted">
              Reach, share rate, cascade depth, and the AI's scored summary render once a run
              completes.
            </p>
          </div>
        )}

        {done && (
          <>
            <div className="flex flex-wrap items-start justify-between gap-3 p-4">
              <div>
                <div className="text-[19px] font-bold text-ink">{m.verdictHeadline}</div>
                <p className="mt-1 max-w-2xl text-[11.5px] leading-snug text-ink/75">
                  {m.verdictBody}
                </p>
              </div>
              <div className="flex flex-col items-end">
                <div className="text-[34px] font-bold leading-none text-ink">
                  {Math.round(report.virality_score)}
                </div>
                <div className="label-micro mt-1">virality score</div>
                <button
                  type="button"
                  onClick={onDownload}
                  className="mt-2 rounded-[3px] border border-line px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-ink hover:bg-ink/5"
                >
                  Download report
                </button>
              </div>
            </div>

            <div className="grid grid-cols-2 divide-y divide-line border-t border-line sm:grid-cols-5 sm:divide-y-0 sm:divide-x">
              <MetricCard
                label="Watch rate"
                value={m.reachPct}
                unit="%"
                sub={`${m.reachCount} of ${run.population} in round ${m.cascadeDepth}`}
              />
              <MetricCard
                label="Watched / skipped"
                value={`${m.inPct}/${m.outPct}`}
                sub="% of final round"
                bar={{ inPct: m.inPct, outPct: m.outPct }}
              />
              <MetricCard
                label="Share rate"
                value={m.shareRate}
                unit="%"
                sub={`${m.shares} shares / ${m.views} views`}
              />
              <MetricCard
                label="Rounds run"
                value={m.cascadeDepth}
                unit="/ 3"
                sub="velocity-gated PUSH/STOP"
              />
              <div className="p-3.5">
                <div className="label-micro">Potential</div>
                <div className="mt-1.5 text-[13px] font-bold leading-snug text-ink">
                  {m.verdictTag}
                </div>
              </div>
            </div>

            {profile && (
              <div className="border-t border-line p-4">
                <div className="text-[13px] font-bold text-ink">{profile.title}</div>
                <p className="mt-1 max-w-2xl text-[11.5px] leading-snug text-ink/75">
                  {profile.summary}
                </p>
                <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <ContentBar label="Hook strength" value={profile.hook_strength} />
                  <ContentBar label="Shareability" value={profile.shareability} />
                  <ContentBar label="Entertainment" value={profile.entertainment_value} />
                  <ContentBar label="Curiosity" value={profile.curiosity_surprise_strength} />
                </div>
              </div>
            )}

            {(report.main_drivers?.length > 0 || report.weaknesses?.length > 0) && (
              <div className="grid grid-cols-1 divide-y divide-line border-t border-line sm:grid-cols-2 sm:divide-y-0 sm:divide-x">
                <div className="p-4">
                  <div className="label-micro mb-2">Main drivers</div>
                  <ul className="list-inside list-disc space-y-1 text-[11.5px] leading-snug text-ink/85">
                    {report.main_drivers.map((d) => (
                      <li key={d}>{d}</li>
                    ))}
                  </ul>
                </div>
                <div className="p-4">
                  <div className="label-micro mb-2">Weaknesses to improve</div>
                  <ul className="list-inside list-disc space-y-1 text-[11.5px] leading-snug text-ink/85">
                    {report.weaknesses.map((w) => (
                      <li key={w}>{w}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )}

            {simulation?.simulationId && (
              <div className="border-t border-line px-4 py-2 font-mono text-[10px] text-muted">
                {simulation.simulationId}
              </div>
            )}
          </>
        )}
      </div>
    </section>
  );
}

function ContentBar({ label, value = 0 }) {
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className="label-micro">{label}</span>
        <span className="text-[10.5px] font-mono text-ink">{Math.round(value * 100)}%</span>
      </div>
      <div className="mt-1 h-[3px] w-full bg-line">
        <div
          className="h-full bg-node-blue"
          style={{ width: `${Math.min(value * 100, 100)}%` }}
        />
      </div>
    </div>
  );
}
