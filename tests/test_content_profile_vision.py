"""
Offline tests for the Phase 4 visual-understanding feature:

- app/simulation/content.py: build_content_profile() attaching sampled
  frames (from VideoInfo.frame_paths) to a multimodal LLM call, with a
  transcript-only fallback whenever visual analysis isn't possible.
- app/llm/base.py: the default (non-abstract) complete_json_multimodal
  raising for providers that don't implement it.
- app/llm/groq.py: GroqProvider.complete_json_multimodal building an
  image-bearing request against a separate vision model, and refusing
  cleanly when no vision model is configured.

None of these tests make real network calls to Groq or Ollama.
"""
from __future__ import annotations

import json
import os
import tempfile

import pytest

from app.config import Settings
from app.llm.base import LLMError, LLMPermanentError, LLMProvider
from app.llm.groq import GroqProvider
from app.simulation.content import build_content_profile
from app.video.processor import VideoInfo

VALID_PROFILE = {
    "title": "Guy tries a spicy noodle challenge",
    "summary": "A short clip of someone reacting to extremely spicy noodles.",
    "hook_strength": 0.7,
    "curiosity_surprise_strength": 0.4,
    "educational_value": 0.1,
    "entertainment_value": 0.8,
    "emotional_intensity": 0.6,
    "shareability": 0.5,
    "call_to_action": None,
    "target_audience": "young adults who enjoy food/reaction content",
}


def _settings(**overrides) -> Settings:
    base = dict(
        model_provider="groq",
        groq_api_key="fake-key",
        groq_model="openai/gpt-oss-120b",
        enable_visual_analysis=True,
    )
    base.update(overrides)
    return Settings(**base)


def _make_video(tmp_frames: list[str] | None = None, transcript: str | None = "hi there") -> VideoInfo:
    return VideoInfo(
        path="/videos/sample.mp4",
        duration_seconds=12.3,
        frame_paths=tmp_frames or [],
        transcript=transcript,
    )


# ---------------------------------------------------------------------------
# Fake LLM providers (no network calls)
# ---------------------------------------------------------------------------

class FakeVisionCapableLLM(LLMProvider):
    """Supports both text-only and multimodal calls."""

    def __init__(self, vision_should_fail: bool = False):
        self.vision_should_fail = vision_should_fail
        self.text_calls: list[tuple[str, str]] = []
        self.multimodal_calls: list[tuple[str, str, list[str]]] = []

    async def complete_json(self, system_prompt: str, user_prompt: str, *, temperature: float = 0.7) -> str:
        self.text_calls.append((system_prompt, user_prompt))
        return json.dumps(VALID_PROFILE)

    async def complete_text(self, system_prompt: str, user_prompt: str, *, temperature: float = 0.7) -> str:
        return "some prose"

    async def complete_json_multimodal(
        self, system_prompt: str, user_prompt: str, *, image_paths: list[str], temperature: float = 0.7
    ) -> str:
        self.multimodal_calls.append((system_prompt, user_prompt, image_paths))
        if self.vision_should_fail:
            raise LLMError("simulated vision model failure")
        return json.dumps(VALID_PROFILE)


class FakeTextOnlyLLM(LLMProvider):
    """A provider that does NOT override complete_json_multimodal, i.e.
    inherits the base class's default (raising) implementation — this
    simulates Ollama/any provider without vision support."""

    def __init__(self):
        self.text_calls: list[tuple[str, str]] = []

    async def complete_json(self, system_prompt: str, user_prompt: str, *, temperature: float = 0.7) -> str:
        self.text_calls.append((system_prompt, user_prompt))
        return json.dumps(VALID_PROFILE)

    async def complete_text(self, system_prompt: str, user_prompt: str, *, temperature: float = 0.7) -> str:
        return "some prose"


# ---------------------------------------------------------------------------
# 1. transcript-only generation still works (no frames at all)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_content_profile_transcript_only_no_frames(capsys):
    llm = FakeVisionCapableLLM()
    video = _make_video(tmp_frames=[])

    profile = await build_content_profile(video, llm, _settings())

    assert profile.title == VALID_PROFILE["title"]
    assert len(llm.multimodal_calls) == 0
    assert len(llm.text_calls) == 1
    captured = capsys.readouterr()
    assert "Visual analysis: fallback to transcript" in captured.out


