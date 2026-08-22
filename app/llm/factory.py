"""
Provider factory.

This is the ONLY place in the app that decides which concrete provider
class to instantiate. Everything else just talks to the `LLMProvider`
interface. This is what lets us switch MODEL_PROVIDER=ollama <-> groq
in `.env` without touching persona/simulation code at all.

One provider instance is created and shared by every persona (see the
diagram in the prompt: one LLM client, many agents on top of it).
"""
from __future__ import annotations

from app.config import Settings
from app.llm.base import LLMProvider
from app.llm.ollama import OllamaProvider
from app.llm.groq import GroqProvider


def create_llm_provider(settings: Settings) -> LLMProvider:
    if settings.model_provider == "ollama":
        return OllamaProvider(model=settings.ollama_model, host=settings.ollama_host)
    if settings.model_provider == "groq":
        return GroqProvider(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            tpm_limit=settings.groq_tpm_limit,
            vision_model=settings.groq_vision_model,
        )
    raise ValueError(f"Unknown MODEL_PROVIDER: {settings.model_provider}")
