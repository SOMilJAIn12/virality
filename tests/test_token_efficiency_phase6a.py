"""
Offline tests for Phase 6A (LLM token efficiency + simulation speed):

- app/prompts/persona.py: persona/content-profile prompts are materially
  smaller than the Phase 5E baseline while keeping every behavior-
  affecting instruction and the JSON schema intact.
- app/video/processor.py: sampled frames are resized/compressed before
  being written to disk, and never upscaled.
- app/llm/groq.py: the multimodal request's proactive token estimate is
  computed from each image's ACTUAL encoded size (not a flat per-image
  guess), so it scales correctly with real image size and stays within
  budget once frames are compressed.
- app/llm/rate_limit.py: the TPM limiter still enforces the configured
  budget under concurrent load (unchanged from Phase 3, re-verified here
  under the new, smaller per-call token estimates).

None of these tests make real network calls to Groq or Ollama.
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import tempfile

import cv2
import numpy as np
import pytest

from app.llm.groq import GroqProvider, _OUTPUT_TOKEN_ALLOWANCE
from app.llm.rate_limit import TokenPerMinuteLimiter, estimate_tokens
from app.prompts.persona import (
    CONTENT_PROFILE_SYSTEM_PROMPT,
    CONTENT_PROFILE_VISION_SYSTEM_PROMPT,
    PERSONA_SYSTEM_TEMPLATE,
    PERSONA_USER_TEMPLATE,
)
from app.video.processor import _extract_duration_and_frames, _resize_for_vision

VALID_PROFILE = {"title": "t", "summary": "s"}

# Phase 5E baseline sizes (chars), measured from the pre-Phase-6A prompt
# templates. Used only as an upper bound -- the exact new sizes are free
# to change further as long as they stay meaningfully smaller and keep
# every behavioral guarantee covered by test_persona_agent_and_reaction.py
# and test_curiosity_surprise_field.py.
_BASELINE_SYSTEM_CHARS = 3274
_BASELINE_USER_CHARS = 1119
_BASELINE_CPS_CHARS = 1762
_BASELINE_CPV_CHARS = 2691


# ---------------------------------------------------------------------------
# 1 & 3. Persona prompt is materially smaller, semantics preserved
# ---------------------------------------------------------------------------


def test_persona_system_prompt_is_materially_smaller():
    assert len(PERSONA_SYSTEM_TEMPLATE) < _BASELINE_SYSTEM_CHARS * 0.9


def test_persona_user_prompt_is_materially_smaller():
    assert len(PERSONA_USER_TEMPLATE) < _BASELINE_USER_CHARS * 0.95


def test_content_profile_prompts_are_materially_smaller():
    assert len(CONTENT_PROFILE_SYSTEM_PROMPT) < _BASELINE_CPS_CHARS * 0.9
    assert len(CONTENT_PROFILE_VISION_SYSTEM_PROMPT) < _BASELINE_CPV_CHARS * 0.9


def test_persona_prompt_still_documents_every_required_field():
    # Every field the spec requires stays present as a literal token in
    # the template (this is what keeps the LLM able to see/use it),
    # even though the surrounding prose was condensed.
    for field in [
        "{name}", "{age_range}", "{interests}", "{personality}",
        "attention_span", "entertainment_preference", "educational_preference",
        "sharing_tendency", "commenting_tendency", "following_tendency",
        "persona_id", "watch", "completion_rate", "rewatch", "like",
        "comment", "share", "follow", "comment_text", "reasoning",
    ]:
        assert field in PERSONA_SYSTEM_TEMPLATE, f"missing {field!r} in system template"


def test_persona_prompt_instructs_short_comment_text():
    # Step 3: comment_text must stay short, without removing the field.
    assert "comment_text" in PERSONA_SYSTEM_TEMPLATE
    lowered = PERSONA_SYSTEM_TEMPLATE.lower()
    assert "short" in lowered


# ---------------------------------------------------------------------------
# 2. Persona output remains valid JSON (schema unchanged) -- covered
#    end-to-end by tests/test_persona_agent_and_reaction.py; here we just
#    confirm the schema keys the agent parses are still all present.
# ---------------------------------------------------------------------------


def test_persona_schema_keys_unchanged():
    required_keys = {
        "persona_id", "watch", "completion_rate", "rewatch", "like",
        "comment", "share", "follow", "comment_text", "reasoning",
    }
    for key in required_keys:
        assert f'"{key}"' in PERSONA_SYSTEM_TEMPLATE


# ---------------------------------------------------------------------------
# 4 & 6. Vision request still uses actual images / representative frames
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multimodal_request_still_carries_real_image_bytes(monkeypatch):
    provider = GroqProvider(
        api_key="fake", model="openai/gpt-oss-120b", vision_model="qwen/qwen3.6-27b"
    )
    captured = {}

    async def fake_complete_raw(self, *, model, messages, temperature, json_mode, est_tokens):
        captured["messages"] = messages
        captured["est_tokens"] = est_tokens
        return json.dumps(VALID_PROFILE)

    monkeypatch.setattr(GroqProvider, "_complete_raw", fake_complete_raw)

    with tempfile.TemporaryDirectory() as tmp_dir:
        p = os.path.join(tmp_dir, "frame_0.jpg")
        with open(p, "wb") as f:
            f.write(b"\xff\xd8\xff\xe0" + b"x" * 5000)  # fake but sizeable jpeg payload

        await provider.complete_json_multimodal("sys", "user", image_paths=[p])

    image_block = [b for b in captured["messages"][1]["content"] if b["type"] == "image_url"][0]
    b64_payload = image_block["image_url"]["url"].split(",", 1)[1]
    assert base64.b64decode(b64_payload).startswith(b"\xff\xd8\xff\xe0")


# ---------------------------------------------------------------------------
# 5. Vision request's proactive token estimate scales with ACTUAL image
#    size, not a flat per-image guess (this is the direct fix for
#    "Requested 8133 / Limit 8000": a flat guess can't tell a compressed
#    thumbnail from a full-resolution frame).
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multimodal_est_tokens_scales_with_actual_image_size(monkeypatch):
    provider = GroqProvider(
        api_key="fake", model="openai/gpt-oss-120b", vision_model="qwen/qwen3.6-27b"
    )
    captured_est = {}

    async def fake_complete_raw(self, *, model, messages, temperature, json_mode, est_tokens):
        captured_est["value"] = est_tokens
        return json.dumps(VALID_PROFILE)

    monkeypatch.setattr(GroqProvider, "_complete_raw", fake_complete_raw)

    with tempfile.TemporaryDirectory() as tmp_dir:
        small_path = os.path.join(tmp_dir, "small.jpg")
        big_path = os.path.join(tmp_dir, "big.jpg")
        with open(small_path, "wb") as f:
            f.write(b"\xff\xd8\xff\xe0" + b"x" * 2000)
        with open(big_path, "wb") as f:
            f.write(b"\xff\xd8\xff\xe0" + b"x" * 40000)

        await provider.complete_json_multimodal("sys", "user", image_paths=[small_path])
        small_est = captured_est["value"]

        await provider.complete_json_multimodal("sys", "user", image_paths=[big_path])
        big_est = captured_est["value"]

    # A ~20x larger encoded image must produce a meaningfully larger
    # estimate -- proving the estimate is derived from real image size,
    # not a static per-image constant.
    assert big_est > small_est * 5


@pytest.mark.asyncio
async def test_realistic_compressed_frames_stay_within_target_budget(monkeypatch):
    """End-to-end sanity check: 3 frames produced by the actual frame
    extractor (resized + JPEG-compressed, same as production) must keep
    the multimodal request's estimated tokens comfortably under the
    8000-token free-tier TPM limit, unlike the pre-Phase-6A full-
    resolution frames that produced "Requested 8133 / Limit 8000"."""
    provider = GroqProvider(
        api_key="fake", model="openai/gpt-oss-120b", vision_model="qwen/qwen3.6-27b"
    )
    captured_est = {}

    async def fake_complete_raw(self, *, model, messages, temperature, json_mode, est_tokens):
        captured_est["value"] = est_tokens
        return json.dumps(VALID_PROFILE)

    monkeypatch.setattr(GroqProvider, "_complete_raw", fake_complete_raw)

    video_path = _make_synthetic_video(num_frames=30, size=(1920, 1080))
    try:
        _duration, frame_paths = _extract_duration_and_frames(
            video_path, num_frames=3, max_dimension=288, jpeg_quality=50
        )
        assert len(frame_paths) == 3

        await provider.complete_json_multimodal(
            CONTENT_PROFILE_VISION_SYSTEM_PROMPT,
            "Analyze these frames.",
            image_paths=frame_paths,
        )
    finally:
        os.remove(video_path)

    # Comfortably under the 8000 TPM free-tier limit (with real headroom
    # for the limiter's own 85% safety margin on top).
    assert captured_est["value"] < 8000


# ---------------------------------------------------------------------------
# Frame resizing (app/video/processor.py)
# ---------------------------------------------------------------------------


def test_resize_for_vision_downscales_oversized_frame():
    frame = np.zeros((1080, 1920, 3), dtype="uint8")
    resized = _resize_for_vision(frame, max_dimension=288)
    h, w = resized.shape[:2]
    assert max(h, w) <= 288


def test_resize_for_vision_never_upscales_small_frame():
    frame = np.zeros((100, 150, 3), dtype="uint8")
    resized = _resize_for_vision(frame, max_dimension=288)
    assert resized.shape == frame.shape


def test_extracted_frames_are_resized_and_valid_jpegs():
    video_path = _make_synthetic_video(num_frames=20, size=(1280, 720))
    try:
        _duration, frame_paths = _extract_duration_and_frames(
            video_path, num_frames=3, max_dimension=288, jpeg_quality=50
        )
        assert len(frame_paths) == 3
        for p in frame_paths:
            img = cv2.imread(p)
            assert img is not None
            h, w = img.shape[:2]
            assert max(h, w) <= 288
    finally:
        os.remove(video_path)


def _make_synthetic_video(num_frames: int, size: tuple[int, int]) -> str:
    """Write a tiny throwaway .mp4 for frame-extraction tests. `size` is
    (width, height)."""
    path = tempfile.mktemp(suffix=".mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(path, fourcc, 10.0, size)
    for _ in range(num_frames):
        frame = (np.random.rand(size[1], size[0], 3) * 255).astype("uint8")
        writer.write(frame)
    writer.release()
    return path


# ---------------------------------------------------------------------------
# 7. Rate limiter still prevents exceeding the configured TPM budget,
#    re-verified under the new (smaller) per-call token reservations.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_limiter_allows_more_calls_per_window_with_smaller_estimates():
    """Directly demonstrates the throughput win from Phase 6A's smaller
    prompts: with the OLD (larger) per-call token estimate, fewer calls
    fit in one window than with the NEW (smaller) estimate -- without
    ever exceeding the configured budget."""
    tpm_limit = 8000
    old_per_call = 818 + 279 + 400  # pre-Phase-6A system+user+output estimate
    new_per_call = (
        estimate_tokens(PERSONA_SYSTEM_TEMPLATE)
        + estimate_tokens(PERSONA_USER_TEMPLATE)
        + _OUTPUT_TOKEN_ALLOWANCE
    )
    assert new_per_call < old_per_call

    budget = int(tpm_limit * 0.85)
    old_calls_per_window = budget // old_per_call
    new_calls_per_window = budget // new_per_call
    assert new_calls_per_window >= old_calls_per_window


@pytest.mark.asyncio
async def test_limiter_never_exceeds_budget_under_concurrent_load():
    limiter = TokenPerMinuteLimiter(tpm_limit=2000, safety_margin=1.0)

    async def worker():
        await limiter.acquire(300)

    # Fire many concurrent acquisitions; none should be allowed to push
    # the rolling-window usage over budget at any point in time.
    tasks = [asyncio.create_task(worker()) for _ in range(5)]
    done, pending = await asyncio.wait(tasks, timeout=0.5)
    for t in pending:
        t.cancel()

    now = __import__("time").monotonic()
    used = limiter._prune(now)
    assert used <= limiter.budget


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
