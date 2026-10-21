# Implementation and verification status

## Completed

- Local FastAPI/SQLite service; eight React dashboard views; live WebSocket sensor data and simulation state controls.
- Deterministic motor/gearbox/belt dynamics, condition-dependent motor efficiency, transmission losses, thermal nodes, measurement noise, and nine healthy/fault scenarios.
- Reproducible synthetic CSV data: 108 runs × 180 steps = 19,440 rows per seed. Training, healthy calibration, test and OOD groups do not share run IDs.
- Actual trained physics, Isolation Forest, autoencoder, residual fusion, physics-regularized neural model, λ=0 ablation, and simulated component classifier checkpoints.
- Active seed-42 checkpoints plus independent seed-42/43/44 experiments, results JSON and comparison plots.
- Interpretable ambiguous localization, supervised localization, baseline-relative Wh integration, temporal persistence, managed training/evaluation jobs, and model-unavailable state.
- Official-source download discovery, guarded download/resume/hash metadata, safe ZIP extraction, numeric/MATLAB signal preprocessing and manifest-grouped public vibration evaluation scripts.
- Docker/Compose configuration, methodology, setup instructions, source-access notes and a research notebook.

## Actual verification

- Backend suite: **19 passed**, one upstream Starlette/httpx deprecation warning.
- Frontend: TypeScript check and Vite production build passed. Vite reports a large chart-vendor bundle warning; npm audit reported zero vulnerabilities at installation.
- Browser: confirmed connected dashboard, live Start control and changing sensor readings, gearbox fault injection, generated diagnostic alert, research metrics rendering, managed training job completion, Pause, and component inspection.
- Three-seed held-out test mean F1 (sample SD): physics 0.86197 (0.01927), Isolation Forest 0.02035 (0.00822), autoencoder 0.53670 (0.05066), hybrid 0.49732 (0.00705), residual fusion 0.88330 (0.01943). No hybrid superiority claim is supported.

## External limits and remaining research improvements

- No public dataset recording was downloaded or used to claim validation. CWRU's official index is accessible; NASA resource fetch timed out, and the historical Paderborn URL returned 404. Downloading requires current-source access review and explicit terms acknowledgement. The downloader and preprocessing workflows are implemented; NASA/Paderborn end-to-end import remains unverified without accessible publisher files.
- Docker configuration is supplied but Docker is unavailable in this environment, so container builds were not executed.
- Ideal servo, balanced supply, lumped thermal parameters and phenomenological vibration require calibration against a physical plant. The dataset is synthetic and short-duration. Public energy-savings validation, waveform models and uncertainty-calibrated diagnosis remain future research.
- λ is configurable and the best epoch is selected on healthy validation data; automated multi-λ search and independent plant uncertainty sweeps are not included.
- The application is intended for a local single-user session. Authentication, distributed simulation state, job cancellation, migration tooling and production telemetry retention are not implemented.
- The browser receives the latest sample at 4 Hz; the deterministic simulator runs at its configured dt. Browser history therefore samples the stream; integrated energy uses every simulation step.

## Reproduce or continue

Use README commands to start the API and UI, or `powershell -File scripts/start.ps1` with the installed short-path environment. Run `python -m scripts.experiment` to reproduce the three-seed comparisons. See docs/datasets.md before public downloads. All source and generated experiment outputs are preserved in this workspace.
