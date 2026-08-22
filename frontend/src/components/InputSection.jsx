import VideoUploader from "./VideoUploader";
import DemographicPanel from "./DemographicPanel";
import PopulationControl from "./PopulationControl";
import SectionHeader from "./SectionHeader";

const BUSY_PHASES = new Set(["uploading", "processing", "revealing"]);

export default function InputSection({
  phase,
  file,
  onFileChange,
  seed,
  onSeedChange,
  targetAudience,
  run,
  onRun,
  fileError,
}) {
  const busy = BUSY_PHASES.has(phase);
  const running = phase === "uploading" || phase === "processing";

  return (
    <section>
      <SectionHeader
        number="01"
        title="Input"
        caption="Drop a short-form video, optionally set a seed, run"
      />
      <div className="mx-4 grid grid-cols-1 divide-y divide-line rounded-[3px] border border-line bg-panel sm:mx-6 sm:grid-cols-[2fr_1.4fr_1.2fr_0.9fr] sm:divide-x sm:divide-y-0">
        <VideoUploader
          file={file}
          onFileChange={onFileChange}
          disabled={busy}
          error={fileError}
        />
        <DemographicPanel targetAudience={targetAudience} phase={phase} />
        <PopulationControl
          seed={seed}
          onSeedChange={onSeedChange}
          disabled={busy}
          run={run}
        />
        <button
          onClick={onRun}
          disabled={running}
          className={`flex min-h-[110px] w-full items-center justify-center text-[12px] font-semibold uppercase tracking-widest transition-colors ${
            running
              ? "bg-[#8C8676] text-panel cursor-default"
              : "bg-ink text-panel hover:bg-ink/90"
          }`}
        >
          {running ? "Running…" : "Run"}
        </button>
      </div>
    </section>
  );
}
