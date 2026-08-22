"""
Builds a ContentProfile from raw VideoInfo using a single LLM call.

This is the "Video -> Content Profile" step from the architecture
diagram. It runs ONCE per video, not once per persona — personas only
ever see this compact structured summary, which keeps the pipeline
cheap even with 15+ personas per round.

Phase 4 (visual understanding)
-------------------------------
This step can optionally be made visually grounded: instead of only
telling the LLM "there are N sampled frames" (a bare count), we attach
the actual sampled frame images (already extracted by
app.video.processor into VideoInfo.frame_paths — we do NOT re-extract a
second set of frames) via `LLMProvider.complete_json_multimodal`.

This is deliberately scoped to ContentProfile generation only. Persona
calls (app/personas/agent.py) remain text-only, unchanged — sending
images to every persona would multiply image/token cost by 15+ calls
per round for very little marginal benefit, since personas only ever
reason over the ContentProfile, not the raw video.

Robustness: visual analysis is best-effort. If frames aren't available,
visual analysis is disabled, or the vision call fails for any reason
(no vision model configured, unsupported provider, network/API error),
we transparently fall back to the original transcript-only call rather
than crashing the simulation.
"""
from __future__ import annotations

import json
import logging

from app.config import Settings
from app.llm.base import LLMProvider
from app.models import ContentProfile
from app.prompts.persona import (
    CONTENT_PROFILE_SYSTEM_PROMPT,
    CONTENT_PROFILE_VISION_SYSTEM_PROMPT,
)
from app.video.processor import VideoInfo

logger = logging.getLogger(__name__)

# Groq vision models currently cap requests at 5 images; keep this in sync
# with app/llm/groq.py's _MAX_VISION_IMAGES. Capped here too so we never
# hand a provider more frames than it can accept, regardless of provider.
_MAX_VISION_FRAMES = 5

_FALLBACK_PROFILE_DATA = {
    "title": "Unknown short-form video",
    "summary": "Automated analysis failed to parse; using neutral defaults.",
    "hook_strength": 0.5,
    "curiosity_surprise_strength": 0.5,
    "educational_value": 0.5,
    "entertainment_value": 0.5,
    "emotional_intensity": 0.5,
    "shareability": 0.5,
    "call_to_action": None,
    "target_audience": "general audience",
}


def _build_user_prompt(video: VideoInfo) -> str:
    transcript_section = (
        f"Transcript (best-effort, may be partial):\n{video.transcript}"
        if video.transcript
        else "Transcript: not available (analyze based on duration/filename only)."
    )
    filename = video.path.rsplit("/", 1)[-1]
    return (
        f"Filename: {filename}\n"
        f"Duration: {video.duration_seconds:.1f} seconds\n"
        f"Number of sampled frames: {len(video.frame_paths)}\n\n"
        f"{transcript_section}\n\n"
        "Produce the ContentProfile JSON now."
    )


def _build_vision_user_prompt(video: VideoInfo, num_images: int) -> str:
    transcript_section = (
        f"Transcript (best-effort, may be partial):\n{video.transcript}"
        if video.transcript
        else "Transcript: not available (analyze based on the frames and duration/filename only)."
    )
    filename = video.path.rsplit("/", 1)[-1]
    return (
        f"Filename: {filename}\n"
        f"Duration: {video.duration_seconds:.1f} seconds\n"
        f"You are also given {num_images} sampled frame(s) from this video, attached as images "
        "in chronological order.\n\n"
        f"{transcript_section}\n\n"
        "Use both the frames and the transcript to produce the ContentProfile JSON now."
    )


def _parse_profile(raw: str, video: VideoInfo) -> ContentProfile:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Fall back to a very conservative default profile if the model
        # returns something unparsable, rather than crashing the app.
        data = dict(_FALLBACK_PROFILE_DATA)

    data["duration_seconds"] = video.duration_seconds
    return ContentProfile.model_validate(data)


async def _try_visual_content_profile(
    video: VideoInfo, llm: LLMProvider
) -> str | None:
    """Attempt the multimodal (frames + transcript) content-profile call.

    Returns the raw JSON string on success, or None if visual analysis
    isn't possible/available right now (no frames, provider doesn't
    support it, or the call failed) — callers should treat None as "fall
    back to transcript-only" rather than an error.

    Failures are logged with `logger.warning(..., exc_info=True)` (not
    `logger.info`) specifically so they're visible even in this app's
    default logging setup, which has no `logging.basicConfig()` call
    anywhere and would otherwise silently drop INFO-level records —
    that gap is what made the original Phase 4 failure look silent.
    """
    if not video.frame_paths:
        logger.info("No sampled frames available; skipping visual analysis.")
        return None

    image_paths = video.frame_paths[:_MAX_VISION_FRAMES]
    vision_user_prompt = _build_vision_user_prompt(video, len(image_paths))

    try:
        return await llm.complete_json_multimodal(
            CONTENT_PROFILE_VISION_SYSTEM_PROMPT,
            vision_user_prompt,
            image_paths=image_paths,
            temperature=0.4,
        )
    except Exception as e:  # noqa: BLE001 - any failure here must degrade, never crash
        print(f"  [VISUAL ANALYSIS ERROR] {type(e).__name__}: {e}")
        logger.warning(
            "Visual analysis failed; falling back to transcript-only content profile.",
            exc_info=True,
        )
        return None


async def build_content_profile(
    video: VideoInfo, llm: LLMProvider, settings: Settings | None = None
) -> ContentProfile:
    if settings is None:
        from app.config import settings as _default_settings

        settings = _default_settings

    raw: str | None = None
    visual_analysis_used = False

    if settings.enable_visual_analysis:
        raw = await _try_visual_content_profile(video, llm)
        visual_analysis_used = raw is not None

    if raw is None:
        user_prompt = _build_user_prompt(video)
        raw = await llm.complete_json(CONTENT_PROFILE_SYSTEM_PROMPT, user_prompt, temperature=0.4)

    status = "yes" if visual_analysis_used else "fallback to transcript"
    print(f"  Visual analysis: {status}")
    logger.info("Visual analysis: %s", status)

    return _parse_profile(raw, video)
