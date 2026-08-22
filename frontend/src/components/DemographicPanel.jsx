export default function DemographicPanel({ targetAudience, phase }) {
  const hasResult = Boolean(targetAudience);

  return (
    <div className="flex h-full flex-col p-4">
      <div className="label-micro mb-2">Target audience</div>
      {hasResult ? (
        <p className="text-[12.5px] leading-snug text-ink">{targetAudience}</p>
      ) : (
        <p className="text-[11.5px] leading-snug text-muted">
          {phase === "idle"
            ? "Auto-detected from the video by the content-analysis model after you hit Run — no need to guess it up front."
            : "Analyzing content to detect the target audience…"}
        </p>
      )}
    </div>
  );
}
