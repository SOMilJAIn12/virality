import { useCallback, useEffect, useState } from "react";
import "./index.css";
import Header from "./components/Header";
import InputSection from "./components/InputSection";
import SpreadSection from "./components/SpreadSection";
import VerdictSection from "./components/VerdictSection";
import HistorySection from "./components/HistorySection";
import Footer from "./components/Footer";
import { useSimulation } from "./hooks/useSimulation.js";
import { fetchHistory, fetchSimulation, downloadReport } from "./lib/api.js";

export default function App() {
  const [file, setFile] = useState(null);
  const [seed, setSeed] = useState("");
  const [fileError, setFileError] = useState("");
  const [history, setHistory] = useState([]);
  const [replayInput, setReplayInput] = useState("");
  const [loadError, setLoadError] = useState("");

  const {
    phase,
    progressText,
    simulation,
    run,
    round,
    roundCount,
    visibleIds,
    selectedId,
    error,
    start,
    replay,
    loadExisting,
    selectNode,
  } = useSimulation();

  const loadHistory = useCallback(async () => {
    try {
      const simulations = await fetchHistory();
      setHistory(simulations);
    } catch (requestError) {
      console.error(requestError);
    }
  }, []);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  useEffect(() => {
    if (phase === "done" || phase === "error") {
      loadHistory();
    }
  }, [phase, loadHistory]);

  async function handleRun() {
    setFileError("");
    if (!file) {
      setFileError("Choose a video file first.");
      return;
    }
    const parsedSeed = seed.trim() ? Number(seed.trim()) : undefined;
    await start(file, parsedSeed);
  }

  async function handleLoadById(id) {
    setLoadError("");
    if (!id) {
      setLoadError("Enter a simulation id.");
      return;
    }
    try {
      const record = await fetchSimulation(id);
      loadExisting(record);
    } catch (requestError) {
      setLoadError(requestError.message);
    }
  }

  const targetAudience = run?.report?.content_profile?.target_audience;

  return (
    <div className="mx-auto min-h-screen max-w-[1180px] bg-paper">
      <Header
        runId={simulation?.simulationId ?? ""}
        population={run?.population}
        phase={phase}
        progressText={progressText}
      />

      <InputSection
        phase={phase}
        file={file}
        onFileChange={(f) => {
          setFile(f);
          setFileError("");
        }}
        seed={seed}
        onSeedChange={setSeed}
        targetAudience={targetAudience}
        run={run}
        onRun={handleRun}
        fileError={fileError}
      />

      <SpreadSection
        phase={phase}
        round={round}
        roundCount={roundCount}
        run={run}
        visibleIds={visibleIds}
        selectedId={selectedId}
        onSelect={selectNode}
        onReplay={replay}
        progressText={progressText}
        error={error}
      />

      <VerdictSection
        phase={phase}
        run={run}
        simulation={simulation}
        onDownload={() => downloadReport(simulation, run?.report)}
      />

      <HistorySection history={history} onSelect={handleLoadById} />

      <Footer
        population={run?.population}
        replayInput={replayInput}
        onReplayInputChange={setReplayInput}
        onLoad={() => handleLoadById(replayInput.trim())}
        loadError={loadError}
      />
    </div>
  );
}
