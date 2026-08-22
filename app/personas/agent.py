"""
PersonaAgent — the core "agent" of this MVP.

Why is this an "agent" at all, and why doesn't it need LangGraph?
-------------------------------------------------------------------
An "agent" here just means: something with (1) a persistent identity/goal
(the persona profile), (2) the ability to perceive input (the content
profile), and (3) the ability to make an autonomous decision using an
LLM. That's it — no tool use, no multi-step planning, no graph of nodes.
A plain Python class with an `evaluate()` method is a perfectly good
agent for this. Frameworks like LangGraph exist for *orchestrating many
agents with branching/looping control flow*; we don't need that here,
because our "orchestration" is just "run N of these concurrently and
collect the results" — which asyncio.gather() already does for us.

Why async?
----------
Each persona.evaluate() call spends almost all of its time *waiting* on
a network response from the LLM (Ollama/Groq), not doing CPU work.
`async def` + `await` lets Python suspend one persona's call while it's
waiting and work on another persona's call in the meantime, all on a
single thread. That's what makes 15 personas take roughly as long as
ONE persona call (bounded by the concurrency limit), instead of 15x as
long as running them one-by-one in a for loop.
"""
from __future__ import annotations

import json
import re

from pydantic import ValidationError

from app.llm.base import LLMProvider, LLMError
from app.models import ContentProfile, Persona, PersonaReaction
from app.prompts.persona import build_persona_prompts


class PersonaEvaluationError(RuntimeError):
    """Raised when a persona's LLM response can't be turned into a valid reaction."""


def _extract_json(text: str) -> dict:
    """Best-effort extraction of a JSON object from an LLM response.

    Local models (via Ollama) sometimes wrap JSON in markdown fences or
    add stray text even when asked not to. We try a direct parse first,
    then fall back to grabbing the first {...} block.
    """
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group(0))

    raise PersonaEvaluationError(f"Could not parse JSON from LLM response: {text[:300]}")


class PersonaAgent:
    """One simulated user. Holds a Persona profile + shared LLM client."""

    def __init__(self, persona: Persona, llm: LLMProvider):
        self.persona = persona
        self.llm = llm

    async def evaluate(self, content_profile: ContentProfile) -> PersonaReaction:
        """Ask the LLM to roleplay this persona reacting to the content.

        Raises PersonaEvaluationError on malformed/invalid responses so
        the caller (simulation engine) can catch it per-persona without
        crashing the whole batch.
        """
        system_prompt, user_prompt = build_persona_prompts(self.persona, content_profile)

        try:
            raw = await self.llm.complete_json(system_prompt, user_prompt, temperature=0.4)
        except LLMError as e:
            raise PersonaEvaluationError(
                f"[{self.persona.name}] LLM call failed: {e}"
            ) from e

        try:
            data = _extract_json(raw)
            # Make sure persona_id is always correct even if the model typos it.
            data["persona_id"] = self.persona.id
            reaction = PersonaReaction.model_validate(data)
        except (json.JSONDecodeError, ValidationError, PersonaEvaluationError) as e:
            raise PersonaEvaluationError(
                f"[{self.persona.name}] Invalid/malformed response: {e}"
            ) from e

        return reaction
