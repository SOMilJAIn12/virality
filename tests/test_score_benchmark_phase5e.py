"""
Phase 5E — score benchmarking, instrumentation, and calibration
evidence. These tests are OFFLINE ONLY: no Groq, Whisper, FFmpeg,
network calls, API keys, or real video files anywhere in this file.

This phase does NOT change the scoring formula, weights, threshold, or
aggregation semantics. Every assertion below runs the CURRENT,
unmodified `app.simulation.scoring` functions against synthetic data
and reports what they actually produce -- including where the current
formula turns out to behave in a way that's worth flagging for a
future calibration phase (see `test_very_bad_and_weak_tie_at_zero`
below, which is evidence, not a bug being "fixed" here).

Run with:
    python -m pytest tests/test_score_benchmark_phase5e.py -v
"""
from __future__ import annotations

from app.config import RecommendationWeights
from app.models import EngagementStats, RoundResult
from app.simulation.benchmarks import (
    BENCHMARK_ORDER,
    BENCHMARK_SCENARIOS,
    compute_benchmark_scores,
    make_stats,
    render_benchmark_report,
    run_synthetic_funnel,
)
from app.simulation.scoring import (
    ScoreBreakdown,
    compute_distribution_score,
    compute_score_breakdown,
    compute_virality_score,
    decide_distribution,
)

WEIGHTS = RecommendationWeights(
    completion=0.30, share=0.25, comment=0.15, like=0.10,
    follow=0.10, rewatch=0.10, skip_penalty=0.20,
)
ROUND_COHORT_SIZES = [15, 30, 60]
PUSH_THRESHOLD = 0.30


# ---------------------------------------------------------------------------
# Step 2 — score breakdown instrumentation
# ---------------------------------------------------------------------------

def test_score_breakdown_exposes_required_fields():
    rounds = run_synthetic_funnel(0.5, ROUND_COHORT_SIZES, PUSH_THRESHOLD)
    breakdown = compute_score_breakdown(rounds, ROUND_COHORT_SIZES)
    assert isinstance(breakdown, ScoreBreakdown)
    for field in (
        "weighted_engagement",
        "reach_component",
        "penetration_component",
        "final_raw_score",
        "final_score_0_to_100",
    ):
        assert hasattr(breakdown, field)


def test_score_breakdown_matches_compute_virality_score():
    """The breakdown must not be a second implementation of the
    formula -- its final_score_0_to_100 has to equal exactly what
    compute_virality_score() (the existing public API) returns, since
    compute_virality_score() is a thin wrapper around this breakdown."""
    for name, rates in BENCHMARK_SCENARIOS.items():
        stats = make_stats(**rates)
        ds = compute_distribution_score(stats, WEIGHTS)
        rounds = run_synthetic_funnel(ds, ROUND_COHORT_SIZES, PUSH_THRESHOLD)
        breakdown = compute_score_breakdown(rounds, ROUND_COHORT_SIZES)
        direct = compute_virality_score(rounds, ROUND_COHORT_SIZES)
        assert breakdown.final_score_0_to_100 == direct, name


def test_score_breakdown_empty_rounds():
    breakdown = compute_score_breakdown([], ROUND_COHORT_SIZES)
    assert breakdown.final_score_0_to_100 == 0.0
    assert breakdown.weighted_engagement == 0.0
    assert breakdown.reach_component == 0.0
    assert breakdown.penetration_component == 0.0


# ---------------------------------------------------------------------------
# Step 3 — offline benchmark scenarios
# ---------------------------------------------------------------------------

def test_benchmark_scores_computed_with_current_formula():
    """Sanity check that the benchmark actually exercises the real
    formula end-to-end and every scenario is in [0, 100]."""
    results = compute_benchmark_scores(WEIGHTS, ROUND_COHORT_SIZES, PUSH_THRESHOLD)
    assert set(results.keys()) == set(BENCHMARK_SCENARIOS.keys())
    for name in BENCHMARK_ORDER:
        score = results[name]["virality_score"]
        assert 0.0 <= score <= 100.0, f"{name} score {score} out of [0, 100]"


def test_benchmark_scores_are_non_decreasing_across_tiers():
    """Core ordering check requested by the Phase 5E spec:
    VERY BAD <= WEAK <= DECENT <= STRONG <= EXCEPTIONAL, using the
    ACTUAL scores produced by the current formula (not assumed
    numbers). This is intentionally <=, not <: see
    test_very_bad_and_weak_tie_at_zero for why VERY BAD and WEAK
    currently tie, which is evidence to report, not a failure to hide
    behind a weaker assertion picked after the fact.
    """
    results = compute_benchmark_scores(WEIGHTS, ROUND_COHORT_SIZES, PUSH_THRESHOLD)
    ordered_scores = [results[name]["virality_score"] for name in BENCHMARK_ORDER]
    for a, b in zip(ordered_scores, ordered_scores[1:]):
        assert a <= b, f"benchmark scores are not monotonic: {ordered_scores}"


def test_decent_strong_exceptional_are_strictly_increasing():
    """Above the zero-floor region, the formula DOES strictly
    differentiate quality -- this isolates that positive result from
    the VERY BAD/WEAK tie documented separately below."""
    results = compute_benchmark_scores(WEIGHTS, ROUND_COHORT_SIZES, PUSH_THRESHOLD)
    decent = results["DECENT"]["virality_score"]
    strong = results["STRONG"]["virality_score"]
    exceptional = results["EXCEPTIONAL"]["virality_score"]
    assert decent < strong < exceptional


