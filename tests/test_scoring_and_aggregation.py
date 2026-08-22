"""
Fast, offline unit tests for the deterministic parts of the pipeline
(aggregation + scoring). These never call an LLM or need Ollama/Groq
running, so they're a good sanity check that `pip install` worked and
the math is correct.

Run with:
    python -m pytest tests/ -v
or, without pytest:
    python tests/test_scoring_and_aggregation.py
"""
from __future__ import annotations

from app.config import RecommendationWeights
from app.models import PersonaReaction, RoundResult
from app.simulation.aggregation import aggregate_engagement
from app.simulation.scoring import (
    compute_distribution_score,
    compute_virality_score,
    decide_distribution,
)

WEIGHTS = RecommendationWeights(
    completion=0.30, share=0.25, comment=0.15, like=0.10,
    follow=0.10, rewatch=0.10, skip_penalty=0.20,
)
ROUND_COHORT_SIZES = [15, 30, 60]
PUSH_THRESHOLD = 0.30

# Hand-picked engagement-rate profiles (see Phase 2 diagnosis for the
# reasoning behind these numbers) used to prove the scoring system
# actually differentiates poor / mediocre / good / excellent content
# instead of collapsing everything to ~8/100.
SCENARIOS = {
    "BAD": dict(
        watch_rate=0.30, skip_rate=0.70, average_completion_rate=0.15,
        rewatch_rate=0.02, like_rate=0.10, comment_rate=0.02,
        share_rate=0.02, follow_rate=0.02,
    ),
    "MEDIUM": dict(
        watch_rate=0.65, skip_rate=0.35, average_completion_rate=0.45,
        rewatch_rate=0.10, like_rate=0.35, comment_rate=0.08,
        share_rate=0.12, follow_rate=0.08,
    ),
    "GOOD": dict(
        watch_rate=0.80, skip_rate=0.20, average_completion_rate=0.65,
        rewatch_rate=0.20, like_rate=0.55, comment_rate=0.15,
        share_rate=0.25, follow_rate=0.15,
    ),
    "EXCELLENT": dict(
        watch_rate=0.92, skip_rate=0.08, average_completion_rate=0.85,
        rewatch_rate=0.35, like_rate=0.75, comment_rate=0.30,
        share_rate=0.45, follow_rate=0.30,
    ),
}


def _stats(**rates):
    from app.models import EngagementStats
    return EngagementStats(
        total_personas=15, successful_personas=15, failed_personas=0, **rates
    )


def _simulate_full_run(distribution_score: float) -> list[RoundResult]:
    """Simulate the engine's round loop for a constant per-round score,
    matching the real STOP/PUSH control flow in app/simulation/engine.py."""
    from app.models import EngagementStats

    dummy_stats = EngagementStats(
        total_personas=1, successful_personas=1, failed_personas=0,
        watch_rate=0, skip_rate=0, average_completion_rate=0,
        rewatch_rate=0, like_rate=0, comment_rate=0, share_rate=0, follow_rate=0,
    )
    rounds: list[RoundResult] = []
    for i, size in enumerate(ROUND_COHORT_SIZES, start=1):
        decision = decide_distribution(distribution_score, PUSH_THRESHOLD)
        rounds.append(RoundResult(
            round_number=i, cohort_size=size, stats=dummy_stats,
            distribution_score=distribution_score, decision=decision, reactions=[],
        ))
        if decision == "STOP":
            break
    return rounds


def _reaction(**overrides) -> PersonaReaction:
    base = dict(
        persona_id="test",
        watch=True,
        completion_rate=0.8,
        rewatch=False,
        like=True,
        comment=False,
        share=False,
        follow=False,
        comment_text=None,
        reasoning="test",
    )
    base.update(overrides)
    return PersonaReaction(**base)


def test_aggregate_engagement_basic():
    reactions = [
        _reaction(watch=True, completion_rate=1.0, like=True, share=True),
        _reaction(watch=False, completion_rate=0.0, like=False, share=False),
    ]
    stats = aggregate_engagement(reactions, total_personas=2, failed_personas=0)
    assert stats.watch_rate == 0.5
    assert stats.skip_rate == 0.5
    assert stats.average_completion_rate == 0.5
    assert stats.like_rate == 0.5
    assert stats.share_rate == 0.5
    assert stats.successful_personas == 2
    assert stats.failed_personas == 0


def test_aggregate_engagement_empty():
    stats = aggregate_engagement([], total_personas=5, failed_personas=5)
    assert stats.total_personas == 5
    assert stats.successful_personas == 0
    assert stats.failed_personas == 5
    assert stats.skip_rate == 1.0


def test_distribution_score_and_decision():
    reactions = [_reaction() for _ in range(10)]
    stats = aggregate_engagement(reactions, total_personas=10, failed_personas=0)
    weights = RecommendationWeights(
        completion=0.30, share=0.25, comment=0.15, like=0.10,
        follow=0.10, rewatch=0.10, skip_penalty=0.20,
    )
    score = compute_distribution_score(stats, weights)
    assert score >= 0.0
    decision = decide_distribution(score, push_threshold=0.70)
    assert decision in {"PUSH", "STOP"}


