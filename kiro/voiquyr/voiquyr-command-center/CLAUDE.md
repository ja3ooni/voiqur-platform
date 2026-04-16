# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

The Voiquyr Command Center is a standalone monitoring and operations app for the Voiquyr Voice AI platform. It is separate from the main platform (`kiro/voiquyr/`) and consists of two independent sub-apps that can run together or separately.

## Commands

### Frontend (from `frontend/`)
```bash
npm install          # first time only
npm run dev          # Vite dev server on port 3000 — requires GEMINI_API_KEY in .env.local
npm run build        # production build
npm run preview      # preview production build
```

### Backend (from `backend/`)
```bash
pip install -r requirements.txt   # first time only
uvicorn main:app --reload          # dev server on port 8000
```

### Docker (from repo root)
```bash
docker compose up    # runs orchestrator + redis together
```

## Environment Variables

**Frontend** — create `frontend/.env.local`:
```
GEMINI_API_KEY=your_key
```

**Backend** — set in environment or `.env`:
```
DEEPGRAM_API_KEY=
OPENAI_API_KEY=
ELEVENLABS_API_KEY=
REDIS_URL=redis://localhost:6379
```

## Architecture

### Frontend (`frontend/`)

React 19 + TypeScript + Vite. No state management library — all state is local `useState`. Tailwind CSS via inline classes (dark slate theme throughout). Charts via `recharts`, icons via `lucide-react`.

**Routing** is tab-based, handled by `App.tsx` with a `activeTab` string. There is no React Router.

```
App.tsx              ← tab switcher
components/
  Layout.tsx         ← sidebar nav + tab bar shell
  MetricCard.tsx     ← reusable stat card
pages/
  Dashboard.tsx      ← latency charts + region status + event log
  FlashSimulator.tsx ← interactive demo of speculative LLM inference (Flash Mode™)
  Config.tsx         ← placeholder for SIP trunks / compliance / deployment / settings tabs
constants.ts         ← MOCK_LATENCY_DATA, MOCK_SIP_TRUNKS, REGIONS_CONFIG (all mock data)
types.ts             ← Region, CallStatus, LatencyMetric, SipTrunk, SimulationStep
```

**Important:** The frontend currently runs entirely on mock data (`constants.ts`). There is no live API integration yet — that is Phase 2 work.

### Backend (`backend/`)

FastAPI application with `uvicorn`. Entry point is `main.py`. Initialises a database on startup via `app/core/database.py`.

```
main.py                        ← FastAPI app, CORS, lifespan, router mounts
app/
  core/
    auth.py                    ← JWT/API key auth
    config.py                  ← pydantic-settings config (reads env vars)
    database.py                ← DB init (async)
  services/
    deepgram_service.py        ← Deepgram Nova-2 STT integration
    llm_service.py             ← OpenAI LLM integration
  websockets/
    twilio_handler.py          ← Twilio Media Streams WebSocket handler
```

Routers are registered at:
- `GET /api/health` — health check
- `POST /api/auth/...` — authentication
- `GET|POST /api/sip-trunks/...` — SIP trunk management
- `GET|POST /api/calls/...` — call records

The real-time voice pipeline flows: **Twilio WebSocket → Deepgram STT → OpenAI LLM → ElevenLabs TTS → Twilio WebSocket**.

### Docker Compose

`docker-compose.yml` runs two services:
- `orchestrator` (the FastAPI backend) — port 9000 in production mode
- `redis` — port 6379, used as a low-latency log buffer before writing to persistent storage

## Key Concepts

**Flash Mode™ (Speculative Inference)** — the FlashSimulator page demonstrates this: when STT confidence crosses 0.85 and the sentence looks grammatically complete, a speculative LLM request is fired before the user finishes speaking. If the user changes their mind (barge-in / context shift), the speculative request is cancelled via a cancellation token and a fresh request is sent with the corrected transcript. This reduces TTFT by ≥80ms when speculation succeeds.

**Regions** — five edge regions are modelled (`EU Frankfurt`, `ME Bahrain`, `Asia Mumbai`, `Asia Singapore`, `Asia Tokyo`). Only Frankfurt, Bahrain, and Mumbai are currently active. The UI in `constants.ts` hard-codes the active flags.

## Phase Status

- **Phase 1 (MVP):** Core FastAPI skeleton, SIP trunk models, auth, EU (Frankfurt) deployment config, dashboard UI with mock data — largely scaffolded.
- **Phase 2:** Live backend integration for the frontend, Middle East region, Arabic dialect support.
- **Phase 3:** Asia regions, production Flash Mode implementation.
