# AI Virality Prediction Simulator

An AI-powered short-form video virality simulator that evaluates a video using AI-generated viewer personas and simulates how the content may perform across multiple distribution rounds.

> **Current status:** MVP / Phase 5 completed. The system has been calibrated and performance-optimized, but it is still a simulation—not a reproduction of Instagram/YouTube/TikTok's real recommendation algorithm.

---

## 1. What the Project Does

The user provides a short-form video.

The pipeline:

```text
Video
  │
  ├── Whisper → Transcript
  │
  ├── Video frames → Vision LLM → Content Profile
  │
  └── Content Profile + Transcript
          │
          ▼
    AI Viewer Personas
          │
          ▼
   Round 1 → 15 personas
          │
       PUSH/STOP
          │
          ▼
   Round 2 → 30 personas
          │
       PUSH/STOP
          │
          ▼
   Round 3 → 60 personas
          │
          ▼
    Final Virality Score
```

Each persona independently evaluates whether they would:

- Watch
- Complete
- Rewatch
- Like
- Comment
- Share
- Follow

The simulator aggregates these reactions into a distribution score and ultimately produces a **Virality Score from 0–100**.

---

# 2. Current Tech Stack

- Python
- FastAPI/project Python modules
- Groq API
- Whisper for transcription
- GPT-OSS 20B for persona evaluation
- Qwen Qwen3.6-27B for visual content analysis
- Pydantic
- asyncio
- Tenacity
- pytest

---

# 3. LLM Configuration

Current `.env` configuration:

```env
MODEL_PROVIDER=groq

GROQ_MODEL=openai/gpt-oss-20b

GROQ_VISION_MODEL=qwen/qwen3.6-27b

ENABLE_VISUAL_ANALYSIS=true
```

### Persona model

The persona evaluator currently uses:

```text
openai/gpt-oss-20b
```

This replaced:

```text
openai/gpt-oss-120b
```

The 120B model was found to be extremely slow under concurrent requests.

### Vision model

Visual analysis continues to use:

```text
qwen/qwen3.6-27b
```

If visual analysis exceeds the Groq TPM limit, the application falls back to transcript-only content analysis instead of terminating the simulation.

---

# 4. Major Phases Completed

## Phase 5A — Persona Decision Calibration

### Problem discovered

The original persona prompt contained overly negative base-rate instructions such as:

```text
Do not be polite or generous by default — most content gets skipped or ignored in real life.
```

and encouraged low-interest personas to skip.

This caused curiosity-driven entertainment content to be systematically undervalued.

### Changes

#### Persona temperature

Changed:

```text
temperature=0.8
```

to:

```text
temperature=0.4
```

This reduced run-to-run stochastic variation.

#### Persona decision prompt

The persona prompt was rewritten to:

- Allow strong hooks to override normal topical-interest mismatch.
- Consider curiosity and mystery.
- Consider surprise/reveal/payoff.
- Consider general entertainment value.
- Avoid treating lack of topical interest as an automatic skip.
- Keep personas selective and realistic.

Topical interest remains especially relevant for:

- Likes
- Shares
- Comments
- Follows

while broad curiosity/entertainment can influence the initial watch decision.

### Watch/engagement consistency

A logical consistency rule was added.

If:

```text
watch = false
```

then:

```text
completion_rate = 0
rewatch = false
like = false
comment = false
share = false
follow = false
comment_text = null
```

This is enforced both in the persona prompt and defensively through Pydantic validation.

---

# 5. Phase 5B — Curiosity / Surprise Signal

A new ContentProfile field was added:

```python
curiosity_surprise_strength: float
```

Range:

```text
0.0 – 1.0
```

It represents:

- Curiosity
- Mystery
- Anticipation
- Surprise
- Reveal/payoff
- Unexpected outcomes

This was added because generic `hook_strength` and `entertainment_value` were not enough to explicitly represent the mechanics behind curiosity-driven viral content.

### Prompt updates

Content-profile prompts were updated to explicitly evaluate this signal.

Persona prompts were also updated so personas receive:

```text
Curiosity/surprise strength
```

as part of the content profile.

The fallback profile uses:

```text
curiosity_surprise_strength = 0.5
```

---

# 6. Phase 5C — Persona Pool Expansion

The original persona pool contained:

```text
15 personas
```

It was expanded to:

```text
18 personas
```

Added personas:

### Surprise/Curiosity Viewer

```text
surprise_curiosity_viewer
```

Focused on:

- surprising videos
- mysteries
- challenges

### Short-Form Entertainment Viewer

```text
short_form_entertainment_viewer
```

Focused on:

- viral videos
- comedy
- reactions

### Mainstream Casual Viewer

```text
mainstream_casual_viewer
```

Focused on:

- entertainment
- sports
- travel
- funny videos

All original 15 personas were preserved.

No original tendency values were changed.

---

# 7. Phase 5D — Deterministic Simulation Seeds

A simulation seed was added for reproducible persona cohort sampling.

Configuration:

```env
SIMULATION_SEED=
```

Empty means normal random behavior.

Example:

```env
SIMULATION_SEED=42
```

or:

```powershell
python main.py --video .\videos\Video-74608.mp4 --seed 42
```

The seed controls:

- Persona cohort sampling
- Persona ordering

It does NOT control:

- LLM temperature
- LLM output
- Groq generation
- scoring

The implementation uses a local:

```python
random.Random(seed)
```

rather than changing global random state.

The same seed + same persona pool reproduces the same cohort selection/order.

---

# 8. Phase 5E — Score Breakdown & Benchmarking

The scoring implementation was refactored to expose a structured score breakdown.

A `ScoreBreakdown` structure was introduced containing:

```text
weighted_engagement
reach_component
penetration_component
final_raw_score
final_score_0_to_100
```

`compute_virality_score()` now uses the shared breakdown calculation.

### Important

The scoring formula itself was NOT changed.

The existing weights remain:

```text
Completion = 0.30
Share      = 0.25
Comment    = 0.15
Like       = 0.10
Follow     = 0.10
Rewatch    = 0.10
Skip Penalty = 0.20
```

The distribution threshold remains:

```text
PUSH_THRESHOLD=0.30
```

Decision rule:

```text
distribution_score >= 0.30 → PUSH
distribution_score <  0.30 → STOP
```

### Benchmark scenarios

Using the existing formula:

```text
VERY BAD     → 0.0 / 100
WEAK         → 0.0 / 100
DECENT       → 10.1 / 100
STRONG       → 59.6 / 100
EXCEPTIONAL  → 72.3 / 100
```

This revealed that very bad and weak profiles can both collapse to 0 because of the skip penalty.

That was flagged as a calibration issue but was intentionally NOT changed during Phase 5E.

---

# 9. Performance Investigation

The original persona model was:

```text
openai/gpt-oss-120b
```

It caused severe latency.

### Single persona benchmark

Approximately:

```text
53 seconds
```

### Three concurrent personas

More than:

```text
304 seconds
```

without aggregate completion.

The investigation confirmed:

- Local rate limiter was not the primary bottleneck.
- JSON parsing was negligible.
- Pydantic validation was negligible.
- Tenacity was not retrying the measured request.
- asyncio concurrency was working.
- The major issue was provider/model latency and concurrency degradation for GPT-OSS 120B.

---

# 10. GPT-OSS 20B Optimization

The persona model was switched to:

```env
GROQ_MODEL=openai/gpt-oss-20b
```

This produced a dramatic improvement.

### Single persona

```text
~0.753 seconds
```

### Three concurrent personas

```text
~1.013 seconds total
```

Example concurrent latencies:

```text
AI/ML Student          0.613 sec
Software Developer     1.013 sec
College Student        0.610 sec
```

### Comparison

| Metric | GPT-OSS 120B | GPT-OSS 20B |
|---|---:|---:|
| Single persona | ~53 sec | ~0.75 sec |
| 3 concurrent | >304 sec | ~1.01 sec |
| Retries | 0 | 0 |
| Limiter wait | negligible | negligible |

