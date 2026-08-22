"""
Offline tests for the Phase 5C persona-pool expansion:

- app/personas/definitions.py: PERSONA_POOL grows from 15 to 18 entries
  by adding three broad-appeal personas (Surprise/Curiosity Viewer,
  Short-Form Entertainment Viewer, Mainstream Casual Viewer) without
  touching any of the original 15.

None of these tests make real network calls to Groq or Ollama.
"""
from __future__ import annotations

from app.personas.definitions import PERSONA_POOL, get_persona_pool
from app.models import Persona

ORIGINAL_15_NAMES = {
    "AI/ML Student",
    "Software Developer",
    "College Student",
    "Entrepreneur",
    "Gamer",
    "Meme/Entertainment User",
    "Fitness Enthusiast",
    "Productivity Enthusiast",
    "Finance/Business User",
    "Fashion/Lifestyle User",
    "General Social Media User",
    "Tech Professional",
    "Creator/Influencer",
    "Casual Viewer",
    "Completely Unrelated User",
}

NEW_3_NAMES = {
    "Surprise/Curiosity Viewer",
    "Short-Form Entertainment Viewer",
    "Mainstream Casual Viewer",
}

# Known-good tendency values for the original 15 personas, captured before
# Phase 5C, keyed by persona id. Used to assert nothing about them changed.
ORIGINAL_TENDENCIES_BY_ID = {
    "ai_ml_student": dict(
        attention_span=0.6, entertainment_preference=0.3, educational_preference=0.9,
        sharing_tendency=0.5, commenting_tendency=0.4, following_tendency=0.5,
    ),
    "software_developer": dict(
        attention_span=0.5, entertainment_preference=0.3, educational_preference=0.8,
        sharing_tendency=0.4, commenting_tendency=0.3, following_tendency=0.4,
    ),
    "college_student": dict(
        attention_span=0.3, entertainment_preference=0.8, educational_preference=0.3,
        sharing_tendency=0.7, commenting_tendency=0.6, following_tendency=0.4,
    ),
    "entrepreneur": dict(
        attention_span=0.5, entertainment_preference=0.3, educational_preference=0.7,
        sharing_tendency=0.6, commenting_tendency=0.3, following_tendency=0.5,
    ),
    "gamer": dict(
        attention_span=0.4, entertainment_preference=0.9, educational_preference=0.2,
        sharing_tendency=0.6, commenting_tendency=0.7, following_tendency=0.3,
    ),
    "meme_entertainment_user": dict(
        attention_span=0.25, entertainment_preference=0.95, educational_preference=0.1,
        sharing_tendency=0.8, commenting_tendency=0.7, following_tendency=0.2,
    ),
    "fitness_enthusiast": dict(
        attention_span=0.5, entertainment_preference=0.4, educational_preference=0.7,
        sharing_tendency=0.5, commenting_tendency=0.4, following_tendency=0.5,
    ),
    "productivity_enthusiast": dict(
        attention_span=0.6, entertainment_preference=0.3, educational_preference=0.85,
        sharing_tendency=0.5, commenting_tendency=0.3, following_tendency=0.5,
    ),
    "finance_business_user": dict(
        attention_span=0.55, entertainment_preference=0.25, educational_preference=0.8,
        sharing_tendency=0.4, commenting_tendency=0.35, following_tendency=0.45,
    ),
    "fashion_lifestyle_user": dict(
        attention_span=0.4, entertainment_preference=0.7, educational_preference=0.2,
        sharing_tendency=0.6, commenting_tendency=0.4, following_tendency=0.5,
    ),
    "general_social_media_user": dict(
        attention_span=0.4, entertainment_preference=0.55, educational_preference=0.4,
        sharing_tendency=0.4, commenting_tendency=0.3, following_tendency=0.3,
    ),
    "tech_professional": dict(
        attention_span=0.55, entertainment_preference=0.35, educational_preference=0.75,
        sharing_tendency=0.45, commenting_tendency=0.4, following_tendency=0.45,
    ),
    "creator_influencer": dict(
        attention_span=0.5, entertainment_preference=0.6, educational_preference=0.5,
        sharing_tendency=0.6, commenting_tendency=0.6, following_tendency=0.5,
    ),
    "casual_viewer": dict(
        attention_span=0.35, entertainment_preference=0.6, educational_preference=0.3,
        sharing_tendency=0.25, commenting_tendency=0.15, following_tendency=0.15,
    ),
    "completely_unrelated_user": dict(
        attention_span=0.3, entertainment_preference=0.5, educational_preference=0.3,
        sharing_tendency=0.15, commenting_tendency=0.1, following_tendency=0.1,
    ),
}


