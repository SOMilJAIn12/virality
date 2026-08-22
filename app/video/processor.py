"""
Lightweight video preprocessing.

Goal for the MVP: turn a raw video file into a small amount of text
(rough description + basic metadata) that an LLM can turn into a
ContentProfile — WITHOUT building a heavy video-understanding pipeline.

What we actually extract:
  - duration (via OpenCV)
  - a handful of representative frame timestamps (evenly spaced)
  - an audio transcript, if ffmpeg + whisper are available (best-effort;
    if either is missing we degrade gracefully instead of crashing)

This keeps step 12/13 of the build honest: "do not spend most of the
MVP building an advanced video-analysis pipeline", while leaving an
obvious extension point (VideoInfo.frame_paths) for a future vision-model
pass.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field

import cv2

SUPPORTED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi"}


class VideoValidationError(ValueError):
    pass


@dataclass
class VideoInfo:
    path: str
    duration_seconds: float
    frame_paths: list[str] = field(default_factory=list)
    transcript: str | None = None


def validate_video_path(path: str) -> None:
    if not os.path.isfile(path):
        raise VideoValidationError(f"Video file not found: {path}")

    ext = os.path.splitext(path)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise VideoValidationError(
            f"Unsupported video extension '{ext}'. Supported: {sorted(SUPPORTED_EXTENSIONS)}"
        )

    cap = cv2.VideoCapture(path)
    opened = cap.isOpened()
    cap.release()
    if not opened:
        raise VideoValidationError(f"Could not open video file (is it corrupted?): {path}")


def _resize_for_vision(frame, max_dimension: int):
    """Downscale `frame` so its longer side is at most `max_dimension` px.

    Phase 6A: the original code wrote frames at their native video
    resolution (e.g. 1920x1080), which is what actually produced Groq's
    "Requested 8133 / Limit 8000" vision error -- 3 full-resolution JPEGs
    base64-encode into a large request regardless of how conservative our
    own token *estimate* is. Vision models don't need full resolution to
    judge a hook/reveal/on-screen-text; a small thumbnail carries the same
    signal at a fraction of the encoded size. No-op if the frame is
    already smaller than `max_dimension` (never upscales).
    """
    h, w = frame.shape[:2]
    longest = max(h, w)
    if longest <= max_dimension:
        return frame
    scale = max_dimension / float(longest)
    new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
    return cv2.resize(frame, new_size, interpolation=cv2.INTER_AREA)


def _extract_duration_and_frames(
    path: str,
    num_frames: int = 3,
    max_dimension: int = 288,
    jpeg_quality: int = 50,
) -> tuple[float, list[str]]:
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 0
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    duration = (frame_count / fps) if fps > 0 else 0.0

    frame_paths: list[str] = []
    if frame_count > 0:
        tmp_dir = tempfile.mkdtemp(prefix="virality_frames_")
        # Evenly spaced sample points, avoiding the very first/last frame.
        positions = [int(frame_count * f) for f in _sample_fractions(num_frames)]
        for i, pos in enumerate(positions):
            cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
            ok, frame = cap.read()
            if not ok:
                continue
            frame = _resize_for_vision(frame, max_dimension)
            out_path = os.path.join(tmp_dir, f"frame_{i}.jpg")
            # Quality param + resize above are what keep the multimodal
            # request comfortably under the Groq TPM budget (see
            # app/llm/groq.py's per-image token estimate, which is now
            # computed from the actual encoded size of these files).
            cv2.imwrite(out_path, frame, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])
            frame_paths.append(out_path)

    cap.release()
    return duration, frame_paths


def _sample_fractions(n: int) -> list[float]:
    if n <= 1:
        return [0.5]
    return [(i + 1) / (n + 1) for i in range(n)]


def _try_transcribe(path: str) -> str | None:
    """Best-effort transcript via ffmpeg (extract audio) + whisper.

    Returns None (not an exception) if ffmpeg or whisper isn't available,
    since a transcript is a nice-to-have for the MVP, not a hard requirement.
    """
    if shutil.which("ffmpeg") is None:
        return None

    try:
        import whisper  # openai-whisper, optional dependency
    except ImportError:
        return None

    tmp_audio = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp_audio.close()
    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", path,
                "-ac", "1", "-ar", "16000", "-vn", tmp_audio.name,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        model = whisper.load_model("base")
        result = model.transcribe(tmp_audio.name)
        text = (result.get("text") or "").strip()
        return text or None
    except Exception as e:
        # Any failure here (missing codecs, no audio track, etc.) should not
        # crash the MVP — we just fall back to visual-only analysis.
        print(f"[TRANSCRIPTION ERROR] {type(e).__name__}: {e}")
        return None
    finally:
        try:
            os.remove(tmp_audio.name)
        except OSError:
            pass


def process_video(
    path: str,
    num_frames: int = 3,
    try_transcript: bool = True,
    frame_max_dimension: int = 288,
    frame_jpeg_quality: int = 50,
) -> VideoInfo:
    """Validate + extract lightweight info from a local video file.

    `frame_max_dimension`/`frame_jpeg_quality` control the size of the
    sampled frame JPEGs (see `_resize_for_vision`), which directly
    determines how many tokens the Phase 4 vision call costs -- kept as
    parameters (backed by `Settings.video_frame_max_dimension` /
    `Settings.video_frame_jpeg_quality`) so this stays tunable instead of
    a hardcoded assumption about any particular Groq tier.
    """
    validate_video_path(path)
    duration, frame_paths = _extract_duration_and_frames(
        path,
        num_frames=num_frames,
        max_dimension=frame_max_dimension,
        jpeg_quality=frame_jpeg_quality,
    )
    transcript = _try_transcribe(path) if try_transcript else None
    return VideoInfo(
        path=path,
        duration_seconds=duration,
        frame_paths=frame_paths,
        transcript=transcript,
    )