The 20B model is therefore the current persona evaluator.

---

# 11. GPT-OSS Model Handling

The code recognizes both GPT-OSS models:

```python
_GPT_OSS_MODELS = {
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
}
```

GPT-OSS-specific reasoning handling can therefore be applied consistently to either model.

The current persona model is:

```text
openai/gpt-oss-20b
```

with low reasoning effort.

---

# 12. Concurrency

Current configuration:

```env
MAX_CONCURRENT_AGENTS=3
```

This means at most three persona LLM calls are active concurrently.

The system uses asyncio-based concurrency and a semaphore to enforce the limit.

The concurrency value was deliberately not increased during the optimization because Groq TPM and provider-side behavior need to be respected.

---

# 13. Groq TPM Protection

Current configured TPM budget:

```env
GROQ_TPM_LIMIT=8000
```

The local limiter proactively manages token reservations.

A previous issue was identified where rejected HTTP 429 requests could remain represented in the local rolling token window.

The limiter was adjusted so that reservations from requests rejected specifically with HTTP 429 can be released, while other failures remain conservatively accounted for.

---

# 14. Video / Vision Configuration

Current settings:

```env
VIDEO_NUM_FRAMES=3
VIDEO_FRAME_MAX_DIMENSION=288
VIDEO_FRAME_JPEG_QUALITY=50
```

These settings were introduced to keep visual requests small enough for Groq's TPM limits.

### Vision fallback

If the vision model returns a request-size / TPM error such as:

```text
Requested 8196
Limit 8000
```

the application does not terminate.

Instead:

```text
Vision analysis failed
        ↓
Transcript-only fallback
        ↓
Simulation continues
```

This behavior was observed successfully during real runs.

---

# 15. Example Real-World Test

A real test was performed using:

```text
Video-74608.mp4
```

The video was a:

```text
Blindfolded Surprise Trip to the World Cup
```

The final simulation produced:

```text
Round 1 → 0.63 → PUSH
Round 2 → 0.61 → PUSH
Round 3 → 0.58 → PUSH
```

Final result:

```text
VIRALITY SCORE: 76/100
Potential: HIGH
```

Final engagement metrics:

```text
Round 1
Watch       100.0%
Completion   84.3%
Rewatch       6.7%
Like         73.3%
Comment      40.0%
Share        93.3%
Follow        0.0%

Round 2
Watch       100.0%
Completion   82.3%
Rewatch       3.3%
Like         80.0%
Comment      40.0%
Share        90.0%
Follow        0.0%

Round 3
Watch       100.0%
Completion   82.0%
Rewatch       3.3%
Like         68.3%
Comment      40.0%
Share        81.7%
Follow        0.0%
```

### Interpretation

The simulator identified:

### Strengths

- Strong completion
- Strong shareability
- Broad entertainment appeal
- Strong conversation potential
- Curiosity/surprise appeal

### Weakness

- Poor follow conversion

The result was:

```text
76/100
HIGH potential
```

This is a significant improvement over the original runs that produced approximately 8–20 scores for the same type of content.

---

# 16. Important Calibration Observation

The new system may now be somewhat optimistic.

The 76/100 result is much more believable for a highly viral curiosity-driven entertainment video than the previous ~8/100 result.

However, the following values are aggressive:

```text
100% watch rate
82%+ completion
81%–93% share rate
```

Therefore, the next calibration task should investigate whether the persona prompt has overcorrected from the original negativity bias.

In particular:

```text
100% watch rate
```

across 15, 30, and 60 personas may be too optimistic.

This should be investigated before claiming the simulator is perfectly calibrated.

---

# 17. Tests

The project has accumulated tests across the phases.

Reported test counts:

```text
Phase 5A → 39
Phase 5B → 52
Phase 5C → 63
Phase 5D → 77
Phase 5E → 92+
```

Later model-switch validation reported:

```text
106 passed
```

The tests cover areas including:

- Persona temperature
- PersonaReaction consistency
- ContentProfile curiosity field
- Persona pool expansion
- Simulation seed behavior
- Score breakdown
- Benchmark scenarios
- Threshold behavior
- Score sensitivity
- GPT-OSS handling
- Existing functionality regression

---

# 18. What Was NOT Changed

The following were deliberately preserved:

- Core scoring formula
- Aggregation semantics
- PUSH threshold
- Persona tendency definitions for original personas
- Persona decision schema
- ContentProfile core fields
- Simulation round structure
- Cohort sizes
- Report format
- Vision model architecture
- Temperature = 0.4
- Seed semantics
- No artificial score multiplier
- No forced persona engagement
- No hidden virality bonus
- No fake real-platform algorithm

---

# 19. Current Architecture

```text
                    ┌───────────────────┐
                    │      Video        │
                    └─────────┬─────────┘
                              │
               ┌──────────────┴──────────────┐
               │                             │
               ▼                             ▼
        Whisper Transcript            Sample Video Frames
               │                             │
               │                             ▼
               │                    Qwen Vision Model
               │                             │
               └──────────────┬──────────────┘
                              ▼
                       ContentProfile
                              │
                              │
                 ┌────────────▼────────────┐
                 │ 18 AI Viewer Personas   │
                 │                          │
                 │ GPT-OSS 20B             │
                 │ temperature = 0.4       │
                 └────────────┬────────────┘
                              │
                     asyncio concurrency
                         max = 3
                              │
               ┌──────────────┼──────────────┐
               ▼              ▼              ▼
             Round 1        Round 2        Round 3
            15 personas    30 personas    60 personas
               │              │              │
               └──────────────┼──────────────┘
                              ▼
                     Distribution Score
                              │
                     ┌────────┴────────┐
                     │                 │
                  >= 0.30            < 0.30
                     │                 │
                    PUSH              STOP
                              │
                              ▼
                       Virality Score
                           0–100
```

---

# 20. Running the Project

Activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Run a video:

```powershell
python main.py --video .\videos\Video-74608.mp4
```

Run with deterministic cohort sampling:

```powershell
python main.py --video .\videos\Video-74608.mp4 --seed 42
```

Run tests:

```powershell
python -m pytest tests/ -v
```

---

# 21. Current `.env` Important Settings

```env
MODEL_PROVIDER=groq

GROQ_MODEL=openai/gpt-oss-20b

GROQ_VISION_MODEL=qwen/qwen3.6-27b

ENABLE_VISUAL_ANALYSIS=true

VIDEO_NUM_FRAMES=3
VIDEO_FRAME_MAX_DIMENSION=288
VIDEO_FRAME_JPEG_QUALITY=50

MAX_CONCURRENT_AGENTS=3
GROQ_TPM_LIMIT=8000

PUSH_THRESHOLD=0.30

COMPLETION_WEIGHT=0.30
SHARE_WEIGHT=0.25
COMMENT_WEIGHT=0.15
LIKE_WEIGHT=0.10
FOLLOW_WEIGHT=0.10
REWATCH_WEIGHT=0.10
SKIP_PENALTY=0.20

ROUND_COHORT_SIZES=15,30,60

SIMULATION_SEED=
```

**Never commit your real `GROQ_API_KEY` to GitHub.** Keep it only in `.env` and make sure `.env` is in `.gitignore`.

---

# 22. Known Limitations / Next Work

The current system is an MVP.

Important next areas:

1. **Vision request calibration**
   - Current Qwen vision requests can exceed the 8,000 TPM limit by a small amount.
   - The application falls back to transcript-only analysis when this happens.

2. **Persona calibration**
   - Watch rates can become unrealistically high.
   - Share rates may also be aggressive.

3. **Real-world calibration dataset**
   - Compare predicted scores against many videos with known real-world performance.
   - Use multiple low-, medium-, and high-performing examples.

4. **Score calibration**
   - Avoid calibrating against only one viral video.
   - Establish benchmark distributions across many videos.

5. **More realistic audience modeling**
   - Separate broad curiosity from topical affinity.
   - Model audience fatigue and diminishing distribution.