# ---------------------------------------------------------------------------
# 2. ContentProfile can receive frame paths and uses the multimodal path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_content_profile_uses_frames_when_available(capsys):
    llm = FakeVisionCapableLLM()
    with tempfile.TemporaryDirectory() as tmp_dir:
        frame_paths = []
        for i in range(3):
            p = os.path.join(tmp_dir, f"frame_{i}.jpg")
            with open(p, "wb") as f:
                f.write(b"\xff\xd8\xff\xe0fake-jpeg-bytes")
            frame_paths.append(p)

        video = _make_video(tmp_frames=frame_paths)
        profile = await build_content_profile(video, llm, _settings())

    assert profile.title == VALID_PROFILE["title"]
    assert len(llm.multimodal_calls) == 1
    assert len(llm.text_calls) == 0
    _, _, used_paths = llm.multimodal_calls[0]
    assert used_paths == frame_paths
    captured = capsys.readouterr()
    assert "Visual analysis: yes" in captured.out


# ---------------------------------------------------------------------------
# 3. Missing frames gracefully falls back (even with vision enabled)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_missing_frames_falls_back_to_transcript(capsys):
    llm = FakeVisionCapableLLM()
    video = _make_video(tmp_frames=[])  # no frames extracted

    profile = await build_content_profile(video, llm, _settings(enable_visual_analysis=True))

    assert profile is not None
    assert len(llm.multimodal_calls) == 0
    assert len(llm.text_calls) == 1
    captured = capsys.readouterr()
    assert "fallback to transcript" in captured.out


# ---------------------------------------------------------------------------
# 4. Vision failure gracefully falls back
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_vision_call_failure_falls_back_to_transcript(capsys):
    llm = FakeVisionCapableLLM(vision_should_fail=True)
    with tempfile.TemporaryDirectory() as tmp_dir:
        p = os.path.join(tmp_dir, "frame_0.jpg")
        with open(p, "wb") as f:
            f.write(b"fake")

        video = _make_video(tmp_frames=[p])
        profile = await build_content_profile(video, llm, _settings())

    assert profile is not None
    assert len(llm.multimodal_calls) == 1  # attempted
    assert len(llm.text_calls) == 1  # then fell back
    captured = capsys.readouterr()
    assert "Visual analysis: fallback to transcript" in captured.out


@pytest.mark.asyncio
async def test_provider_without_vision_support_falls_back(capsys):
    """A provider that never implements complete_json_multimodal (e.g.
    Ollama) should hit the base class's default, which raises — and the
    caller should treat that exactly like any other vision failure."""
    llm = FakeTextOnlyLLM()
    with tempfile.TemporaryDirectory() as tmp_dir:
        p = os.path.join(tmp_dir, "frame_0.jpg")
        with open(p, "wb") as f:
            f.write(b"fake")

        video = _make_video(tmp_frames=[p])
        profile = await build_content_profile(video, llm, _settings())

    assert profile is not None
    assert len(llm.text_calls) == 1
    captured = capsys.readouterr()
    assert "Visual analysis: fallback to transcript" in captured.out


@pytest.mark.asyncio
async def test_visual_analysis_disabled_skips_multimodal_entirely():
    llm = FakeVisionCapableLLM()
    with tempfile.TemporaryDirectory() as tmp_dir:
        p = os.path.join(tmp_dir, "frame_0.jpg")
        with open(p, "wb") as f:
            f.write(b"fake")

        video = _make_video(tmp_frames=[p])
        await build_content_profile(video, llm, _settings(enable_visual_analysis=False))

    assert len(llm.multimodal_calls) == 0
    assert len(llm.text_calls) == 1


