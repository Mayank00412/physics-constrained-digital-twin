# Architecture

- `backend/physics/engine.py`: deterministic SI-unit simulator, configurable faults, healthy expected-power engine.
- `backend/datasets/`: synthetic run-grouped CSV pipeline, official-source downloader, integrity and signal preprocessing.
- `backend/ai/models.py`: healthy-only detectors, physics-constrained neural training, persistence of preprocessors/checkpoints, offline metrics.
- `backend/diagnostics/`: interpretable component evidence; supervised classifier lives with the model suite.
- `backend/energy/`: baseline-relative energy integration.
- `backend/database/`: SQLAlchemy/SQLite telemetry samples, alerts, experiment records.
- `backend/api.py`: validated commands, managed worker jobs, runtime state and WebSocket broadcast.
- `frontend/`: React/TypeScript/Vite, Recharts, responsive CSS, synthetic source labels and model availability state.
- `scripts/`: dataset generation, multi-seed comparisons, public data management and recording-grouped evaluation.

Runtime owns one twin and one energy accumulator. A background asyncio task advances physical dt at wall-clock dt. Training runs in a single-worker executor; the active suite is swapped only after successful training/evaluation. WebSocket clients receive the latest observation, while the browser also polls model/job state. The in-memory history holds 3600 samples; SQLite persists every tenth sample and all generated alert events. Reset clears the current live session while database records remain available for research provenance. Restart begins a fresh live session and restores active trained checkpoints.

The browser uses same-origin `/api` and `/ws`, proxied by Vite during development and nginx with Compose. No cloud dependency exists at runtime.
