from __future__ import annotations

import asyncio
from collections.abc import Callable

from app.config import settings
from app.llm.factory import create_llm_provider
from app.models import SimulationReport
from app.personas.definitions import get_persona_pool
from app.simulation.content import build_content_profile
from app.simulation.engine import run_simulation
from app.simulation.report import build_report
from app.video.processor import process_video

ProgressCallback = Callable[[str], None]


async def run_pipeline(
    video_path: str,
    seed: int | None = None,
    on_progress: ProgressCallback | None = None,
) -> SimulationReport:
    """Run the existing CLI pipeline and return its structured report."""

    def progress(message: str) -> None:
        if on_progress:
            on_progress(message)

    try:
        settings.validate()
    except ValueError as error:
        raise RuntimeError(f"Python service configuration error: {error}") from error

    # Mirrors main.py's CLI precedence: an explicit seed argument wins,
    # otherwise fall back to the optional SIMULATION_SEED from config/.env.
    effective_seed = seed if seed is not None else settings.simulation_seed

    progress("Extracting video content...")

    # Video/Whisper work is synchronous and can be slow, so run it off
    # FastAPI's event loop. Frame sampling/compression settings are passed
    # through explicitly so VIDEO_NUM_FRAMES / VIDEO_FRAME_MAX_DIMENSION /
    # VIDEO_FRAME_JPEG_QUALITY from .env actually take effect here, exactly
    # as they do for the CLI in main.py.
    video_info = await asyncio.to_thread(
        process_video,
        video_path,
        settings.video_num_frames,
        True,
        settings.video_frame_max_dimension,
        settings.video_frame_jpeg_quality,
    )

    llm = create_llm_provider(settings)

    try:
        progress("Analyzing content...")
        content_profile = await build_content_profile(video_info, llm, settings)

        progress("Preparing viewer personas...")
        persona_pool = get_persona_pool()

        # NOTE: app.simulation.engine.run_simulation (Version A / the
        # authoritative AI engine) has no on_progress hook, so we don't pass
        # one here -- doing so would raise a TypeError. Progress reporting
        # around this call stays coarse-grained (before/after) rather than
        # per-round, matching what the engine actually exposes.
        rounds = await run_simulation(
            content=content_profile,
            persona_pool=persona_pool,
            llm=llm,
            settings=settings,
            seed=effective_seed,
        )

        if not rounds:
            raise RuntimeError("The simulation completed without any rounds.")

        progress("Generating final report...")
        report = await build_report(video_path, content_profile, rounds, llm, settings)

        progress("Completed")
        return report

    finally:
        aclose = getattr(llm, "aclose", None)

        if aclose:
            await aclose()