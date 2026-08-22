from __future__ import annotations

import asyncio
import shutil
import tempfile
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status

from app.service import run_pipeline
from app.video.processor import SUPPORTED_EXTENSIONS

app = FastAPI(
    title="AI Virality Python Service",
    version="0.1.0",
)

jobs: dict[str, dict[str, Any]] = {}

upload_directory = Path(tempfile.gettempdir()) / "aivirality-uploads"
upload_directory.mkdir(parents=True, exist_ok=True)


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "python-simulation-engine",
    }


@app.post("/simulate", status_code=status.HTTP_202_ACCEPTED)
async def create_simulation(
    video: UploadFile = File(...),
    seed: int | None = Form(default=None),
) -> dict[str, str]:
    extension = Path(video.filename or "").suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported video extension '{extension}'. "
                f"Supported: {sorted(SUPPORTED_EXTENSIONS)}"
            ),
        )

    simulation_id = f"sim_{uuid4().hex[:8]}"
    video_path = upload_directory / f"{simulation_id}{extension}"

    try:
        with video_path.open("wb") as output_file:
            shutil.copyfileobj(video.file, output_file)
    finally:
        await video.close()

    jobs[simulation_id] = {
        "simulationId": simulation_id,
        "status": "PENDING",
        "progress": "Video uploaded. Waiting to start...",
        "result": None,
        "error": None,
    }

    asyncio.create_task(run_job(simulation_id, video_path, seed))

    return {
        "simulationId": simulation_id,
        "status": "PENDING",
    }


@app.get("/simulate/{simulation_id}")
async def get_simulation(simulation_id: str) -> dict[str, Any]:
    job = jobs.get(simulation_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Simulation not found.",
        )

    return job


async def run_job(
    simulation_id: str,
    video_path: Path,
    seed: int | None,
) -> None:
    job = jobs[simulation_id]
    job["status"] = "PROCESSING"

    def update_progress(message: str) -> None:
        job["progress"] = message

    try:
        report = await run_pipeline(
            video_path=str(video_path),
            seed=seed,
            on_progress=update_progress,
        )

        job["status"] = "COMPLETED"
        job["progress"] = "Completed"
        job["result"] = report.model_dump()

    except Exception as error:
        job["status"] = "FAILED"
        job["progress"] = "Failed"
        job["error"] = str(error)

    finally:
        video_path.unlink(missing_ok=True)