def test_scenario_distribution_scores_are_ordered():
    """BAD < MEDIUM < GOOD < EXCELLENT, using the real formula/weights."""
    scores = {
        name: compute_distribution_score(_stats(**rates), WEIGHTS)
        for name, rates in SCENARIOS.items()
    }
    assert scores["BAD"] < scores["MEDIUM"] < scores["GOOD"] < scores["EXCELLENT"]
    # BAD's positive terms don't cover the skip penalty -> clamped to 0.
    assert scores["BAD"] == 0.0
    # A realistic "good" video should be able to clear PUSH_THRESHOLD;
    # this is the calibration check for the new default threshold.
    assert scores["GOOD"] >= PUSH_THRESHOLD
    assert scores["MEDIUM"] < PUSH_THRESHOLD


def test_bad_video_stops_early_with_low_score_not_fixed_floor():
    rounds = _simulate_full_run(compute_distribution_score(_stats(**SCENARIOS["BAD"]), WEIGHTS))
    assert len(rounds) == 1
    assert rounds[-1].decision == "STOP"
    score = compute_virality_score(rounds, ROUND_COHORT_SIZES)
    # This is the core Phase 2 regression check: zero real engagement
    # must NOT produce the old ~8/100 floor that came from a fixed
    # round-1 cohort size regardless of content.
    assert score < 5.0


def test_medium_video_stops_but_scores_above_bad():
    bad_rounds = _simulate_full_run(compute_distribution_score(_stats(**SCENARIOS["BAD"]), WEIGHTS))
    medium_rounds = _simulate_full_run(
        compute_distribution_score(_stats(**SCENARIOS["MEDIUM"]), WEIGHTS)
    )
    bad_score = compute_virality_score(bad_rounds, ROUND_COHORT_SIZES)
    medium_score = compute_virality_score(medium_rounds, ROUND_COHORT_SIZES)
    assert medium_rounds[-1].decision == "STOP"
    assert medium_score > bad_score


def test_good_video_pushes_through_all_rounds_and_scores_higher():
    good_rounds = _simulate_full_run(compute_distribution_score(_stats(**SCENARIOS["GOOD"]), WEIGHTS))
    assert len(good_rounds) == len(ROUND_COHORT_SIZES)
    assert good_rounds[-1].decision == "PUSH"
    score = compute_virality_score(good_rounds, ROUND_COHORT_SIZES)
    medium_rounds = _simulate_full_run(
        compute_distribution_score(_stats(**SCENARIOS["MEDIUM"]), WEIGHTS)
    )
    medium_score = compute_virality_score(medium_rounds, ROUND_COHORT_SIZES)
    assert score > medium_score


def test_excellent_video_scores_highest_and_pushes_through_all_rounds():
    excellent_rounds = _simulate_full_run(
        compute_distribution_score(_stats(**SCENARIOS["EXCELLENT"]), WEIGHTS)
    )
    assert len(excellent_rounds) == len(ROUND_COHORT_SIZES)
    assert excellent_rounds[-1].decision == "PUSH"
    excellent_score = compute_virality_score(excellent_rounds, ROUND_COHORT_SIZES)

    good_rounds = _simulate_full_run(compute_distribution_score(_stats(**SCENARIOS["GOOD"]), WEIGHTS))
    good_score = compute_virality_score(good_rounds, ROUND_COHORT_SIZES)

    assert excellent_score > good_score
    assert 0.0 <= excellent_score <= 100.0


def test_virality_score_bounds_and_no_rounds():
    assert compute_virality_score([], ROUND_COHORT_SIZES) == 0.0
    for name, rates in SCENARIOS.items():
        ds = compute_distribution_score(_stats(**rates), WEIGHTS)
        rounds = _simulate_full_run(ds)
        score = compute_virality_score(rounds, ROUND_COHORT_SIZES)
        assert 0.0 <= score <= 100.0


def test_changing_distribution_score_changes_virality_score():
    """Sanity check that virality score is actually sensitive to
    engagement quality, not dominated by a fixed cohort-size term."""
    low = _simulate_full_run(0.05)
    high = _simulate_full_run(0.05)
    # bump the "high" round's distribution_score directly to isolate the
    # effect of engagement quality on the final virality score
    high[0] = high[0].model_copy(update={"distribution_score": 0.5})
    assert compute_virality_score(low, ROUND_COHORT_SIZES) != compute_virality_score(
        high, ROUND_COHORT_SIZES
    )


def test_round1_stop_does_not_force_constant_eight():
    """Regression test for the exact bug found in the Phase 1 diagnosis:
    a single STOPped round-1 (cohort_size=15) used to always produce
    ~7.8-8.0/100 no matter what, because penetration was based on raw
    cohort_size instead of actual engagement."""
    zero_engagement_round = [RoundResult(
        round_number=1, cohort_size=15,
        stats=_stats(watch_rate=0, skip_rate=1.0, average_completion_rate=0,
                     rewatch_rate=0, like_rate=0, comment_rate=0, share_rate=0, follow_rate=0),
        distribution_score=0.0, decision="STOP", reactions=[],
    )]
    score = compute_virality_score(zero_engagement_round, ROUND_COHORT_SIZES)
    assert score == 0.0, f"expected 0.0 for zero engagement, got {score}"


if __name__ == "__main__":
    test_aggregate_engagement_basic()
    test_aggregate_engagement_empty()
    test_distribution_score_and_decision()
    test_scenario_distribution_scores_are_ordered()
    test_bad_video_stops_early_with_low_score_not_fixed_floor()
    test_medium_video_stops_but_scores_above_bad()
    test_good_video_pushes_through_all_rounds_and_scores_higher()
    test_excellent_video_scores_highest_and_pushes_through_all_rounds()
    test_virality_score_bounds_and_no_rounds()
    test_changing_distribution_score_changes_virality_score()
    test_round1_stop_does_not_force_constant_eight()
    print("All tests passed ✅")
