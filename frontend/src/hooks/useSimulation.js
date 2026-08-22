import { useCallback, useEffect, useRef, useState } from "react";
import { createSimulation, fetchSimulation } from "../lib/api.js";
import { buildRunFromReport } from "../lib/runAdapter.js";

const POLL_MS = 3000;
const REVEAL_STAGGER_MS = 90;
const ROUND_PAUSE_MS = 900;

export function useSimulation() {
  const [phase, setPhase] = useState("idle"); // idle | uploading | processing | revealing | done | error
  const [progressText, setProgressText] = useState("");
  const [simulation, setSimulation] = useState(null); // raw API record
  const [run, setRun] = useState(null); // adapted graph
  const [round, setRound] = useState(0);
  const [visibleIds, setVisibleIds] = useState(() => new Set());
  const [selectedId, setSelectedId] = useState(null);
  const [error, setError] = useState("");

  const timers = useRef([]);
  const pollInterval = useRef(null);

  const clearTimers = useCallback(() => {
    timers.current.forEach((t) => clearTimeout(t));
    timers.current = [];
    if (pollInterval.current) {
      clearInterval(pollInterval.current);
      pollInterval.current = null;
    }
  }, []);

  useEffect(() => clearTimers, [clearTimers]);

  const revealRun = useCallback((nextRun) => {
    setVisibleIds(new Set(["hub"]));
    setRound(1);
    setPhase("revealing");

    const roundNumbers = Object.keys(nextRun.nodesByRound)
      .map(Number)
      .sort((a, b) => a - b);

    let cursor = 0;

    const revealRound = (roundNumber) => {
      const ids = nextRun.nodesByRound[roundNumber] || [];
      let i = 0;
      const step = () => {
        setVisibleIds((prev) => {
          const next = new Set(prev);
          ids.slice(i, i + 6).forEach((id) => next.add(id));
          return next;
        });
        i += 6;
        if (i < ids.length) {
          timers.current.push(setTimeout(step, REVEAL_STAGGER_MS));
        } else {
          cursor += 1;
          if (cursor < roundNumbers.length) {
            setRound(roundNumbers[cursor]);
            timers.current.push(setTimeout(() => revealRound(roundNumbers[cursor]), ROUND_PAUSE_MS));
          } else {
            timers.current.push(setTimeout(() => setPhase("done"), 300));
          }
        }
      };
      step();
    };

    if (roundNumbers.length) {
      revealRound(roundNumbers[0]);
    } else {
      setPhase("done");
    }
  }, []);

  const applyCompletedResult = useCallback(
    (record) => {
      const nextRun = buildRunFromReport(record.result, record.simulationId);
      setRun(nextRun);
      revealRun(nextRun);
    },
    [revealRun],
  );

  const poll = useCallback(
    (id) => {
      clearTimers();
      pollInterval.current = setInterval(async () => {
        try {
          const record = await fetchSimulation(id);
          setSimulation(record);
          setProgressText(record.progress || "");

          if (record.status === "COMPLETED") {
            clearInterval(pollInterval.current);
            pollInterval.current = null;
            applyCompletedResult(record);
          } else if (record.status === "FAILED") {
            clearInterval(pollInterval.current);
            pollInterval.current = null;
            setError(record.error || "Simulation failed. Check the server logs.");
            setPhase("error");
          }
        } catch (requestError) {
          setError(requestError.message);
        }
      }, POLL_MS);
    },
    [applyCompletedResult, clearTimers],
  );

  const start = useCallback(
    async (file, seed) => {
      clearTimers();
      setError("");
      setSelectedId(null);
      setRun(null);
      setVisibleIds(new Set());
      setRound(0);

      if (!file) {
        setError("Choose a video file first.");
        return;
      }

      try {
        setPhase("uploading");
        setProgressText("Uploading video...");
        const created = await createSimulation(file, seed);
        setSimulation(created);
        setPhase("processing");
        setProgressText(created.progress || "Starting simulation...");
        poll(created.simulationId);
      } catch (requestError) {
        setError(requestError.message);
        setPhase("error");
      }
    },
    [clearTimers, poll],
  );

  const loadExisting = useCallback(
    (record) => {
      clearTimers();
      setError("");
      setSelectedId(null);
      setSimulation(record);

      if (record.status === "COMPLETED" && record.result) {
        applyCompletedResult(record);
      } else if (record.status === "FAILED") {
        setError(record.error || "That simulation failed.");
        setPhase("error");
      } else {
        setPhase("processing");
        setProgressText(record.progress || "");
        poll(record.simulationId);
      }
    },
    [applyCompletedResult, clearTimers, poll],
  );

  const replay = useCallback(() => {
    if (run) revealRun(run);
  }, [revealRun, run]);

  const selectNode = useCallback((id) => {
    setSelectedId((prev) => (prev === id ? null : id));
  }, []);

  const reset = useCallback(() => {
    clearTimers();
    setPhase("idle");
    setProgressText("");
    setSimulation(null);
    setRun(null);
    setRound(0);
    setVisibleIds(new Set());
    setSelectedId(null);
    setError("");
  }, [clearTimers]);

  return {
    phase,
    progressText,
    simulation,
    run,
    round,
    roundCount: run?.roundCount || 0,
    visibleIds,
    selectedId,
    error,
    start,
    replay,
    loadExisting,
    reset,
    selectNode,
  };
}
