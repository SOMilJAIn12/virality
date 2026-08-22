"""
Offline tests for the Phase 3 Groq reliability fixes:

- TokenPerMinuteLimiter (app/llm/rate_limit.py): proactive TPM throttling.
- _groq_retry_wait (app/llm/groq.py): 429-aware backoff.
- LLMError / LLMRateLimitError / LLMPermanentError (app/llm/base.py) and
  the retry policy that treats them differently.

None of these tests make real network calls to Groq or Ollama.
"""
from __future__ import annotations

import asyncio

import pytest
from tenacity import retry, retry_if_exception_type, retry_if_not_exception_type, stop_after_attempt

from app.llm.base import LLMError, LLMPermanentError, LLMRateLimitError
from app.llm.groq import _groq_retry_wait
from app.llm.rate_limit import TokenPerMinuteLimiter, estimate_tokens


# ---------------------------------------------------------------------------
# TokenPerMinuteLimiter
# ---------------------------------------------------------------------------

def test_estimate_tokens_scales_with_length():
    short = estimate_tokens("hello")
    long = estimate_tokens("hello " * 200)
    assert short >= 1
    assert long > short


def test_prune_removes_entries_older_than_60s():
    limiter = TokenPerMinuteLimiter(tpm_limit=1000)
    now = 1000.0
    limiter._usage = [(now - 70, 500), (now - 10, 200)]
    used = limiter._prune(now)
    assert used == 200
    assert limiter._usage == [(now - 10, 200)]


@pytest.mark.asyncio
async def test_acquire_is_immediate_when_under_budget():
    limiter = TokenPerMinuteLimiter(tpm_limit=8000)
    # Comfortably under the (de-rated) budget -> should return almost
    # instantly, not sleep.
    await asyncio.wait_for(limiter.acquire(500), timeout=1.0)
    await asyncio.wait_for(limiter.acquire(500), timeout=1.0)


@pytest.mark.asyncio
async def test_acquire_reserves_budget_and_blocks_when_exhausted():
    # Tiny budget so we can prove blocking behavior without a real 60s wait:
    # use a very small tpm_limit and confirm a second large request has to
    # wait (we don't wait for the real 60s -- just confirm it does NOT
    # return immediately).
    limiter = TokenPerMinuteLimiter(tpm_limit=100, safety_margin=1.0)
    await limiter.acquire(90)  # consumes almost the whole budget
    with pytest.raises(asyncio.TimeoutError):
        # Not enough budget left; acquiring more should have to wait for
        # the window to roll over (~60s), which we don't wait around for.
        await asyncio.wait_for(limiter.acquire(50), timeout=0.3)


# ---------------------------------------------------------------------------
# 429-aware backoff
# ---------------------------------------------------------------------------

class _FakeOutcome:
    def __init__(self, exc):
        self._exc = exc

    def exception(self):
        return self._exc


class _FakeRetryState:
    def __init__(self, exc, attempt_number):
        self.outcome = _FakeOutcome(exc)
        self.attempt_number = attempt_number


def test_wait_honors_retry_after_header():
    exc = LLMRateLimitError("429", retry_after=5.0)
    wait = _groq_retry_wait(_FakeRetryState(exc, attempt_number=1))
    # retry_after + jitter(0.5-2.0)
    assert 5.5 <= wait <= 7.0


def test_wait_backs_off_longer_without_retry_after_header():
    exc = LLMRateLimitError("429", retry_after=None)
    wait_attempt1 = _groq_retry_wait(_FakeRetryState(exc, attempt_number=1))
    wait_attempt3 = _groq_retry_wait(_FakeRetryState(exc, attempt_number=3))
    assert wait_attempt1 >= 4.0
    assert wait_attempt3 > wait_attempt1  # grows with attempt number
    assert wait_attempt3 <= 31.0  # capped at 30s + jitter


def test_wait_is_short_for_generic_transient_errors():
    exc = LLMError("connection reset")
    wait = _groq_retry_wait(_FakeRetryState(exc, attempt_number=3))
    assert wait <= 8.0


# ---------------------------------------------------------------------------
# Permanent vs. transient retry policy
# ---------------------------------------------------------------------------

def _retry_policy():
    return retry_if_exception_type(LLMError) & retry_if_not_exception_type(LLMPermanentError)


@pytest.mark.asyncio
async def test_transient_errors_are_retried_until_success():
    attempts = {"n": 0}

    @retry(reraise=True, stop=stop_after_attempt(5), wait=lambda rs: 0, retry=_retry_policy())
    async def flaky():
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise LLMRateLimitError("429", retry_after=0.0)
        return "ok"

    result = await flaky()
    assert result == "ok"
    assert attempts["n"] == 3


@pytest.mark.asyncio
async def test_permanent_errors_are_not_retried():
    attempts = {"n": 0}

    @retry(reraise=True, stop=stop_after_attempt(5), wait=lambda rs: 0, retry=_retry_policy())
    async def always_bad_request():
        attempts["n"] += 1
        raise LLMPermanentError("400 bad request / json_validate_failed")

    with pytest.raises(LLMPermanentError):
        await always_bad_request()
    # Must fail on the FIRST attempt -- retrying a permanent error wastes
    # TPM budget on a request that can't succeed.
    assert attempts["n"] == 1


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
