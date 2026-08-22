"""
Simulation engine: orchestrates rounds of concurrent persona evaluation.

This module owns the two most important control-flow requirements from
the spec:

1. PARALLEL EXECUTION — `run_round()` fires off every persona's
   `.evaluate()` coroutine at once via `asyncio.gather()`, instead of
   awaiting them one at a time in a for-loop. A `Semaphore` caps how
   many run truly concurrently (MAX_CONCURRENT_AGENTS), so we don't
   hammer a local Ollama server or hit provider rate limits.

2. FAULT ISOLATION — `asyncio.gather(..., return_exceptions=True)`
   means one persona raising an exception does NOT cancel the others.
   We separate successes from failures afterwards and keep going.
"""
from __future__ import annotations

import asyncio
import random

from app.config import Settings
from app.llm.base import LLMProvider
from app.models import ContentProfile, Persona, PersonaReaction, RoundResult
from app.personas.agent import PersonaAgent, PersonaEvaluationError
from app.simulation.aggregation import aggregate_engagement
from app.simulation.scoring import compute_distribution_score, decide_distribution


def build_cohort(pool: list[Persona], size: int, rng: random.Random) -> list[Persona]:
    """Pick `size` personas for a round from the fixed pool.

    If size <= len(pool), sample without repeats (each persona is a
    distinct viewer). If size > len(pool) (later rounds simulate a
    bigger audience), sample WITH repeats — same archetypes, different
    "instances" of that type of viewer, which is a reasonable MVP
    approximation of a larger population without needing to invent an
    unbounded number of new persona archetypes.
    """
    if size <= len(pool):
        return rng.sample(pool, size)
    return [rng.choice(pool) for _ in range(size)]


async def _evaluate_with_semaphore(
    agent: PersonaAgent,
    content: ContentProfile,
    semaphore: asyncio.Semaphore,
) -> PersonaReaction:
    async with semaphore:
        return await agent.evaluate(content)


async def run_round(
    round_number: int,
    cohort: list[Persona],
    content: ContentProfile,
    llm: LLMProvider,
    settings: Settings,
    on_persona_result=None,
) -> RoundResult:
    """Run one round: evaluate `cohort` concurrently, aggregate, score."""
    semaphore = asyncio.Semaphore(settings.max_concurrent_agents)
    agents = [PersonaAgent(p, llm) for p in cohort]

    tasks = [_evaluate_with_semaphore(agent, content, semaphore) for agent in agents]

    # KEY LINE: run all tasks concurrently; don't let one failure kill the batch.
    results = await asyncio.gather(*tasks, return_exceptions=True)

    reactions: list[PersonaReaction] = []
    failures = 0
    for persona, result in zip(cohort, results):
        if isinstance(result, Exception):
            failures += 1
            msg = (
                str(result)
                if isinstance(result, PersonaEvaluationError)
                else f"[{persona.name}] Unexpected error: {result}"
            )
            print(f"  ⚠️  Persona failed: {msg}")
        else:
            reactions.append(result)
        if on_persona_result:
            on_persona_result(persona, result)

    stats = aggregate_engagement(reactions, total_personas=len(cohort), failed_personas=failures)
    score = compute_distribution_score(stats, settings.weights)
    decision = decide_distribution(score, settings.push_threshold)

    return RoundResult(
        round_number=round_number,
        cohort_size=len(cohort),
        stats=stats,
        distribution_score=round(score, 3),
        decision=decision,
        reactions=reactions,
    )


async def run_simulation(
    content: ContentProfile,
    persona_pool: list[Persona],
    llm: LLMProvider,
    settings: Settings,
    seed: int | None = None,
) -> list[RoundResult]:
    """Run multiple rounds with growing cohort sizes until STOP or rounds exhausted.

    `seed` (Phase 5D) controls ONLY persona cohort sampling, via a single
    local `random.Random(seed)` instance created once per simulation
    execution and reused across every round -- the global `random`
    module is never touched, so this has zero effect on other code that
    happens to use `random` elsewhere, and zero effect on LLM
    temperature/output. `seed=None` (the default) means "use normal,
    unseeded random cohort sampling", exactly as before this phase; a
    given integer seed makes the same persona_pool + same
    round_cohort_sizes reproduce the same cohort membership/order every
    run, while a different seed can produce a different cohort.
    """
    rng = random.Random(seed)
    rounds: list[RoundResult] = []

    for i, cohort_size in enumerate(settings.round_cohort_sizes, start=1):
        cohort = build_cohort(persona_pool, cohort_size, rng)
        print(f"\nROUND {i} — evaluating {len(cohort)} personas concurrently "
              f"(max {settings.max_concurrent_agents} at once)...")
        round_result = await run_round(i, cohort, content, llm, settings)
        rounds.append(round_result)

        print(f"  Distribution score: {round_result.distribution_score:.2f} "
              f"-> {round_result.decision}")

        if round_result.decision == "STOP":
            break

    return rounds