# ---------------------------------------------------------------------------
# Base class default behavior
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_base_provider_default_multimodal_raises():
    llm = FakeTextOnlyLLM()
    with pytest.raises(LLMError):
        await llm.complete_json_multimodal("sys", "user", image_paths=["/tmp/does_not_exist.jpg"])


# ---------------------------------------------------------------------------
# GroqProvider.complete_json_multimodal
# ---------------------------------------------------------------------------

def test_groq_provider_without_vision_model_raises_permanent_error():
    provider = GroqProvider(api_key="fake", model="openai/gpt-oss-120b", vision_model="")
    with pytest.raises(LLMPermanentError):
        import asyncio

        asyncio.run(
            provider.complete_json_multimodal("sys", "user", image_paths=["/tmp/does_not_exist.jpg"])
        )


@pytest.mark.asyncio
async def test_groq_provider_multimodal_missing_frame_file_raises():
    provider = GroqProvider(
        api_key="fake",
        model="openai/gpt-oss-120b",
        vision_model="meta-llama/llama-4-scout-17b-16e-instruct",
    )
    with pytest.raises(LLMError):
        await provider.complete_json_multimodal(
            "sys", "user", image_paths=["/tmp/definitely_missing_frame.jpg"]
        )


@pytest.mark.asyncio
async def test_groq_provider_multimodal_sends_vision_model_not_text_model(monkeypatch):
    provider = GroqProvider(
        api_key="fake",
        model="openai/gpt-oss-120b",
        vision_model="meta-llama/llama-4-scout-17b-16e-instruct",
    )

    captured_kwargs = {}

    async def fake_complete_raw(self, *, model, messages, temperature, json_mode, est_tokens):
        captured_kwargs["model"] = model
        captured_kwargs["messages"] = messages
        captured_kwargs["json_mode"] = json_mode
        return json.dumps(VALID_PROFILE)

    monkeypatch.setattr(GroqProvider, "_complete_raw", fake_complete_raw)

    with tempfile.TemporaryDirectory() as tmp_dir:
        p = os.path.join(tmp_dir, "frame_0.jpg")
        with open(p, "wb") as f:
            f.write(b"\xff\xd8\xff\xe0fake-jpeg-bytes")

        raw = await provider.complete_json_multimodal("sys", "user prompt", image_paths=[p])

    assert json.loads(raw) == VALID_PROFILE
    # Multimodal calls must use the SEPARATE vision model, never the
    # text-only persona/content model.
    assert captured_kwargs["model"] == "meta-llama/llama-4-scout-17b-16e-instruct"
    assert captured_kwargs["json_mode"] is True
    user_message = captured_kwargs["messages"][1]
    assert user_message["role"] == "user"
    # Content must be a list of blocks (text + image_url), not a plain string.
    assert isinstance(user_message["content"], list)
    types = [block["type"] for block in user_message["content"]]
    assert types == ["text", "image_url"]
    assert user_message["content"][1]["image_url"]["url"].startswith("data:image/jpeg;base64,")


@pytest.mark.asyncio
async def test_groq_provider_multimodal_caps_at_five_images(monkeypatch):
    provider = GroqProvider(
        api_key="fake",
        model="openai/gpt-oss-120b",
        vision_model="meta-llama/llama-4-scout-17b-16e-instruct",
    )

    captured_kwargs = {}

    async def fake_complete_raw(self, *, model, messages, temperature, json_mode, est_tokens):
        captured_kwargs["messages"] = messages
        return json.dumps(VALID_PROFILE)

    monkeypatch.setattr(GroqProvider, "_complete_raw", fake_complete_raw)

    with tempfile.TemporaryDirectory() as tmp_dir:
        paths = []
        for i in range(8):
            p = os.path.join(tmp_dir, f"frame_{i}.jpg")
            with open(p, "wb") as f:
                f.write(b"\xff\xd8\xff\xe0fake")
            paths.append(p)

        await provider.complete_json_multimodal("sys", "user", image_paths=paths)

    content_blocks = captured_kwargs["messages"][1]["content"]
    image_blocks = [b for b in content_blocks if b["type"] == "image_url"]
    assert len(image_blocks) == 5  # capped, not 8


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
