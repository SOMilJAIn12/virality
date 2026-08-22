"""
Central configuration for the AI Virality Simulator.

Everything here is loaded from environment variables (via a .env file)
so that no secrets or magic numbers are hardcoded across the codebase.

Every other module should import `settings` from here instead of
calling os.environ / os.getenv directly.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

# Load variables from a .env file in the project root (if present).
load_dotenv()


def _get_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return float(raw)


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _get_int_list(name: str, default: list[int]) -> list[int]:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return [int(x.strip()) for x in raw.split(",") if x.strip()]


def _get_optional_int(name: str) -> int | None:
    """Like _get_int, but returns None (not a default) when unset/empty.

    Used for SIMULATION_SEED: unset must mean "use normal random
    behavior", not "use some fallback integer seed".
    """
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return None
    return int(raw)


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class RecommendationWeights:
    """Weights for the deterministic 'Instagram-inspired' distribution score.

    This is NOT Instagram's real algorithm. It's a simplified, transparent,
    configurable formula we invented for this simulation so results are
    explainable and reproducible.
    """
    completion: float = _get_float("COMPLETION_WEIGHT", 0.30)
    share: float = _get_float("SHARE_WEIGHT", 0.25)
    comment: float = _get_float("COMMENT_WEIGHT", 0.15)
    like: float = _get_float("LIKE_WEIGHT", 0.10)
    follow: float = _get_float("FOLLOW_WEIGHT", 0.10)
    rewatch: float = _get_float("REWATCH_WEIGHT", 0.10)
    skip_penalty: float = _get_float("SKIP_PENALTY", 0.20)


@dataclass(frozen=True)
class Settings:
    # --- LLM provider ---
    model_provider: str = os.getenv("MODEL_PROVIDER", "ollama").strip().lower()

    ollama_model: str = os.getenv("OLLAMA_MODEL", "").strip()
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434").strip()

    groq_api_key: str = os.getenv("GROQ_API_KEY", "").strip()
    groq_model: str = os.getenv("GROQ_MODEL", "").strip()

    # --- Phase 4: visual understanding (content-profile step only) ---
    # `GROQ_MODEL` above (e.g. openai/gpt-oss-120b) is text-only — it does
    # NOT support image input. Vision needs a separate, vision-capable
    # model, used ONLY when building the ContentProfile, never for persona
    # calls (that would multiply image cost by 15+ personas per round).
    # NOTE: meta-llama/llama-4-scout-17b-16e-instruct (the original Phase 4
    # default) was decommissioned by Groq (shutdown 07/17/26) and now
    # returns HTTP 404 model_not_found. qwen/qwen3.6-27b is the current
    # vision-capable replacement, though Groq serves it as PREVIEW (not
    # production-SLA'd) — recheck https://console.groq.com/docs/vision.
    groq_vision_model: str = os.getenv(
        "GROQ_VISION_MODEL", "qwen/qwen3.6-27b"
    ).strip()

    # Master switch for the whole visual-analysis feature. When False (or
    # when no frames/vision model are available), content-profile
    # generation is transcript-only, same as before Phase 4.
    enable_visual_analysis: bool = _get_bool("ENABLE_VISUAL_ANALYSIS", True)

    # --- Phase 6A: vision frame size (token efficiency) ---
    # The number of frames sampled per video, and the size/quality they're
    # saved at before being sent to the vision model. Full-resolution
    # frames are what caused "Request too large ... Requested 8133 /
    # Limit 8000" -- a small thumbnail carries the same visual signal
    # (hook, on-screen text, reveal moment) at a fraction of the encoded
    # size. Configurable so a higher-tier Groq plan (or a different vision
    # model) can raise these back up without a code change.
    video_num_frames: int = _get_int("VIDEO_NUM_FRAMES", 3)
    video_frame_max_dimension: int = _get_int("VIDEO_FRAME_MAX_DIMENSION", 288)
    video_frame_jpeg_quality: int = _get_int("VIDEO_FRAME_JPEG_QUALITY", 50)

    # --- Concurrency ---
    # Originally 10. That's a request-count cap, not a token-budget cap
    # -- 10 persona calls fired at once (each ~700-1000 tokens including
    # the persona system prompt + schema) can burst past an 8000 TPM
    # limit in a single instant, which is what caused repeated 429s.
    # Lowered to 3: still gives a meaningful concurrency speedup over
    # fully-sequential calls, but keeps the largest possible burst
    # (~3 x ~1000 tokens ≈ 3000 tokens) comfortably under budget so the
    # token-per-minute limiter (app/llm/rate_limit.py) rarely has to
    # make anyone wait. Still fully configurable via .env for people on
    # a higher-tier Groq plan or using a local Ollama model (no TPM cap).
    max_concurrent_agents: int = _get_int("MAX_CONCURRENT_AGENTS", 3)

    # --- Groq rate limiting ---
    # The tokens-per-minute budget for the active Groq plan/model. Used
    # by GroqProvider's TokenPerMinuteLimiter to throttle calls BEFORE
    # sending them, instead of only reacting to 429s after the fact.
    groq_tpm_limit: int = _get_int("GROQ_TPM_LIMIT", 8000)

    # --- Distribution decision ---
    # 0.70 was the original default but is effectively unreachable given
    # the weights below: even a strong, realistic round (e.g. ~70%
    # completion, ~30% share, ~10% comment, ~60% like, ~15% follow, ~20%
    # rewatch, ~30% skip) only scores ~0.33. Hitting 0.70 would require
    # near-100% completion/share/comment/like/follow/rewatch with 0%
    # skip simultaneously, which no realistic cohort produces. That made
    # every round STOP at round 1 regardless of content quality. 0.30 was
    # chosen so genuinely weak content (~0.0-0.2) still STOPs, while
    # good/strong content (~0.30+) can PUSH to the next, larger cohort —
    # see the BAD/MEDIUM/GOOD/EXCELLENT scenarios in
    # tests/test_scoring_and_aggregation.py for the numbers behind this.
    push_threshold: float = _get_float("PUSH_THRESHOLD", 0.30)

    # --- Recommendation weights ---
    weights: RecommendationWeights = field(default_factory=RecommendationWeights)

    # --- Rounds ---
    round_cohort_sizes: list[int] = field(
        default_factory=lambda: _get_int_list("ROUND_COHORT_SIZES", [15, 30, 60])
    )

    # --- Phase 5D: reproducible persona cohort sampling ---
    # Optional simulation-level seed for persona cohort selection ONLY
    # (app/simulation/engine.py::build_cohort / run_simulation). This has
    # NO effect on LLM temperature or model output -- it only controls
    # which/what-order personas are sampled from the pool for a given
    # round, via a local `random.Random(seed)` instance (never the
    # global `random` module).
    #
    # Unset (default): every simulation run samples cohorts using normal
    # unseeded randomness, same as before this phase.
    # Set: the same video + same SIMULATION_SEED reproduces the exact
    # same cohort membership/order every run; a different seed can
    # produce a different cohort.
    simulation_seed: int | None = _get_optional_int("SIMULATION_SEED")

    def validate(self) -> None:
        """Fail fast with a clear message if required config is missing."""
        if self.model_provider not in {"ollama", "groq"}:
            raise ValueError(
                f"MODEL_PROVIDER must be 'ollama' or 'groq', got '{self.model_provider}'"
            )
        if self.model_provider == "ollama" and not self.ollama_model:
            raise ValueError(
                "MODEL_PROVIDER=ollama but OLLAMA_MODEL is empty. "
                "Set OLLAMA_MODEL in your .env (e.g. OLLAMA_MODEL=llama3.1)."
            )
        if self.model_provider == "groq":
            if not self.groq_api_key:
                raise ValueError("MODEL_PROVIDER=groq but GROQ_API_KEY is empty.")
            if not self.groq_model:
                raise ValueError("MODEL_PROVIDER=groq but GROQ_MODEL is empty.")


settings = Settings()
