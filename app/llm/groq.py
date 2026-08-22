"""
Groq provider (optional, cloud-based, fast).

Uses the official `groq` Python SDK. The SDK itself is synchronous, so
we run each call in a background thread via `asyncio.to_thread` — this
still lets multiple persona calls happen "concurrently enough" without
blocking the event loop, without needing an async-native SDK.

Reliability under Groq's TPM limit (Phase 3)
---------------------------------------------
Two things work together to keep 15+ persona calls reliable under a
constrained tokens-per-minute (TPM) budget:

1. `TokenPerMinuteLimiter` (app/llm/rate_limit.py) — throttles calls
   BEFORE they're sent, based on a rough token estimate, so the process
   doesn't burst past the TPM budget in the first place. This is the
   primary fix; concurrency alone (the semaphore in engine.py) can't
   prevent bursts because it has no concept of tokens.
2. 429-aware retry — when a 429 slips through anyway, we parse Groq's
   `Retry-After` header and back off for exactly that long (plus
   jitter), instead of a short generic exponential backoff that's very
   likely to hit the same still-exhausted TPM window again.

Non-transient errors (400 bad request / schema rejection, 401 auth) are
raised as `LLMPermanentError` and are NOT retried — retrying a request
that was rejected for being malformed just burns more TPM budget on a
result that can't change.
"""
from __future__ import annotations

import asyncio
import base64
import os
import random

from groq import AuthenticationError, BadRequestError, Groq, RateLimitError
from tenacity import (
    retry,
    retry_if_exception_type,
    retry_if_not_exception_type,
    stop_after_attempt,
)

from app.llm.base import LLMError, LLMPermanentError, LLMProvider, LLMRateLimitError
from app.llm.rate_limit import TokenPerMinuteLimiter, estimate_tokens

# Rough allowance added to the input-token estimate to account for the
# model's output. Persona JSON is now explicitly instructed to keep
# comment_text/reasoning short (see app/prompts/persona.py), and content-
# profile/summary output is likewise compact structured JSON or a few
# sentences -- 300 is still a conservative pad (~2x the realistic output
# size) without reserving as much dead budget per call as the original
# flat 400 did.
_OUTPUT_TOKEN_ALLOWANCE = 300

# Floor for a single image's estimated token cost, so a tiny/degenerate
# image (or a test fixture) never estimates as ~0 tokens and slips past
# the proactive throttle.
_MIN_IMAGE_TOKEN_ESTIMATE = 200

# Groq's vision models currently cap requests at 5 images; enforce this
# locally so we fail fast with a clear error instead of a confusing 400.
_MAX_VISION_IMAGES = 5

# Groq defaults GPT-OSS to medium reasoning effort. Persona evaluation is a
# single, tightly constrained JSON classification task, so low effort avoids
# spending TPM on unnecessary hidden reasoning while preserving the same
# prompt, response format, and temperature. 
_GPT_OSS_MODELS = {"openai/gpt-oss-20b", "openai/gpt-oss-120b"}

_EXT_TO_MIME = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
    "gif": "image/gif",
}


def _groq_retry_wait(retry_state) -> float:
    """Backoff strategy tailored to *why* the call failed.

    - LLMRateLimitError WITH a Retry-After header: wait exactly that
      long (+ small random jitter so concurrent personas don't all wake
      up in the same instant and immediately re-collide on the limit).
    - LLMRateLimitError WITHOUT a header: Groq's TPM window is
      typically ~60s, so back off longer than a generic transient
      error would (capped at 30s) rather than retrying into the same
      exhausted window.
    - Any other transient LLMError: short exponential backoff (same
      shape as the original pre-Phase-3 behavior).
    """
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    attempt = retry_state.attempt_number

    if isinstance(exc, LLMRateLimitError):
        if exc.retry_after:
            return exc.retry_after + random.uniform(0.5, 2.0)
        return min(30.0, 4.0 * (2 ** (attempt - 1))) + random.uniform(0, 1.0)

    return min(8.0, float(2 ** (attempt - 1)))


