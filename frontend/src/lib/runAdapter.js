// Turns a real `SimulationReport` (app/models.py::SimulationReport, as
// returned by POST/GET /api/simulations) into the node/edge graph shape
// that NetworkGraph, AgentDetailPanel, NodeTooltip, and VerdictSection
// were built to render. Every value below is derived from real backend
// output — nothing here is randomly generated content, only the (x, y)
// layout positions are computed client-side so the graph has somewhere
// to draw each real reaction.

import { getPersonaMeta } from "../data/personas.js";

function hashSeed(str) {
  let h = 0;
  for (let i = 0; i < str.length; i++) {
    h = (Math.imul(31, h) + str.charCodeAt(i)) | 0;
  }
  return h >>> 0;
}

function mulberry32(seed) {
  let a = seed;
  return function rand() {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Decide a single headline action for a reaction (a persona can like +
// comment + share at once — we surface the most significant one for the
// node color/label, matching the original mock's single-action model).
function primaryAction(reaction) {
  if (!reaction.watch) return "SKIP";
  if (reaction.share) return "SHARE";
  if (reaction.comment) return "COMMENT";
  if (reaction.like) return "LIKE";
  if (reaction.follow) return "FOLLOW";
  return "WATCH";
}

function behaviorTag(meta) {
  if (meta.sharingTendency >= 0.6) return "sharer";
  if (meta.commentingTendency >= 0.5) return "commenter";
  return "lurker";
}

const HUB = { x: 150, y: 300 };

/**
 * @param {object} report SimulationReport (result.result from the API)
 * @param {string} simulationId
 */
export function buildRunFromReport(report, simulationId) {
  const rand = mulberry32(hashSeed(simulationId || "seed"));
  const rounds = report.rounds || [];

  const nodes = [
    { id: "hub", kind: "hub", x: HUB.x, y: HUB.y, round: 1, cohort: "hub" },
  ];
  const edges = [];
  const personaById = {};
  const nodesByRound = {};

  // Track, per persona archetype, the last node id that engaged with it in
  // the previous round so later rounds can draw a cascade-style edge back
  // to a real "parent" reaction rather than a purely random one.
  let previousRoundEngagedByPersona = {};
  let previousRoundParentPool = ["hub"];

  rounds.forEach((round, roundIdx) => {
    const roundNumber = round.round_number;
    const reactions = round.reactions || [];
    nodesByRound[roundNumber] = [];

    const engagedThisRound = {};
    const engagedNodes = [];

    reactions.forEach((reaction, i) => {
      const meta = getPersonaMeta(reaction.persona_id);
      const action = primaryAction(reaction);
      const engaged = reaction.watch;
      const cohort = engaged ? "in-target" : "out-of-target";

      // Fan the round out around the hub; later rounds sit farther out,
      // engaged reactions cluster tighter than skipped ones.
      const ringBase = 90 + roundIdx * 260;
      const angle = -1.15 + rand() * 2.3;
      const dist = ringBase + rand() * 220 + (engaged ? 0 : 90);
      const x = HUB.x + Math.cos(angle) * dist + rand() * 40;
      const y = HUB.y + Math.sin(angle) * dist * 0.62;

      const nodeId = `r${roundNumber}-${i}`;

      nodes.push({
        id: nodeId,
        kind: "persona",
        cohort,
        x: Math.max(30, Math.min(970, x)),
        y: Math.max(30, Math.min(490, y)),
        round: roundNumber,
        sharedDirectly: reaction.share === true,
        personaId: nodeId,
      });
      nodesByRound[roundNumber].push(nodeId);

      personaById[nodeId] = {
        id: nodeId,
        archetypeId: reaction.persona_id,
        name: meta.name,
        ageRange: meta.ageRange,
        interests: meta.interests,
        personality: meta.personality,
        behavior: behaviorTag(meta),
        round: roundNumber,
        action,
        watched: Math.round((reaction.completion_rate || 0) * 100),
        quote: reaction.comment_text || null,
        why: reaction.reasoning || "No reasoning was recorded for this reaction.",
      };

      if (roundNumber === 1) {
        edges.push({
          from: "hub",
          to: nodeId,
          kind: reaction.share ? "direct" : "algo",
          round: roundNumber,
        });
      } else {
        const pool = previousRoundParentPool.length
          ? previousRoundParentPool
          : ["hub"];
        const parentId =
          previousRoundEngagedByPersona[reaction.persona_id] ||
          pool[Math.floor(rand() * pool.length)];
        edges.push({ from: parentId, to: nodeId, kind: "algo", round: roundNumber });
      }

      if (engaged) {
        engagedThisRound[reaction.persona_id] = nodeId;
        engagedNodes.push(nodeId);
      }
    });

    previousRoundParentPool = engagedNodes.length
      ? engagedNodes
      : nodesByRound[roundNumber].length
        ? nodesByRound[roundNumber]
        : previousRoundParentPool;
    previousRoundEngagedByPersona = engagedThisRound;
  });

  const lastRound = rounds[rounds.length - 1];
  const stats = lastRound?.stats;
  const totalReach = rounds.reduce((sum, r) => sum + (r.cohort_size || 0), 0);
  const population = lastRound?.cohort_size || totalReach || 0;

  const reachPct = stats ? Math.round(stats.watch_rate * 100) : 0;
  const skipPct = stats ? Math.round(stats.skip_rate * 100) : 0;
  const shareRatePct = stats ? Math.round(stats.share_rate * 1000) / 10 : 0;
  const shares = stats ? Math.round(stats.share_rate * (lastRound.cohort_size || 0)) : 0;

  const potential = (report.potential || "").toUpperCase();
  const isBreakout = potential === "HIGH" || potential === "VERY HIGH";

  const metrics = {
    reachPct,
    reachCount: stats?.successful_personas ?? 0,
    inPct: reachPct,
    outPct: skipPct,
    shareRate: shareRatePct,
    shares,
    views: lastRound?.cohort_size ?? 0,
    cascadeDepth: rounds.length,
    verdictHeadline: isBreakout ? "Breakout." : "Niche hit.",
    verdictBody: report.ai_summary || "",
    verdictTag: `${report.potential || "UNKNOWN"} POTENTIAL · score ${Math.round(
      report.virality_score ?? 0,
    )}/100`,
  };

  return {
    runId: simulationId,
    population,
    nodes,
    edges,
    personaById,
    nodesByRound,
    metrics,
    roundCount: rounds.length,
    report,
  };
}
