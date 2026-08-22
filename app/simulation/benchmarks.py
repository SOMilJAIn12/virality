"""
Phase 5E — deterministic, OFFLINE benchmark scenarios for scoring
calibration checks.

Nothing in this module calls Groq, Whisper, FFmpeg, or any network
service, and nothing here needs an API key or a real video file. Every
scenario is a hand-picked EngagementStats-shaped rate profile that gets
run through the REAL, unmodified scoring functions in
`app.simulation.scoring`.

This module is intentionally the single place these five scenarios are
defined. Both `tests/test_score_benchmark_phase5e.py` and the optional
`python main.py --benchmark` CLI import `BENCHMARK_SCENARIOS` /
`compute_benchmark_scores` from here instead of each hardcoding their
own copy of the numbers.
"""
from __future__ import annotations

from app.config import RecommendationWeights
from app.models import EngagementStats, RoundResult
from app.simulation.scoring import (
    compute_distribution_score,
    compute_virality_score,
    decide_distribution,
)

# Qualitative tiers requested in the Phase 5E spec. Rates are
# approximate — they encode "very bad / weak / decent / strong /
# exceptional" as a human would describe the underlying engagement,
# not a target score. The actual score each tier receives is whatever
# the CURRENT scoring formula produces; that's the whole point of this
# benchmark.
BENCHMARK_SCENARIOS: dict[str, dict[str, float]] = {
    "VERY BAD": dict(
        watch_rate=0.10, skip_rate=0.90, average_completion_rate=0.05,
        rewatch_rate=0.00, like_rate=0.03, comment_rate=0.01,
        share_rate=0.01, follow_rate=0.00,
    ),
    "WEAK": dict(
        watch_rate=0.30, skip_rate=0.70, average_completion_rate=0.15,
        rewatch_rate=0.00, like_rate=0.10, comment_rate=0.03,
        share_rate=0.05, follow_rate=0.02,
    ),
    "DECENT": dict(
        watch_rate=0.55, skip_rate=0.45, average_completion_rate=0.40,
        rewatch_rate=0.00, like_rate=0.35, comment_rate=0.10,
        share_rate=0.15, follow_rate=0.05,
    ),
    "STRONG": dict(
        watch_rate=0.75, skip_rate=0.25, average_completion_rate=0.65,
        rewatch_rate=0.10, like_rate=0.60, comment_rate=0.20,
        share_rate=0.30, follow_rate=0.10,
    ),
    "EXCEPTIONAL": dict(
        watch_rate=0.90, skip_rate=0.10, average_completion_rate=0.85,
        rewatch_rate=0.20, like_rate=0.80, comment_rate=0.35,
        share_rate=0.50, follow_rate=0.20,
    ),
}

# Order matters for the printed benchmark report; keep it as the
# qualitative ordering the scenarios were designed around.
BENCHMARK_ORDER: list[str] = ["VERY BAD", "WEAK", "DECENT", "STRONG", "EXCEPTIONAL"]


def make_stats(total_personas: int = 15, **rates: float) -> EngagementStats:
    """Build a synthetic EngagementStats for one benchmark scenario."""
    return EngagementStats(
        total_personas=total_personas,
        successful_personas=total_personas,
        failed_personas=0,
        **rates,
    )


def run_synthetic_funnel(
    distribution_score: float,
    round_cohort_sizes: list[int],
    push_threshold: float,
) -> list[RoundResult]:
    """Replay the engine's round loop for a CONSTANT per-round
    distribution_score, matching the real STOP/PUSH control flow in
    `app/simulation/engine.py` (same pattern already used in
    `tests/test_scoring_and_aggregation.py`).

    A constant distribution_score is a simplification (the real engine
    re-samples a cohort and gets a fresh score each round), but it's the
    right simplification for calibration checks: it isolates "does the
    scoring math treat a given distribution_score consistently across
    the funnel" from "how much do successive rounds vary."
    """
    dummy_stats = EngagementStats(
        total_personas=1, successful_personas=1, failed_personas=0,
        watch_rate=0, skip_rate=0, average_completion_rate=0,
        rewatch_rate=0, like_rate=0, comment_rate=0, share_rate=0, follow_rate=0,
    )
    rounds: list[RoundResult] = []
    for i, size in enumerate(round_cohort_sizes, start=1):
        decision = decide_distribution(distribution_score, push_threshold)
        rounds.append(RoundResult(
            round_number=i, cohort_size=size, stats=dummy_stats,
            distribution_score=distribution_score, decision=decision, reactions=[],
        ))
        if decision == "STOP":
            break
    return rounds


def compute_benchmark_scores(
    weights: RecommendationWeights,
    round_cohort_sizes: list[int],
    push_threshold: float,
) -> dict[str, dict]:
    """Run every BENCHMARK_SCENARIOS entry end-to-end through the
    CURRENT, unmodified scoring formula:

        rates -> EngagementStats -> compute_distribution_score()
              -> synthetic funnel (STOP/PUSH per round)
              -> compute_virality_score()

    Returns, per scenario name:
        distribution_score, virality_score, rounds_run, final_decision
    """
    results: dict[str, dict] = {}
    for name in BENCHMARK_ORDER:
        rates = BENCHMARK_SCENARIOS[name]
        stats = make_stats(**rates)
        distribution_score = compute_distribution_score(stats, weights)
        rounds = run_synthetic_funnel(distribution_score, round_cohort_sizes, push_threshold)
        virality_score = compute_virality_score(rounds, round_cohort_sizes)
        results[name] = {
            "distribution_score": distribution_score,
            "virality_score": virality_score,
            "rounds_run": len(rounds),
            "final_decision": rounds[-1].decision if rounds else None,
        }
    return results


def render_benchmark_report(results: dict[str, dict]) -> str:
    """Plain-text `VERY BAD   X/100` style report for the CLI."""
    lines = []
    name_width = max(len(n) for n in BENCHMARK_ORDER) + 2
    for name in BENCHMARK_ORDER:
        r = results[name]
        lines.append(f"{name.ljust(name_width)}{r['virality_score']:.1f}/100")
    return "\n".join(lines)