def _by_id() -> dict[str, Persona]:
    return {p.id: p for p in PERSONA_POOL}


# ---------------------------------------------------------------------------
# Pool size
# ---------------------------------------------------------------------------

def test_persona_pool_size_is_18():
    assert len(PERSONA_POOL) == 18


def test_get_persona_pool_returns_18_and_is_a_copy():
    pool = get_persona_pool()
    assert len(pool) == 18
    assert pool is not PERSONA_POOL  # returns a copy, not the module-level list itself


# ---------------------------------------------------------------------------
# Old personas preserved
# ---------------------------------------------------------------------------

def test_all_15_original_persona_names_still_exist():
    names = {p.name for p in PERSONA_POOL}
    missing = ORIGINAL_15_NAMES - names
    assert not missing, f"Missing original personas: {missing}"


def test_original_persona_tendencies_unchanged():
    by_id = _by_id()
    for persona_id, expected in ORIGINAL_TENDENCIES_BY_ID.items():
        assert persona_id in by_id, f"Original persona '{persona_id}' is missing"
        persona = by_id[persona_id]
        for field, expected_value in expected.items():
            actual_value = getattr(persona, field)
            assert actual_value == expected_value, (
                f"{persona_id}.{field} changed: expected {expected_value}, got {actual_value}"
            )


# ---------------------------------------------------------------------------
# New personas exist
# ---------------------------------------------------------------------------

def test_3_new_broad_appeal_persona_names_exist():
    names = {p.name for p in PERSONA_POOL}
    missing = NEW_3_NAMES - names
    assert not missing, f"Missing new broad-appeal personas: {missing}"


def test_new_personas_have_expected_ids():
    ids = {p.id for p in PERSONA_POOL}
    assert "surprise_curiosity_viewer" in ids
    assert "short_form_entertainment_viewer" in ids
    assert "mainstream_casual_viewer" in ids


# ---------------------------------------------------------------------------
# Validity / no duplicates
# ---------------------------------------------------------------------------

def test_all_personas_have_valid_required_fields():
    for persona in PERSONA_POOL:
        assert isinstance(persona, Persona)
        assert persona.id
        assert persona.name
        assert persona.age_range
        assert persona.interests
        assert persona.personality
        for field in [
            "attention_span",
            "entertainment_preference",
            "educational_preference",
            "sharing_tendency",
            "commenting_tendency",
            "following_tendency",
        ]:
            value = getattr(persona, field)
            assert 0.0 <= value <= 1.0, f"{persona.id}.{field}={value} out of [0,1]"


def test_no_duplicate_persona_names():
    names = [p.name for p in PERSONA_POOL]
    assert len(names) == len(set(names))


def test_no_duplicate_persona_ids():
    ids = [p.id for p in PERSONA_POOL]
    assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# New personas: distinct interests, not hardcoded to always watch
# ---------------------------------------------------------------------------

def test_new_personas_have_distinct_interest_lists():
    by_name = {p.name: set(p.interests) for p in PERSONA_POOL if p.name in NEW_3_NAMES}
    assert len(by_name) == 3

    surprise_interests = by_name["Surprise/Curiosity Viewer"]
    shortform_interests = by_name["Short-Form Entertainment Viewer"]
    mainstream_interests = by_name["Mainstream Casual Viewer"]

    # No two of the three new personas share an identical interest list.
    assert surprise_interests != shortform_interests
    assert surprise_interests != mainstream_interests
    assert shortform_interests != mainstream_interests


def test_new_personas_are_not_hardcoded_to_always_watch():
    # Personas are pure data (Persona model) -- there is no "always_watch"
    # or similar hardcoded field/flag anywhere on the model or the new
    # entries. The actual watch/skip decision is made by the LLM at
    # evaluation time (app/personas/agent.py, untouched by this phase),
    # so verify the model simply has no such deterministic field.
    persona_fields = set(Persona.model_fields.keys())
    assert "always_watch" not in persona_fields
    assert "watch" not in persona_fields
    assert "guaranteed_watch" not in persona_fields

    new_personas = [p for p in PERSONA_POOL if p.name in NEW_3_NAMES]
    assert len(new_personas) == 3
    for persona in new_personas:
        # Tendencies are moderate/high as designed, but not fixed at 1.0
        # (i.e. not deterministically maxed-out / guaranteed positive).
        assert persona.entertainment_preference < 1.0
        assert persona.attention_span < 1.0
        assert persona.following_tendency < 1.0
