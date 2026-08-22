"""
Offline tests for the Phase 5B curiosity/surprise signal:

- app/models.py: ContentProfile gains curiosity_surprise_strength
  (float, 0.0-1.0, required).
- app/prompts/persona.py: CONTENT_PROFILE_SYSTEM_PROMPT and
  CONTENT_PROFILE_VISION_SYSTEM_PROMPT both document the new field in
  their JSON schema; PERSONA_USER_TEMPLATE exposes it to personas.
- app/simulation/content.py: _FALLBACK_PROFILE_DATA includes a neutral
  0.5 default for the new field.

None of these tests make real network calls to Groq or Ollama.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models import ContentProfile
from app.prompts.persona import (
    CONTENT_PROFILE_SYSTEM_PROMPT,
    CONTENT_PROFILE_VISION_SYSTEM_PROMPT,
    PERSONA_USER_TEMPLATE,
    build_persona_prompts,
)
from app.personas.definitions import PERSONA_POOL
from app.simulation.content import _FALLBACK_PROFILE_DATA


def _profile_kwargs(**overrides) -> dict:
    base = dict(
        title="Guy tries a spicy noodle challenge",
        summary="A short clip of someone reacting to extremely spicy noodles.",
        duration_seconds=18.0,
        hook_strength=0.7,
        curiosity_surprise_strength=0.6,
        educational_value=0.1,
        entertainment_value=0.8,
        emotional_intensity=0.6,
        shareability=0.5,
        call_to_action=None,
        target_audience="young adults who enjoy food/reaction content",
    )
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# ContentProfile field validation
# ---------------------------------------------------------------------------

def test_content_profile_accepts_curiosity_surprise_strength_0_0():
    profile = ContentProfile(**_profile_kwargs(curiosity_surprise_strength=0.0))
    assert profile.curiosity_surprise_strength == 0.0


def test_content_profile_accepts_curiosity_surprise_strength_1_0():
    profile = ContentProfile(**_profile_kwargs(curiosity_surprise_strength=1.0))
    assert profile.curiosity_surprise_strength == 1.0


def test_content_profile_rejects_curiosity_surprise_strength_out_of_range():
    with pytest.raises(ValidationError):
        ContentProfile(**_profile_kwargs(curiosity_surprise_strength=1.5))

    with pytest.raises(ValidationError):
        ContentProfile(**_profile_kwargs(curiosity_surprise_strength=-0.1))


def test_content_profile_requires_curiosity_surprise_strength():
    kwargs = _profile_kwargs()
    del kwargs["curiosity_surprise_strength"]
    with pytest.raises(ValidationError):
        ContentProfile(**kwargs)


def test_content_profile_existing_fields_still_present_and_unchanged():
    profile = ContentProfile(**_profile_kwargs())
    assert profile.title == "Guy tries a spicy noodle challenge"
    assert profile.hook_strength == 0.7
    assert profile.educational_value == 0.1
    assert profile.entertainment_value == 0.8
    assert profile.emotional_intensity == 0.6
    assert profile.shareability == 0.5
    assert profile.call_to_action is None
    assert profile.target_audience == "young adults who enjoy food/reaction content"


# ---------------------------------------------------------------------------
# Fallback profile
# ---------------------------------------------------------------------------

def test_fallback_profile_includes_neutral_curiosity_surprise_strength():
    assert "curiosity_surprise_strength" in _FALLBACK_PROFILE_DATA
    assert _FALLBACK_PROFILE_DATA["curiosity_surprise_strength"] == 0.5


def test_fallback_profile_data_is_still_a_valid_content_profile():
    # duration_seconds is injected separately by _parse_profile, so add it here.
    data = dict(_FALLBACK_PROFILE_DATA)
    data["duration_seconds"] = 12.0
    profile = ContentProfile.model_validate(data)
    assert profile.curiosity_surprise_strength == 0.5
    # Other fallback values untouched.
    assert profile.hook_strength == 0.5
    assert profile.educational_value == 0.5
    assert profile.entertainment_value == 0.5
    assert profile.emotional_intensity == 0.5
    assert profile.shareability == 0.5


# ---------------------------------------------------------------------------
# Content-profile prompts document the new field
# ---------------------------------------------------------------------------

def test_transcript_only_content_prompt_documents_new_field():
    assert "curiosity_surprise_strength" in CONTENT_PROFILE_SYSTEM_PROMPT
    assert "mystery" in CONTENT_PROFILE_SYSTEM_PROMPT.lower()
    assert "surprise" in CONTENT_PROFILE_SYSTEM_PROMPT.lower()
    # Still calibrated / not defaulting to high scores.
    assert "most content is mediocre" in CONTENT_PROFILE_SYSTEM_PROMPT.lower()


def test_vision_content_prompt_documents_new_field():
    assert "curiosity_surprise_strength" in CONTENT_PROFILE_VISION_SYSTEM_PROMPT
    assert "mystery" in CONTENT_PROFILE_VISION_SYSTEM_PROMPT.lower()
    assert "surprise" in CONTENT_PROFILE_VISION_SYSTEM_PROMPT.lower()
    assert "most content is mediocre" in CONTENT_PROFILE_VISION_SYSTEM_PROMPT.lower()


def test_content_prompts_distinguish_hook_from_curiosity():
    for prompt in (CONTENT_PROFILE_SYSTEM_PROMPT, CONTENT_PROFILE_VISION_SYSTEM_PROMPT):
        lowered = prompt.lower()
        # The prompt should explicitly warn against conflating a strong hook
        # with strong curiosity/surprise.
        assert "hook_strength" in lowered
        assert "not automatically" in lowered or "separately" in lowered


# ---------------------------------------------------------------------------
# Persona user prompt exposes curiosity/surprise
# ---------------------------------------------------------------------------

def test_persona_user_template_includes_curiosity_surprise_placeholder():
    assert "curiosity_surprise_strength" in PERSONA_USER_TEMPLATE


def test_build_persona_prompts_renders_curiosity_surprise_value():
    persona = PERSONA_POOL[0]
    profile = ContentProfile(**_profile_kwargs(curiosity_surprise_strength=0.85))

    _, user_prompt = build_persona_prompts(persona, profile)

    assert "0.85" in user_prompt
    assert "curiosity" in user_prompt.lower()


def test_persona_user_prompt_notes_curiosity_is_not_guaranteed_positive():
    persona = PERSONA_POOL[0]
    profile = ContentProfile(**_profile_kwargs(curiosity_surprise_strength=0.9))

    _, user_prompt = build_persona_prompts(persona, profile)
    lowered = user_prompt.lower()

    assert "does not" in lowered or "not guarantee" in lowered or "not automatically" in lowered
