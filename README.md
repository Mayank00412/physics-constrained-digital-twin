# AXIOM — Physics-constrained industrial digital twin

Local research application for an electric motor → 15:1 gearbox → conveyor → load. FastAPI/SQLite streams deterministic synthetic telemetry into an eight-view React dashboard. No paid services or hardware are required.

## Install and run

Python 3.11+ and Node 22+ are required. Run commands from this repository root. On Windows, use a **short environment path** to avoid MAX_PATH failures with scientific packages.

`requirements.lock.txt` and `frontend/package-lock.json` record the tested dependency versions. Use `pip install -r requirements.lock.txt` and `npm.cmd ci --prefix frontend` for exact dependency reproduction on compatible platforms.

```powershell
py -3.11 -m venv C:\twin-env
C:\twin-env\Scripts\python.exe -m pip install -r requirements.txt
npm.cmd install --prefix frontend
C:\twin-env\Scripts\python.exe -m uvicorn backend.api:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
npm.cmd run dev --prefix frontend
```

Open http://localhost:5173. API documentation: http://127.0.0.1:8000/docs. Start the simulation on Overview or Digital Twin. Change load/speed and apply; inject faults on Digital Twin. Dataset & Model Management starts managed training/evaluation jobs. An untrained installation displays no fabricated anomaly predictions.

This workspace was verified with the environment at `C:\Users\mayan\Documents\ChatGPT\twin-env`. Substitute that path for `C:\twin-env` to use the installed environment.

Linux/macOS: `python3 -m venv .venv`, `.venv/bin/python -m pip install -r requirements.txt`, then use `.venv/bin/python` for the commands above.

## Reproduce experiments

```powershell
C:\twin-env\Scripts\python.exe -m scripts.generate --runs 108 --steps 180 --seed 42
C:\twin-env\Scripts\python.exe -m scripts.experiment --config experiments/configs/default.yaml
C:\twin-env\Scripts\python.exe -m pytest backend/tests -q
npm.cmd run build --prefix frontend
```

The experiment command trains three independent seeds, saves checkpoints and real test/OOD metrics, and exports PNG comparisons with sample standard deviation. API training saves the active model to `models/` and results to SQLite and `experiments/results/latest.json`. CLI multi-seed experiments save separate model versions under `models/seed-N/`.

## Public datasets

No public recording is silently replaced with synthetic measurements. Review access terms before downloading. Files over 50 MiB or with unknown size require an explicit flag.

```powershell
C:\twin-env\Scripts\python.exe -m scripts.public_data --discover-cwru
C:\twin-env\Scripts\python.exe -m scripts.public_data --url OFFICIAL_HTTPS_FILE_URL --output data/raw/cwru/recording.mat --accept-terms
C:\twin-env\Scripts\python.exe -m scripts.public_data --preprocess data/raw/cwru/recording.mat
C:\twin-env\Scripts\python.exe -m scripts.public_evaluate data/processed/manifest.csv
```

Use `--approve-large` only after reviewing the printed size; `--sha256 PUBLISHER_HASH` verifies an available publisher hash. Otherwise the tool records a local SHA256 without claiming publisher authenticity. Resume uses HTTP Range/ETag where available. MATLAB DE channels are auto-selected only when unambiguous; use `--channel` otherwise. ZIP extraction rejects path traversal and symlinks. Text vibration recordings and MATLAB arrays are supported; nested Paderborn structures need explicit export to a numeric channel first.

Official sources and current access status are recorded in [docs/datasets.md](docs/datasets.md). Public evaluation requires an explicit publisher-derived recording manifest with `path,label,split` (and optional `channel`). Never split windows from the same recording across train and test.

## Deployment

`docker compose up --build` exposes the dashboard at http://localhost:8080 and API at http://localhost:8000. Docker execution is optional and requires a working Docker installation. This is a local single-user research service: bind to loopback; authentication and multi-user isolation are outside this implementation.

See [research methodology](docs/methodology.md), [architecture](docs/architecture.md), and [verification/progress](docs/progress.md) for assumptions and actual validation status.
