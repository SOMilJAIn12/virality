"""
Minimal in-process tokens-per-minute (TPM) throttle.

Why this exists
----------------
`asyncio.Semaphore(MAX_CONCURRENT_AGENTS)` (see app/simulation/engine.py)
limits how many requests are *in flight* at once, but says nothing about
*tokens*. With MAX_CONCURRENT_AGENTS=10 and ~700-1000 tokens per persona
call, firing 10 requests at once can burst past an 8000 TPM limit in a
single instant, which is exactly what produced the 429s in Phase 1/3.

What this is (and isn't)
-------------------------
This is a small, single-process, in-memory sliding-window limiter — NOT
a distributed/multi-process rate limiter (Redis, etc). That's the right
scope for this MVP: one `GroqProvider` instance is created once per CLI
run and shared by every persona call (see app/llm/factory.py), so a
single in-process limiter naturally governs the whole run.

It intentionally uses a *rough* token estimate (chars / 4) rather than a
real tokenizer. Precision doesn't matter here -- the goal is just to
stop the process from bursting far past the provider's budget, not to
account for every token exactly.
"""
from __future__ import annotations

import asyncio
import time

# ~4 characters per token is a standard rough estimate for English text
# and system/JSON-schema prompts; good enough for throttling purposes.
_CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    """Rough token estimate for throttling. Not exact -- just needs to be
    in the right ballpark so we don't burst past the TPM budget."""
    return max(1, len(text) // _CHARS_PER_TOKEN)


class TokenPerMinuteLimiter:
    """Blocks callers until enough token budget is free in a rolling
    60-second window.

    `safety_margin` de-rates the configured limit (default: use only 85%
    of it) to leave headroom for: (a) our token estimate being rough,
    and (b) other calls (content-profile analysis, the AI summary) that
    share the same provider/limit but aren't part of the persona batch.
    """

    def __init__(self, tpm_limit: int, safety_margin: float = 0.85):
        self.budget = max(1, int(tpm_limit * safety_margin))
        self._usage: list[tuple[float, int]] = []
        self._lock = asyncio.Lock()

    def _prune(self, now: float) -> int:
        cutoff = now - 60.0
        self._usage = [(t, n) for t, n in self._usage if t > cutoff]
        return sum(n for _, n in self._usage)

    async def acquire(self, tokens: int) -> tuple[float, int]:
        """Reserve `tokens` worth of budget, waiting if necessary.

        If a single request's estimate is larger than the entire budget
        (shouldn't normally happen for our prompts), it's let through
        immediately once the window is otherwise empty, rather than
        blocking forever.
        """
        while True:
            async with self._lock:
                now = time.monotonic()
                used = self._prune(now)
                if used + tokens <= self.budget or not self._usage:
                    reservation = (now, tokens)
                    self._usage.append(reservation)
                    return reservation
                # Not enough room right now -- wait until the oldest
                # reservation ages out of the 60s window, then recheck.
                oldest_time = self._usage[0][0]
                wait_for = max(0.1, 60.0 - (now - oldest_time))
            await asyncio.sleep(wait_for)

    async def release(self, reservation: tuple[float, int]) -> None:
        """Release a reservation for a request Groq rejected before processing.

        This is deliberately used only for HTTP 429 responses.  A network
        failure may still have reached Groq, so retaining that reservation is
        the conservative choice for the configured TPM budget.
        """
        async with self._lock:
            try:
                self._usage.remove(reservation)
            except ValueError:
                # The reservation has already aged out of the rolling window.
                pass
