"""
Ollama provider.

Ollama exposes a local HTTP server (default http://localhost:11434).
We call its `/api/chat` endpoint with `format: "json"` so the model is
constrained to return valid JSON, then hand the raw text back up to
whoever asked for it (PersonaAgent, ContentProfile builder, etc).

Why httpx.AsyncClient instead of `requests`?
`requests` is synchronous and would block the whole event loop, which
defeats the purpose of running 10-15 personas concurrently. httpx gives
us a real `async def` HTTP call that plays nicely with asyncio.gather().
"""
from __future__ import annotations

import json

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.llm.base import LLMProvider, LLMError


class OllamaProvider(LLMProvider):
    def __init__(self, model: str, host: str = "http://localhost:11434", timeout: float = 120.0):
        self.model = model
        self.host = host.rstrip("/")
        self.timeout = timeout
        # One shared client reused across all persona calls (connection pooling).
        self._client = httpx.AsyncClient(timeout=timeout)

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type((httpx.HTTPError, LLMError)),
    )
    async def _complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float,
        json_mode: bool,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {"temperature": temperature},
        }
        if json_mode:
            payload["format"] = "json"
        try:
            resp = await self._client.post(f"{self.host}/api/chat", json=payload)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise LLMError(
                f"Ollama request failed ({e}). Is `ollama serve` running and is "
                f"model '{self.model}' pulled? Try: ollama pull {self.model}"
            ) from e

        data = resp.json()
        content = data.get("message", {}).get("content")
        if not content:
            raise LLMError(f"Ollama returned no content: {json.dumps(data)[:300]}")
        return content

    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.7,
    ) -> str:
        return await self._complete(
            system_prompt, user_prompt, temperature=temperature, json_mode=True
        )

    async def complete_text(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.7,
    ) -> str:
        # No `format: "json"` here — same rationale as GroqProvider:
        # forcing JSON-mode on a plain-text request (the AI summary) can
        # cause the model to fail to produce valid output for a request
        # that was never JSON in the first place.
        return await self._complete(
            system_prompt, user_prompt, temperature=temperature, json_mode=False
        )

    async def aclose(self) -> None:
        await self._client.aclose()
