"""
Deterministic scoring: distribution score (per round) and the final
0-100 virality score (across all rounds).

Nothing in this file calls an LLM. All weights/thresholds come from
`app.config.settings`, so tuning the algorithm never requires touching
this file — just the .env.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from app.config import RecommendationWeights
from app.models import EngagementStats, RoundResult


def compute_distribution_score(stats: EngagementStats, weights: RecommendationWeights) -> float:
    """"Instagram-inspired" (NOT the real algorithm) weighted engagement score.

    Returns a float that is USUALLY in [0, 1] but is not hard-clamped,
    since a very strong round (e.g. very high completion+share with low
    skip) could nudge slightly above 1.0 — callers that need a strict
    0-1 range should clamp explicitly.
    """
    score = (
        weights.completion * stats.average_completion_rate
        + weights.share * stats.share_rate
        + weights.comment * stats.comment_rate
        + weights.like * stats.like_rate
        + weights.follow * stats.follow_rate
        + weights.rewatch * stats.rewatch_rate
        - weights.skip_penalty * stats.skip_rate
    )
    return max(0.0, score)


def decide_distribution(score: float, push_threshold: float) -> str:
    return "PUSH" if score >= push_threshold else "STOP"


@dataclass(frozen=True)
class ScoreBreakdown:
    """Structured view of what `compute_virality_score` actually computed.

    This is instrumentation only (Phase 5E) — every field here is read
    directly out of `compute_score_breakdown`, which is the SAME
    function `compute_virality_score` calls. There is no second copy of
    the formula anywhere; this dataclass just exposes the intermediate
    values that were previously local variables.
    """

    weighted_engagement: float
    reach_component: float
    penetration_component: float
    final_raw_score: float  # 0-1 scale, pre-rounding, pre-*100
    final_score_0_to_100: float


def compute_score_breakdown(
    rounds: list[RoundResult],
    round_cohort_sizes: list[int] | None = None,
) -> ScoreBreakdown:
    """Combine all rounds into a structured virality-score breakdown.

    Formula (deterministic, explainable — UNCHANGED from before Phase 5E,
    just extracted into its own function so the intermediate values are
    inspectable):
      - weighted_engagement: average distribution_score across rounds,
        weighted so LATER rounds (larger, "harder to impress" cohorts)
        count more — surviving more rounds is a stronger virality signal.
      - reach_component: how many rounds PUSHed / total rounds run,
        i.e. how far the content traveled through the funnel.
      - penetration_component: log-scaled boost for *engaged* reach
        (audience size reached, weighted by how well each round actually
        performed), capped so it can't dominate the score.

    `round_cohort_sizes` should be the full configured funnel
    (e.g. settings.round_cohort_sizes = [15, 30, 60]) so the penetration
    component is normalized against the real maximum reachable audience.
    If omitted, it falls back to the cohort sizes actually observed in
    `rounds` (a smaller, less meaningful reference, but still correct).

    IMPORTANT: penetration is deliberately keyed off *engaged* reach
    (cohort_size * distribution_score), not raw cohort_size. Raw
    cohort_size is fixed by config and has nothing to do with how the
    video actually performed — using it directly would let a video with
    ZERO real engagement still collect a "the round ran with N people"
    bonus, producing a misleading non-zero floor for every video
    regardless of quality. Weighting by distribution_score means a round
    with 0 engagement contributes 0 to penetration, same as it should
    contribute 0 everywhere else.
    """
    if not rounds:
        return ScoreBreakdown(
            weighted_engagement=0.0,
            reach_component=0.0,
            penetration_component=0.0,
            final_raw_score=0.0,
            final_score_0_to_100=0.0,
        )

    # Weighted average distribution score, weight = round_number (later
    # rounds count more because they represent bigger, tougher cohorts).
    total_weight = sum(r.round_number for r in rounds)
    weighted_engagement = sum(r.distribution_score * r.round_number for r in rounds) / total_weight

    pushes = sum(1 for r in rounds if r.decision == "PUSH")
    reach_component = pushes / len(rounds)

    engaged_reach = sum(r.cohort_size * r.distribution_score for r in rounds)
    max_possible_reach = (
        sum(round_cohort_sizes) if round_cohort_sizes else sum(r.cohort_size for r in rounds)
    )
    penetration_component = 0.0
    if max_possible_reach > 0:
        penetration_component = min(
            1.0, math.log10(engaged_reach + 1) / math.log10(max_possible_reach + 1)
        )

    raw = (
        0.55 * weighted_engagement
        + 0.30 * reach_component
        + 0.15 * penetration_component
    )
    final_raw_score = max(0.0, min(1.0, raw))
    final_score_0_to_100 = round(final_raw_score * 100, 1)

    return ScoreBreakdown(
        weighted_engagement=weighted_engagement,
        reach_component=reach_component,
        penetration_component=penetration_component,
        final_raw_score=final_raw_score,
        final_score_0_to_100=final_score_0_to_100,
    )


def compute_virality_score(
    rounds: list[RoundResult],
    round_cohort_sizes: list[int] | None = None,
) -> float:
    """Combine all rounds into one 0-100 virality score.

    Thin wrapper around `compute_score_breakdown` — kept for backwards
    compatibility with existing callers (app/simulation/report.py,
    tests). `compute_score_breakdown` is the single source of truth for
    the math; this function does not recompute anything.
    """
    return compute_score_breakdown(rounds, round_cohort_sizes).final_score_0_to_100


def classify_potential(virality_score: float) -> str:
    if virality_score >= 80:
        return "VERY HIGH"
    if virality_score >= 60:
        return "HIGH"
    if virality_score >= 35:
        return "MEDIUM"
    return "LOW"


def identify_drivers_and_weaknesses(
    rounds: list[RoundResult],
) -> tuple[list[str], list[str]]:
    """Turn the last round's stats into plain-English bullet points.

    Purely rule-based (thresholds on the real numbers) — no LLM guessing.
    """
    if not rounds:
        return [], []

    last = rounds[-1].stats
    drivers: list[str] = []
    weaknesses: list[str] = []

    if last.average_completion_rate >= 0.6:
        drivers.append("Strong completion rate")
    elif last.average_completion_rate < 0.35:
        weaknesses.append("Low completion rate — viewers drop off early")

    if last.share_rate >= 0.3:
        drivers.append("High shareability")
    elif last.share_rate < 0.1:
        weaknesses.append("Low share rate")

    if last.like_rate >= 0.5:
        drivers.append("Broad likability")

    if last.comment_rate >= 0.25:
        drivers.append("Sparks conversation (high comment rate)")

    if last.follow_rate >= 0.2:
        drivers.append("Strong target audience fit (high follow rate)")
    elif last.follow_rate < 0.08:
        weaknesses.append("Weak conversion to followers")

    if last.skip_rate >= 0.4:
        weaknesses.append("High skip rate — weak hook or mismatched audience")

    if len(rounds) >= 1 and rounds[-1].decision == "STOP":
        weaknesses.append("Engagement dropped below the distribution threshold")

    if not drivers:
        drivers.append("No standout strengths identified in this run")
    if not weaknesses:
        weaknesses.append("No major weaknesses identified in this run")

    return drivers, weaknesses
