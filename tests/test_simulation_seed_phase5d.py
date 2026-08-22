"""
Offline tests for the Phase 5D cohort-sampling reproducibility feature:

- app/simulation/engine.py: build_cohort()/run_simulation() take an
  optional local `random.Random` seed that controls ONLY which
  personas get sampled into each round's cohort (and in what order),
  never the global `random` module and never LLM temperature/output.
- app/config.py: Settings.simulation_seed reads the optional
  SIMULATION_SEED env var (None when unset -> normal random behavior).

None of these tests make real network calls to Groq or Ollama.
"""
from __future__ import annotations

import json
import random

import pytest

from app.config import RecommendationWeights, Settings
from app.llm.base import LLMProvider
from app.models import ContentProfile
from app.personas.definitions import PERSONA_POOL, get_persona_pool
from app.simulation.engine import build_cohort, run_simulation

WEIGHTS = RecommendationWeights(
    completion=0.30, share=0.25, comment=0.15, like=0.10,
    follow=0.10, rewatch=0.10, skip_penalty=0.20,
)

VALID_CONTENT_PROFILE = ContentProfile(
    title="Blindfold challenge, World Cup VIP reveal",
    summary="A mystery journey ending in a surprise VIP reveal.",
    duration_seconds=45.0,
    hook_strength=0.7,
    curiosity_surprise_strength=0.9,
    educational_value=0.1,
    entertainment_value=0.8,
    emotional_intensity=0.7,
    shareability=0.6,
    call_to_action=None,
    target_audience="general short-form audience",
)


def _settings(**overrides) -> Settings:
    base = dict(
        model_provider="groq",
        groq_api_key="fake-key",
        groq_model="openai/gpt-oss-120b",
        weights=WEIGHTS,
        push_threshold=0.30,
        max_concurrent_agents=3,
        round_cohort_sizes=[15, 30, 60],
    )
    base.update(overrides)
    return Settings(**base)


class _AllSkipLLM(LLMProvider):
    """Every persona skips -- keeps a run_simulation() test to 1 round (STOP)."""

    async def complete_json(self, system_prompt: str, user_prompt: str, *, temperature: float = 0.7) -> str:
        payload = {
            "persona_id": "placeholder",
            "watch": False,
            "completion_rate": 0.0,
            "rewatch": False,
            "like": False,
            "comment": False,
            "share": False,
            "follow": False,
            "comment_text": None,
            "reasoning": "Not interested, skipped immediately.",
        }
        return json.dumps(payload)

    async def complete_text(self, system_prompt: str, user_prompt: str, *, temperature: float = 0.7) -> str:
        return "some prose"


# ---------------------------------------------------------------------------
# build_cohort() determinism
# ---------------------------------------------------------------------------

def test_same_seed_produces_identical_cohort_membership_and_order():
    pool = get_persona_pool()

    cohort_a = build_cohort(pool, 15, random.Random(42))
    cohort_b = build_cohort(pool, 15, random.Random(42))

    assert [p.id for p in cohort_a] == [p.id for p in cohort_b]


def test_different_seeds_can_produce_different_cohorts():
    pool = get_persona_pool()

    cohort_a = build_cohort(pool, 15, random.Random(1))
    cohort_b = build_cohort(pool, 15, random.Random(2))

    # With an 18-person pool and a 15-person sample, different seeds are
    # overwhelmingly likely to select/order differently.
    assert [p.id for p in cohort_a] != [p.id for p in cohort_b]


def test_no_seed_preserves_normal_random_behavior():
    pool = get_persona_pool()

    # random.Random(None) seeds from OS entropy each time it's constructed,
    # exactly like plain unseeded `random` -- two independent instances
    # should (overwhelmingly likely) disagree, proving no hidden fixed
    # default seed crept in.
    cohort_a = build_cohort(pool, 15, random.Random(None))
    cohort_b = build_cohort(pool, 15, random.Random(None))

    assert [p.id for p in cohort_a] != [p.id for p in cohort_b]


def test_build_cohort_with_size_greater_than_pool_samples_with_repeats():
    pool = get_persona_pool()
    cohort = build_cohort(pool, 30, random.Random(7))
    assert len(cohort) == 30
    # Sampling-with-repeats for round 2 (30 > 18-person pool) is expected
    # to reuse some archetypes.
    assert len({p.id for p in cohort}) <= len(pool)


# ---------------------------------------------------------------------------
# RNG is local, never touches global random state
# ---------------------------------------------------------------------------

