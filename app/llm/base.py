"""
Abstract LLM provider interface.

Every concrete provider (Ollama, Groq, ...) implements two methods:

- `complete_json`: constrains the model to structured JSON output
  (persona reactions, content profile). Used wherever the caller parses
  and validates the response as JSON — this must stay strict.
- `complete_text`: plain free-form text output, no JSON-mode
  constraint. Used for prose the app doesn't parse as JSON (the AI
  summary). Forcing JSON-mode on a plain-text request is what caused
  Groq to reject the summary call with `json_validate_failed` (HTTP
  400) — the model can't simultaneously satisfy "write plain English"
  and "respond only with valid JSON".

Keeping the interface this thin means the rest of the app (persona
agents, content-profile builder, summary generator) never needs to know
which provider is active.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Common interface every LLM backend must implement."""

    @abstractmethod
    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.7,
    ) -> str:
        """Send a chat completion request constrained to JSON output and
        return the raw text response.

        The caller is responsible for parsing/validating the JSON — this
        keeps the provider layer dumb and swappable.
        """
        raise NotImplementedError

    @abstractmethod
    async def complete_text(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.7,
    ) -> str:
        """Send a chat completion request for free-form text (no JSON-mode
        constraint) and return the raw text response.

        Use this instead of `complete_json` whenever the caller wants
        prose, not something it will `json.loads()`.
        """
        raise NotImplementedError

    async def complete_json_multimodal(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        image_paths: list[str],
        temperature: float = 0.7,
    ) -> str:
        """Send a chat completion request that includes local images plus
        text, constrained to JSON output, and return the raw text response.

        This is intentionally NOT `@abstractmethod`: most providers/models
        in this app are text-only (persona calls stay text-only on
        purpose to control cost), so requiring every provider to
        implement image support would be wrong. Providers that can't do
        this simply inherit this default, which raises — callers (e.g.
        `build_content_profile`) are expected to catch that and fall
        back to a transcript-only `complete_json` call rather than
        crashing the simulation.
        """
        raise LLMError(
            f"{type(self).__name__} does not support multimodal (image) input. "
            "Configure a vision-capable model/provider for this step, or "
            "fall back to transcript-only analysis."
        )


class LLMError(RuntimeError):
    """Raised when a provider call fails after retries."""


class LLMRateLimitError(LLMError):
    """Raised specifically for HTTP 429 rate-limit responses.

    Carries a server-provided `retry_after` hint (seconds), when the
    provider supplies one, so retry logic can back off precisely instead
    of guessing.
    """

    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class LLMPermanentError(LLMError):
    """Raised for non-transient failures (bad request, invalid schema,
    auth errors) that will not succeed if simply retried. Retry logic
    should NOT retry these — retrying a malformed/rejected request just
    burns TPM budget for a result that can't change.
    """
