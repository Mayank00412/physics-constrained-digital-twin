# Implementation plan

Build a local React/Vite dashboard backed by FastAPI, SQLite, a deterministic fixed-step simulator, and offline scikit-learn/PyTorch training.

1. Validate power balance, gearbox transformations, sensor isolation, and simulation state transitions.
2. Generate reproducible run-grouped train/validation/test/OOD partitions.
3. Train physics, Isolation Forest, autoencoder, fusion, and physics-regularized models; save real evaluations and checkpoints.
4. Add interpretable and supervised localization, energy integration, persisted telemetry, managed jobs, and WebSocket streaming.
5. Build eight dashboard views using live API data; validate types/build and API integration.
6. Add official-source public data workflows, experiment configuration, documentation, and deployment files.

Research boundary: synthetic energy estimates are relative to a calibrated healthy model, not verified savings. Public vibration data validate vibration diagnostics separately. No hidden efficiency, severity, component, or fault label enters inference features.