6. **Better visual sampling**
   - Three frames may miss important hook/reveal moments.
   - Future versions can use adaptive frame sampling while staying within token limits.

7. **Production reliability**
   - Better observability and per-persona latency/token logging.
   - Better handling of provider-side rate limits.

---

# 23. Key Lessons From Development

### Lesson 1

The original low scores were not primarily caused by the scoring formula.

The biggest issue was upstream persona behavior.

### Lesson 2

Curiosity-driven content cannot be modeled purely through topical-interest matching.

A viewer may have zero interest in a creator's niche but still watch because of:

```text
mystery
curiosity
surprise
reveal
entertainment
```

### Lesson 3

LLM temperature can create significant score variance.

The persona evaluator was reduced from:

```text
0.8 → 0.4
```

to improve stability.

### Lesson 4

Model selection matters enormously.

GPT-OSS 120B:

```text
~53 sec/persona
```

GPT-OSS 20B:

```text
~0.75 sec/persona
```

For this constrained classification task, the smaller model is dramatically more practical.

### Lesson 5

Concurrency is not automatically faster.

Three simultaneous GPT-OSS 120B requests caused severe provider-side latency, while three GPT-OSS 20B requests completed in about one second.

---

# 24. Project Status

### Completed

- [x] Video ingestion
- [x] Whisper transcription
- [x] Vision content analysis
- [x] Transcript fallback
- [x] Structured ContentProfile
- [x] Curiosity/surprise signal
- [x] AI persona simulation
- [x] 18-persona pool
- [x] Multi-round distribution simulation
- [x] PUSH/STOP mechanism
- [x] Virality scoring
- [x] Score breakdown
- [x] Deterministic cohort seed
- [x] Persona consistency validation
- [x] Groq TPM protection
- [x] GPT-OSS 20B optimization
- [x] Automated tests

### Current result

The simulator can now process a highly viral curiosity-driven video through all three rounds and produce a high-potential score.

Example:

```text
76/100 — HIGH
```

The next major goal is **calibration against a diverse real-world video dataset**, not further arbitrary score boosting.

---

## Backend / Full-Stack Integration (merged from the `feature/backend-api` branch)

This repo now also ships an Express + PostgreSQL backend and a Vite/React frontend on
top of the Python simulation engine described above. The Python engine remains the
single source of truth for content analysis, persona reactions, aggregation, scoring,
and the final report — the backend never recomputes or reconstructs the virality score.

```text
Frontend (React/Vite)
        ↓
Express Backend  (backend/)          — HTTP API, uploads, PostgreSQL persistence
        ↓
Python FastAPI Simulation Service    — server.py (POST /simulate, GET /simulate/{id})
        ↓
AI Engine (app/)                     — content.py, engine.py, scoring.py, aggregation.py, report.py
        ↓
Groq / Ollama
```

### Running everything locally

**1. Python simulation service**

```bash
cp .env.example .env        # fill in GROQ_API_KEY or configure Ollama
pip install -e ".[dev]"
python server.py             # or: uvicorn server:app --reload --port 8000
```

- `GET  /health` — service health check
- `POST /simulate` — multipart upload (`video`, optional `seed`) → `{ simulationId, status }`
- `GET  /simulate/{simulationId}` — poll for `PENDING` / `PROCESSING` / `COMPLETED` / `FAILED` + the final `SimulationReport` once complete

**2. Express backend**

```bash
cd backend
cp .env.example .env        # set DATABASE_URL, PYTHON_SERVICE_URL=http://localhost:8000, etc.
npm install
npm run dev                  # or: npm start
```

The backend proxies uploads/status polling to the Python service (`backend/src/services/pythonClient.js`)
and persists simulation status/results to PostgreSQL (`backend/src/services/simulationService.js`), reading
`virality_score` straight out of the JSON report the Python service returns — it does not calculate it.

**3. Frontend**

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

### Testing

```bash
python -m pytest tests/ -v   # all Version-A AI/scoring/simulation tests
python main.py --benchmark   # offline Phase 5E scoring benchmark, no API key required
```
