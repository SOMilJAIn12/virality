#!/usr/bin/env python3
"""
AI Virality Prediction Simulator — CLI entry point.

Usage:
    python main.py --video ./videos/my_reel.mp4

Pipeline:
    Video file
      -> process_video()        (app/video/processor.py)      duration, frames, transcript
      -> build_content_profile()(app/simulation/content.py)    1 LLM call -> ContentProfile
      -> run_simulation()       (app/simulation/engine.py)     N rounds of concurrent personas
      -> build_report()         (app/simulation/report.py)     deterministic score + AI summary
      -> render_text_report()   (app/simulation/report.py)     printable final report
"""
from __future__ import annotations

import argparse
import asyncio
import sys

from app.config import settings
from app.llm.factory import create_llm_provider
from app.personas.definitions import get_persona_pool
from app.simulation.benchmarks import compute_benchmark_scores, render_benchmark_report
from app.simulation.content import build_content_profile
from app.simulation.engine import run_simulation
from app.simulation.report import build_report, render_text_report
from app.video.processor import VideoValidationError, process_video


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI Virality Prediction Simulator")
    parser.add_argument(
        "--video", required=False, help="Path to a short-form video file"
    )
    parser.add_argument(
        "--seed", type=int, default=None, help="Optional random seed for reproducible cohorts"
    )
    parser.add_argument(
        "--no-transcript",
        action="store_true",
        help="Skip audio transcription even if ffmpeg/whisper are available (faster)",
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help=(
            "Run the offline synthetic scoring benchmark (Phase 5E) and exit. "
            "Uses deterministic synthetic data only -- no video, no Groq/Whisper/"
            "FFmpeg calls, no API key required."
        ),
    )
    args = parser.parse_args(argv)
    if not args.benchmark and not args.video:
        parser.error("--video is required unless --benchmark is given")
    return args


def run_benchmark() -> int:
    """Phase 5E offline benchmark: prints the CURRENT scoring formula's
    output for the five synthetic calibration scenarios. Does not touch
    the LLM provider, video processing, or settings.validate() (which
    requires a configured provider/API key) -- this must work even with
    an empty .env."""
    results = compute_benchmark_scores(
        settings.weights, settings.round_cohort_sizes, settings.push_threshold
    )
    print(render_benchmark_report(results))
    return 0


async def async_main(argv: list[str]) -> int:
    args = parse_args(argv)

    if args.benchmark:
        return run_benchmark()

    try:
        settings.validate()
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("   Copy .env.example to .env and fill in the required values.")
        return 1

    print(f"Using provider: {settings.model_provider}")

    # --- Step 1: video processing ---
    print(f"\nReading video: {args.video}")
    try:
        video_info = process_video(
            args.video,
            num_frames=settings.video_num_frames,
            try_transcript=not args.no_transcript,
            frame_max_dimension=settings.video_frame_max_dimension,
            frame_jpeg_quality=settings.video_frame_jpeg_quality,
        )
    except VideoValidationError as e:
        print(f"❌ {e}")
        return 1

    print(f"  Duration: {video_info.duration_seconds:.1f}s")
    print(f"  Sampled frames: {len(video_info.frame_paths)}")
    print(f"  Transcript: {'yes' if video_info.transcript else 'not available'}")

    llm = create_llm_provider(settings)

    try:
        # --- Step 2: content profile (1 LLM call) ---
        print("\nAnalyzing content...")
        content_profile = await build_content_profile(video_info, llm, settings)
        print(f"  Title: {content_profile.title}")
        print(f"  Target audience: {content_profile.target_audience}")

        # --- Step 3: multi-round persona simulation (concurrent LLM calls) ---
        persona_pool = get_persona_pool()
        # CLI --seed takes precedence when given; otherwise fall back to the
        # optional SIMULATION_SEED from config/.env (None by default, i.e.
        # normal unseeded random cohort sampling).
        seed = args.seed if args.seed is not None else settings.simulation_seed
        rounds = await run_simulation(
            content=content_profile,
            persona_pool=persona_pool,
            llm=llm,
            settings=settings,
            seed=seed,
        )

        if not rounds:
            print("❌ No rounds completed — nothing to report.")
            return 1

        # --- Step 4: scoring + report ---
        print("\nGenerating final report...")
        report = await build_report(args.video, content_profile, rounds, llm, settings)
        print("\n" + render_text_report(report))

        return 0
    finally:
        aclose = getattr(llm, "aclose", None)
        if aclose:
            await aclose()


def main() -> None:
    argv = sys.argv[1:]
    exit_code = asyncio.run(async_main(argv))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