class GroqProvider(LLMProvider):
    def __init__(
        self,
        api_key: str,
        model: str,
        tpm_limit: int = 8000,
        vision_model: str = "",
    ):
        if not api_key:
            raise LLMError("GROQ_API_KEY is empty. Set it in your .env file.")
        self.model = model
        # Optional: a separate, vision-capable Groq model used ONLY for the
        # content-profile step (see complete_json_multimodal below). Kept
        # distinct from `self.model` so persona calls stay on the cheaper
        # text model — we deliberately do NOT send images to every persona.
        self.vision_model = vision_model.strip() if vision_model else ""
        self._client = Groq(api_key=api_key)
        # One limiter per provider instance, shared by every call made
        # through it (content profile, every persona, the summary) —
        # see app/llm/factory.py, which creates exactly one provider per
        # run. This is what makes the TPM budget apply to the whole
        # simulation, not just one round or one call.
        self._limiter = TokenPerMinuteLimiter(tpm_limit=tpm_limit)

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=_groq_retry_wait,
        retry=retry_if_exception_type(LLMError) & retry_if_not_exception_type(LLMPermanentError),
    )
    async def _complete_raw(
        self,
        *,
        model: str,
        messages: list[dict],
        temperature: float,
        json_mode: bool,
        est_tokens: int,
    ) -> str:
        """Shared call path for every Groq chat-completion request (plain
        text, JSON-mode, or multimodal) — throttling, retry policy, and
        error mapping all live here exactly once."""
        # Throttle BEFORE sending, using a rough pre-call token estimate,
        # so we avoid 429s proactively instead of only reacting to them.
        reservation = await self._limiter.acquire(est_tokens + _OUTPUT_TOKEN_ALLOWANCE)

        def _call() -> str:
            kwargs = dict(model=model, messages=messages, temperature=temperature)
            if model in _GPT_OSS_MODELS:
                kwargs["reasoning_effort"] = "low"
            if json_mode:
                # Only constrain to JSON mode for callers that actually
                # parse the response as JSON (persona reactions, content
                # profile). Forcing this on a plain-text request (the AI
                # summary) is what caused `json_validate_failed` (400).
                kwargs["response_format"] = {"type": "json_object"}

            try:
                resp = self._client.chat.completions.create(**kwargs)
            except RateLimitError as e:
                retry_after: float | None = None
                try:
                    retry_after = float(e.response.headers.get("retry-after"))
                except (TypeError, ValueError, AttributeError):
                    retry_after = None
                raise LLMRateLimitError(
                    f"Groq rate limit (429): {e}", retry_after=retry_after
                ) from e
            except (BadRequestError, AuthenticationError) as e:
                # Non-transient: a malformed request or bad credentials
                # will fail again identically on retry.
                raise LLMPermanentError(
                    f"Groq request rejected ({getattr(e, 'status_code', '?')}): {e}"
                ) from e
            except Exception as e:  # groq SDK raises other exception types too
                # Everything else (network blips, 5xx, timeouts) is
                # treated as transient and retried by @retry above.
                raise LLMError(f"Groq request failed: {e}") from e

            content = resp.choices[0].message.content
            if not content:
                raise LLMError("Groq returned an empty response.")
            return content

        # Run the blocking SDK call in a worker thread so asyncio.gather()
        # across personas doesn't get stuck behind one blocking call.
        try:
            return await asyncio.to_thread(_call)
        except LLMRateLimitError:
            # Groq rejected this attempt, so it consumed no completion quota.
            # Removing the local reservation prevents a failed retry from
            # needlessly blocking every queued persona for another minute.
            await self._limiter.release(reservation)
            raise

    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.7,
    ) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        est_tokens = estimate_tokens(system_prompt) + estimate_tokens(user_prompt)
        return await self._complete_raw(
            model=self.model,
            messages=messages,
            temperature=temperature,
            json_mode=True,
            est_tokens=est_tokens,
        )

    async def complete_text(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.7,
    ) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        est_tokens = estimate_tokens(system_prompt) + estimate_tokens(user_prompt)
        return await self._complete_raw(
            model=self.model,
            messages=messages,
            temperature=temperature,
            json_mode=False,
            est_tokens=est_tokens,
        )

    async def complete_json_multimodal(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        image_paths: list[str],
        temperature: float = 0.7,
    ) -> str:
        """Content-profile-only multimodal call: text + up to
        `_MAX_VISION_IMAGES` local frame images, sent to `self.vision_model`
        (NOT `self.model` — persona calls never go through this method).

        Raises `LLMPermanentError`/`LLMError` (never crashes) if no vision
        model is configured, a frame can't be read, or the request fails —
        callers are expected to catch this and fall back to
        `complete_json` (transcript-only).
        """
        if not self.vision_model:
            raise LLMPermanentError(
                "No vision-capable Groq model configured. Set GROQ_VISION_MODEL "
                "in your .env (e.g. meta-llama/llama-4-scout-17b-16e-instruct) "
                "to enable image-grounded content profiles."
            )

        selected_paths = image_paths[:_MAX_VISION_IMAGES]
        content_blocks: list[dict] = [{"type": "text", "text": user_prompt}]
        image_token_estimate = 0
        for path in selected_paths:
            try:
                with open(path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("ascii")
            except OSError as e:
                raise LLMError(f"Could not read frame image '{path}': {e}") from e
            # Estimate this image's throttle cost from its ACTUAL encoded
            # size (same chars/4 heuristic as text), instead of a flat
            # per-image guess. A flat guess can't tell a small compressed
            # thumbnail from a large raw frame -- which is exactly what
            # let a real request silently reach "Requested 8133 / Limit
            # 8000" while our old estimate assumed only ~3600. Frames are
            # now pre-resized/compressed in app/video/processor.py, so
            # both the real request AND this estimate shrink together,
            # and this scales correctly for any image size going forward.
            image_token_estimate += max(_MIN_IMAGE_TOKEN_ESTIMATE, estimate_tokens(b64))
            ext = os.path.splitext(path)[1].lstrip(".").lower()
            mime = _EXT_TO_MIME.get(ext, "image/jpeg")
            content_blocks.append(
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}
            )

        if len(content_blocks) == 1:
            raise LLMError("No valid frame images were available for multimodal analysis.")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content_blocks},
        ]
        est_tokens = (
            estimate_tokens(system_prompt)
            + estimate_tokens(user_prompt)
            + image_token_estimate
        )
        return await self._complete_raw(
            model=self.vision_model,
            messages=messages,
            temperature=temperature,
            json_mode=True,
            est_tokens=est_tokens,
        )