def test_build_cohort_does_not_mutate_global_random_state():
    pool = get_persona_pool()

    random.seed(999)
    expected_next_value = random.random()

    # Reset to the same global state, then run build_cohort with an
    # unrelated LOCAL seeded Random instance in between.
    random.seed(999)
    local_rng = random.Random(12345)
    build_cohort(pool, 15, local_rng)
    build_cohort(pool, 60, local_rng)  # exercise the with-repeats path too

    # The global random module's sequence must be completely unaffected
    # by any of the local_rng calls above.
    actual_next_value = random.random()
    assert actual_next_value == expected_next_value


# ---------------------------------------------------------------------------
# run_simulation() threads a single RNG per execution
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_simulation_same_seed_yields_same_round1_cohort_ids():
    settings = _settings()
    llm = _AllSkipLLM()

    rounds_a = await run_simulation(
        content=VALID_CONTENT_PROFILE,
        persona_pool=get_persona_pool(),
        llm=llm,
        settings=settings,
        seed=2024,
    )
    rounds_b = await run_simulation(
        content=VALID_CONTENT_PROFILE,
        persona_pool=get_persona_pool(),
        llm=llm,
        settings=settings,
        seed=2024,
    )

    ids_a = sorted(r.persona_id for r in rounds_a[0].reactions)
    ids_b = sorted(r.persona_id for r in rounds_b[0].reactions)
    assert ids_a == ids_b


@pytest.mark.asyncio
async def test_run_simulation_stops_early_and_produces_valid_round():
    # All-skip LLM -> distribution_score should be well below push_threshold
    # -> exactly 1 round, proving existing STOP behavior still works
    # end-to-end with the seeded cohort-sampling path wired in.
    settings = _settings()
    llm = _AllSkipLLM()

    rounds = await run_simulation(
        content=VALID_CONTENT_PROFILE,
        persona_pool=get_persona_pool(),
        llm=llm,
        settings=settings,
        seed=1,
    )

    assert len(rounds) == 1
    assert rounds[0].decision == "STOP"
    assert rounds[0].cohort_size == 15


# ---------------------------------------------------------------------------
# Pool size / round cohort sizes unchanged by this phase
# ---------------------------------------------------------------------------

def test_persona_pool_still_18():
    assert len(PERSONA_POOL) == 18


def test_default_round_cohort_sizes_still_15_30_60():
    settings = _settings()
    assert settings.round_cohort_sizes == [15, 30, 60]


# ---------------------------------------------------------------------------
# Config: SIMULATION_SEED
# ---------------------------------------------------------------------------

def test_get_optional_int_returns_none_when_unset(monkeypatch):
    from app.config import _get_optional_int

    monkeypatch.delenv("SIMULATION_SEED", raising=False)
    assert _get_optional_int("SIMULATION_SEED") is None


def test_get_optional_int_returns_none_for_empty_string(monkeypatch):
    from app.config import _get_optional_int

    monkeypatch.setenv("SIMULATION_SEED", "")
    assert _get_optional_int("SIMULATION_SEED") is None


def test_get_optional_int_parses_set_value(monkeypatch):
    from app.config import _get_optional_int

    monkeypatch.setenv("SIMULATION_SEED", "777")
    assert _get_optional_int("SIMULATION_SEED") == 777


def test_settings_simulation_seed_field_reflects_env_at_reload(monkeypatch):
    """Settings' dataclass field defaults (like every other Settings field,
    e.g. model_provider/push_threshold) are evaluated once at module
    import time from the environment -- this is the existing, pre-Phase-5D
    pattern used throughout app/config.py. So to observe a *new*
    SIMULATION_SEED value flowing into Settings.simulation_seed's default,
    the module has to be reloaded after the env var changes, exactly like
    it would be if the process were restarted with a different .env.
    """
    import importlib

    import app.config as config_module

    monkeypatch.setenv("SIMULATION_SEED", "555")
    try:
        reloaded = importlib.reload(config_module)
        settings = reloaded.Settings(
            model_provider="groq", groq_api_key="fake-key", groq_model="openai/gpt-oss-120b",
        )
        assert settings.simulation_seed == 555
    finally:
        monkeypatch.delenv("SIMULATION_SEED", raising=False)
        importlib.reload(config_module)  # restore normal (unset) state for other tests


def test_settings_simulation_seed_can_be_passed_explicitly():
    # The common/robust way callers (including our own _settings() helper
    # in this file, and main.py) get a specific seed onto Settings --
    # doesn't depend on module reload timing at all.
    settings = _settings(simulation_seed=None)
    assert settings.simulation_seed is None

    settings_with_seed = _settings(simulation_seed=123)
    assert settings_with_seed.simulation_seed == 123
