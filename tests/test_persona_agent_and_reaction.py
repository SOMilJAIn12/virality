"""
Offline tests for the Phase 5A persona fixes:

- app/personas/agent.py: PersonaAgent calls the LLM with temperature=0.4
  (lowered from 0.8) to reduce excessive run-to-run stochasticity.
- app/prompts/persona.py: PERSONA_SYSTEM_TEMPLATE no longer tells the
  model to default to negativity, and explicitly documents hooks/
  curiosity/entertainment as valid reasons to watch independent of
  topical interest, plus the watch=false consistency rule.
- app/models.py: PersonaReaction enforces watch=false => every
  downstream engagement field is forced to its "didn't happen" state,
  while watch=true leaves all engagement fields independently
  determined by the persona.

None of these tests make real network calls to Groq or Ollama.
"""
from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from app.llm.base import LLMProvider
from app.models import ContentProfile, Persona, PersonaReaction
from app.personas.agent import PersonaAgent
from app.prompts.persona import PERSONA_SYSTEM_TEMPLATE


VALID_CONTENT_PROFILE = ContentProfile(
    title="Guy tries a spicy noodle challenge",
    summary="A short clip of someone reacting to extremely spicy noodles.",
    duration_seconds=18.0,
    hook_strength=0.7,
    curiosity_surprise_strength=0.3,
    educational_value=0.1,
    entertainment_value=0.8,
    emotional_intensity=0.6,
    shareability=0.5,
    call_to_action=None,
    target_audience="young adults who enjoy food/reaction content",
)

SAMPLE_PERSONA = Persona(
    id="test_persona",
    name="Test Persona",
    age_range="18-24",
    interests=["cooking", "food science"],
    personality="Curious and easily entertained.",
    attention_span=0.6,
    entertainment_preference=0.7,
    educational_preference=0.4,
    sharing_tendency=0.5,
    commenting_tendency=0.4,
    following_tendency=0.3,
)