def test_very_bad_and_weak_tie_at_zero():
    """CALIBRATION EVIDENCE (not a bug fix): with the current weights
    (skip_penalty=0.20) and PUSH_THRESHOLD funnel, both the VERY BAD
    and WEAK synthetic scenarios produce distribution_score == 0.0
    (the positive weighted terms don't cover the skip penalty for
    either profile), so both collapse to the same virality_score ==
    0.0. The formula is not distinguishing "very bad" from "weak" --
    they hit the same floor. This is reported as-is; Phase 5E does not
    change the formula to fix it.
    """
    results = compute_benchmark_scores(WEIGHTS, ROUND_COHORT_SIZES, PUSH_THRESHOLD)
    assert results["VERY BAD"]["distribution_score"] == 0.0
    assert results["WEAK"]["distribution_score"] == 0.0
    assert results["VERY BAD"]["virality_score"] == results["WEAK"]["virality_score"] == 0.0


def test_benchmark_report_renders_all_scenarios():
    results = compute_benchmark_scores(WEIGHTS, ROUND_COHORT_SIZES, PUSH_THRESHOLD)
    report = render_benchmark_report(results)
    for name in BENCHMARK_ORDER:
        assert name in report
    assert "/100" in report


# ---------------------------------------------------------------------------
# Step 4 — PUSH threshold boundary behavior (validation only)
# ---------------------------------------------------------------------------

def test_push_threshold_boundary_below():
    assert decide_distribution(0.299, PUSH_THRESHOLD) == "STOP"


def test_push_threshold_boundary_exact():
    assert decide_distribution(0.30, PUSH_THRESHOLD) == "PUSH"


def test_push_threshold_boundary_above():
    assert decide_distribution(0.301, PUSH_THRESHOLD) == "PUSH"


# ---------------------------------------------------------------------------
# Step 5 — score sensitivity to engagement quality
# ---------------------------------------------------------------------------

def _stats_with(**overrides) -> EngagementStats:
    base = dict(
        watch_rate=0.60, skip_rate=0.40, average_completion_rate=0.30,
        rewatch_rate=0.05, like_rate=0.30, comment_rate=0.08,
        share_rate=0.10, follow_rate=0.05,
    )
    base.update(overrides)
    return make_stats(**base)


def test_higher_completion_increases_distribution_score():
    low = compute_distribution_score(_stats_with(average_completion_rate=0.30), WEIGHTS)
    high = compute_distribution_score(_stats_with(average_completion_rate=0.60), WEIGHTS)
    assert high > low


def test_higher_share_increases_distribution_score():
    low = compute_distribution_score(_stats_with(share_rate=0.10), WEIGHTS)
    high = compute_distribution_score(_stats_with(share_rate=0.40), WEIGHTS)
    assert high > low


def test_higher_engagement_increases_virality_score():
    """Isolate engagement-quality sensitivity at the virality-score
    level (post-funnel), not just the per-round distribution score."""
    low_ds = compute_distribution_score(_stats_with(average_completion_rate=0.20, share_rate=0.05), WEIGHTS)
    high_ds = compute_distribution_score(_stats_with(average_completion_rate=0.70, share_rate=0.40), WEIGHTS)
    assert high_ds > low_ds

    low_rounds = run_synthetic_funnel(low_ds, ROUND_COHORT_SIZES, PUSH_THRESHOLD)
    high_rounds = run_synthetic_funnel(high_ds, ROUND_COHORT_SIZES, PUSH_THRESHOLD)
    low_score = compute_virality_score(low_rounds, ROUND_COHORT_SIZES)
    high_score = compute_virality_score(high_rounds, ROUND_COHORT_SIZES)
    assert high_score > low_score


# ---------------------------------------------------------------------------
# Step 6 — regression test for the old "~8/100" fixed floor
# ---------------------------------------------------------------------------

def test_zero_engagement_single_round_does_not_hit_old_eight_floor():
    """Regression guard (Phase 5E instrumentation copy of the Phase 2
    fix): a single STOPped round-1 (cohort_size=15) with ZERO real
    engagement must score 0.0, not the old ~7.8-8.0/100 that came from
    a penetration term keyed off raw cohort_size instead of engaged
    reach. This test does not modify the formula -- it only asserts
    the existing implementation still behaves correctly.
    """
    zero_stats = make_stats(
        watch_rate=0.0, skip_rate=1.0, average_completion_rate=0.0,
        rewatch_rate=0.0, like_rate=0.0, comment_rate=0.0,
        share_rate=0.0, follow_rate=0.0,
    )
    distribution_score = compute_distribution_score(zero_stats, WEIGHTS)
    assert distribution_score == 0.0

    round_result = RoundResult(
        round_number=1, cohort_size=15, stats=zero_stats,
        distribution_score=distribution_score,
        decision=decide_distribution(distribution_score, PUSH_THRESHOLD),
        reactions=[],
    )
    assert round_result.decision == "STOP"

    breakdown = compute_score_breakdown([round_result], ROUND_COHORT_SIZES)
    assert breakdown.final_score_0_to_100 == 0.0
    assert breakdown.penetration_component == 0.0
