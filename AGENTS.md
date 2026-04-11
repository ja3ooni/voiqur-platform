# Repository Guidelines

## Project Structure & Module Organization
Treat the repository root as an umbrella workspace. Most product code lives in `kiro/voiquyr/`: `src/` contains the Python backend and agent framework, `tests/` contains backend tests, `frontend/` is the React dashboard, and `voiquyr-command-center/` contains a separate backend/frontend monitoring app. Client-specific business assets live in `voiquyr/`, while `.planning/` stores roadmap and phase artifacts rather than runtime code.

## Build, Test, and Development Commands
Run application commands from `kiro/voiquyr` unless noted otherwise.

`python -m venv .venv && source .venv/bin/activate` creates the backend environment.

`pip install -r requirements.txt` installs backend dependencies.

`python -m uvicorn src.api.main:app --reload` starts the FastAPI API locally.

`pytest` runs the backend suite defined by `pytest.ini`.

`pytest --cov=src --cov-report=term-missing` checks Python coverage.

`cd frontend && npm install && npm start` runs the dashboard app.

`cd frontend && npm test` runs the React test suite in CI mode.

`cd voiquyr-command-center/frontend && npm install && npm run dev` starts the Vite command center UI.

## Coding Style & Naming Conventions
Follow the existing style in each subsystem. Python uses 4-space indentation, snake_case modules, and type-aware, small functions grouped by domain (`src/api`, `src/core`, `src/agents`). React code uses PascalCase components and page folders such as `pages/Dashboard/Dashboard.tsx`; keep hooks and store code colocated under `frontend/src`. Use the linters already present in the frontend toolchain (`react-scripts` ESLint for the dashboard). No repository-wide formatter config is checked in, so avoid reformat-only churn.

## Testing Guidelines
Backend tests live in `kiro/voiquyr/tests` and follow `test_*.py`. `pytest.ini` sets `asyncio_mode = auto`, so prefer pytest for new async coverage even though some older tests still use `unittest`. Integration fixtures in `tests/conftest.py` read `TEST_DATABASE_URL` and `TEST_REDIS_URL`; if those services are unavailable, related tests skip gracefully. Target at least 80% coverage for new backend functionality.

## Commit & Pull Request Guidelines
Recent history follows scoped Conventional Commit prefixes such as `feat(02-stt-01): ...`, `docs(02-stt-00): ...`, and `test(02-stt-00): ...`. Keep that pattern: `<type>(<scope>): <imperative summary>`. Pull requests should describe the affected area, list the commands you ran, link the relevant phase or issue, and include screenshots for UI changes in either frontend.

## Security & Configuration Tips
Copy `kiro/voiquyr/.env.example` to `.env` for local work. Never commit secrets, live API keys, or production-ready Kubernetes secrets; the repo documents placeholder infrastructure values that must stay non-sensitive.
