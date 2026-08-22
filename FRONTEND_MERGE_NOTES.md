# Frontend merge notes

This project is the original **AIvirality-merged** backend (Python simulation
engine in `app/`, FastAPI in `server.py`, Express API in `backend/`) unchanged,
with a new **frontend** rebuilt from the `virality-simulator` design (network
graph, round timeline, persona detail panel) wired to the real API instead of
mock data.

## What changed vs. the two source projects

- `backend/`, `app/`, `main.py`, `server.py`, `tests/`, `docs/` — **untouched**,
  copied as-is from AIvirality-merged. This is still the authoritative
  simulation logic.
- `frontend/` — replaced:
  - Design system (Tailwind tokens, fonts, panel/paper/ink palette) and all
    visual components (`Header`, `InputSection`, `SpreadSection`,
    `NetworkGraph`, `AgentNode`, `NodeTooltip`, `AgentDetailPanel`,
    `GraphLegend`, `Timeline`, `VerdictSection`, `MetricCard`, `Footer`) are
    ported from `virality-simulator`.
  - `src/lib/api.js` — real API client (upload video, poll simulation status,
    fetch history), replacing the mock generator's non-existent network layer.
  - `src/lib/runAdapter.js` — converts a real `SimulationReport` (rounds,
    persona reactions, completion rates, AI-written reasoning) into the exact
    node/edge graph shape the visual components expect. **The graphs are
    driven entirely by real simulation output**, not randomly generated data.
  - `src/data/personas.js` — a read-only JS mirror of the 18 real persona
    archetypes in `app/personas/definitions.py`, used only to label nodes
    with a human-readable name/interests/personality; all reaction data
    (watch/like/comment/share, completion rate, reasoning) still comes from
    the backend.
  - `src/hooks/useSimulation.js` — replaces the mock's `setTimeout`-driven
    fake generator with real upload + polling against
    `POST/GET /api/simulations`, then plays the same round-by-round reveal
    animation once the real result has arrived.
  - `src/components/HistorySection.jsx` — new; lists persisted simulations
    from Postgres and lets you reload one into the graph.
  - `InputSection`/`DemographicPanel`/`PopulationControl` were adapted: the
    "population" and "demographic" pre-run controls from the mock don't exist
    in the real engine (round sizes are fixed at 15 → 30 → 60, and target
    audience is auto-detected from the video, not typed in). These now show
    real, functional equivalents: an optional reproducible **seed** field,
    the actual fixed round-size sequence, and the auto-detected target
    audience once analysis completes.

## Running it

Same as the original AIvirality-merged README: start the Python service
(`server.py`, port 8000), the Express API (`backend/`, port 4000), then the
frontend:

```bash
cd frontend
npm install
npm run dev
```

`frontend/.env.example` already points `VITE_API_URL` at
`http://localhost:4000/api`, matching the Express API's default port and CORS
origin (`http://localhost:5173`).

The production build was verified with `npm run build` (Vite) prior to
packaging.