def _valid_watch_true_payload(**overrides) -> dict:
    payload = {
        "persona_id": SAMPLE_PERSONA.id,
        "watch": True,
        "completion_rate": 0.8,
        "rewatch": False,
        "like": True,
        "comment": False,
        "share": False,
        "follow": False,
        "comment_text": None,
        "reasoning": "The hook grabbed me even though it's not my main interest.",
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# CHANGE 1 — persona temperature lowered to 0.4
# ---------------------------------------------------------------------------

class _RecordingLLM(LLMProvider):
    """Captures the temperature passed into complete_json."""

    def __init__(self, response: dict):
        self.response = response
        self.calls: list[dict] = []

    async def complete_json(self, system_prompt: str, user_prompt: str, *, temperature: float = 0.7) -> str:
        self.calls.append(
            {"system_prompt": system_prompt, "user_prompt": user_prompt, "temperature": temperature}
        )
        return json.dumps(self.response)

    async def complete_text(self, system_prompt: str, user_prompt: str, *, temperature: float = 0.7) -> str:
        return "some prose"


@pytest.mark.asyncio
async def test_persona_agent_uses_temperature_0_4():
    llm = _RecordingLLM(_valid_watch_true_payload())
    agent = PersonaAgent(SAMPLE_PERSONA, llm)

    reaction = await agent.evaluate(VALID_CONTENT_PROFILE)

    assert len(llm.calls) == 1
    assert llm.calls[0]["temperature"] == 0.4
    assert reaction.persona_id == SAMPLE_PERSONA.id


# ---------------------------------------------------------------------------
# CHANGE 2 — persona prompt bias fix
# ---------------------------------------------------------------------------

def test_persona_prompt_no_longer_forces_unconditional_negativity():
    rendered = PERSONA_SYSTEM_TEMPLATE.format(
        name=SAMPLE_PERSONA.name,
        age_range=SAMPLE_PERSONA.age_range,
        interests=", ".join(SAMPLE_PERSONA.interests),
        personality=SAMPLE_PERSONA.personality,
        attention_span=SAMPLE_PERSONA.attention_span,
        entertainment_preference=SAMPLE_PERSONA.entertainment_preference,
        educational_preference=SAMPLE_PERSONA.educational_preference,
        sharing_tendency=SAMPLE_PERSONA.sharing_tendency,
        commenting_tendency=SAMPLE_PERSONA.commenting_tendency,
        following_tendency=SAMPLE_PERSONA.following_tendency,
        persona_id=SAMPLE_PERSONA.id,
    )

    # The old unconditional "should often skip" line tied to low interest-overlap
    # is gone...
    assert "low interest-overlap with the content should often skip" not in rendered

    # ...and the new balanced-decision language is present.
    assert "hook" in rendered.lower()
    assert "curiosity" in rendered.lower()
    assert "entertainment" in rendered.lower()
    assert "should not" in rendered.lower() or "should NOT" in rendered

    # All persona fields are still preserved in the prompt.
    for field in [
        SAMPLE_PERSONA.name,
        SAMPLE_PERSONA.age_range,
        SAMPLE_PERSONA.personality,
    ]:
        assert field in rendered
    for tendency in [
        "attention_span",
        "entertainment_preference",
        "educational_preference",
        "sharing_tendency",
        "commenting_tendency",
        "following_tendency",
    ]:
        assert tendency in rendered


def test_persona_prompt_documents_watch_false_consistency_rule():
    rendered = PERSONA_SYSTEM_TEMPLATE.format(
        name=SAMPLE_PERSONA.name,
        age_range=SAMPLE_PERSONA.age_range,
        interests=", ".join(SAMPLE_PERSONA.interests),
        personality=SAMPLE_PERSONA.personality,
        attention_span=SAMPLE_PERSONA.attention_span,
        entertainment_preference=SAMPLE_PERSONA.entertainment_preference,
        educational_preference=SAMPLE_PERSONA.educational_preference,
        sharing_tendency=SAMPLE_PERSONA.sharing_tendency,
        commenting_tendency=SAMPLE_PERSONA.commenting_tendency,
        following_tendency=SAMPLE_PERSONA.following_tendency,
        persona_id=SAMPLE_PERSONA.id,
    )

    assert "watch=false" in rendered
    assert "completion_rate must be 0" in rendered
    assert "comment_text=null" in rendered


# ---------------------------------------------------------------------------
# CHANGE 3 — PersonaReaction watch/engagement consistency enforcement
# ---------------------------------------------------------------------------

def test_watch_false_forces_all_engagement_fields_off():
    reaction = PersonaReaction(
        persona_id="p1",
        watch=False,
        completion_rate=0.9,  # LLM incorrectly returned nonzero
        rewatch=True,
        like=True,
        comment=True,
        share=True,
        follow=True,
        comment_text="great video!",
        reasoning="Not really my thing but I guess I engaged anyway.",
    )

    assert reaction.watch is False
    assert reaction.completion_rate == 0.0
    assert reaction.rewatch is False
    assert reaction.like is False
    assert reaction.comment is False
    assert reaction.share is False
    assert reaction.follow is False
    assert reaction.comment_text is None


def test_watch_true_leaves_engagement_fields_independently_determined():
    reaction = PersonaReaction(**_valid_watch_true_payload(
        like=False, comment=False, share=False, follow=False, rewatch=False, completion_rate=0.55,
    ))

    assert reaction.watch is True
    assert reaction.completion_rate == 0.55
    # All-false engagement is still valid when watch=True -- nothing should
    # be force-flipped to true.
    assert reaction.like is False
    assert reaction.comment is False
    assert reaction.share is False
    assert reaction.follow is False
    assert reaction.rewatch is False


def test_watch_true_with_completion_rate_between_0_and_1_is_valid():
    reaction = PersonaReaction(**_valid_watch_true_payload(completion_rate=0.42))
    assert reaction.watch is True
    assert reaction.completion_rate == 0.42


def test_completion_rate_out_of_bounds_is_rejected():
    # Field(ge=0, le=1) rejects out-of-range values outright (pre-existing
    # behavior, unchanged by Phase 5A) -- completion_rate always ends up
    # within [0, 1] for any valid PersonaReaction.
    with pytest.raises(ValidationError):
        PersonaReaction(**_valid_watch_true_payload(completion_rate=1.5))

    with pytest.raises(ValidationError):
        PersonaReaction(**_valid_watch_true_payload(completion_rate=-0.3))


# ---------------------------------------------------------------------------
# CHANGE 4 — persona agent end-to-end still normalizes inconsistent LLM output
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_agent_normalizes_inconsistent_watch_false_llm_response():
    inconsistent_payload = {
        "persona_id": SAMPLE_PERSONA.id,
        "watch": False,
        "completion_rate": 0.6,
        "rewatch": True,
        "like": True,
        "comment": True,
        "share": True,
        "follow": True,
        "comment_text": "loved it",
        "reasoning": "I skipped it but somehow the model still marked engagement.",
    }
    llm = _RecordingLLM(inconsistent_payload)
    agent = PersonaAgent(SAMPLE_PERSONA, llm)

    reaction = await agent.evaluate(VALID_CONTENT_PROFILE)

    assert reaction.watch is False
    assert reaction.completion_rate == 0.0
    assert reaction.rewatch is False
    assert reaction.like is False
    assert reaction.comment is False
    assert reaction.share is False
    assert reaction.follow is False
    assert reaction.comment_text is None
