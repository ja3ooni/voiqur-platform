---
phase: 02-stt
plan: "00"
subsystem: testing
tags: [pytest, stt, deepgram, mistralai, langdetect, xfail, wave-0]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: pytest.ini with asyncio_mode=auto, venv, conftest.py
provides:
  - Pytest-discoverable test scaffold for STT-01 through STT-05 (xfail stubs)
  - deepgram-sdk, mistralai, langdetect pinned in requirements.txt and installed
  - torch/torchaudio import guard in stt_agent.py for test-time importability
affects:
  - 02-stt plans that need STT test infrastructure
  - Any plan importing from src.agents (benefits from llm_agent IndentationError guard)

# Tech tracking
tech-stack:
  added:
    - deepgram-sdk>=3.1.0,<4.0
    - mistralai>=2.0.0
    - langdetect>=1.0.9
  patterns:
    - xfail stubs for Wave 0 test scaffolding (tests exist before implementation)
    - skipif on API-key-dependent tests to keep CI green without secrets

key-files:
  created:
    - kiro/voiquyr/tests/test_stt_agent.py
  modified:
    - kiro/voiquyr/requirements.txt
    - kiro/voiquyr/src/agents/stt_agent.py
    - kiro/voiquyr/src/agents/__init__.py

key-decisions:
  - "xfail stubs pattern: tests define contract before Wave 1/2 implementation wires real API calls"
  - "torch/torchaudio guarded with try/except in stt_agent.py — not installed in lean CI venv"
  - "deepgram-sdk pinned <4.0 — project uses v3 API surface (listen.asyncprerecorded.v(1).transcribe_file)"
  - "test_voxtral_fallback uses skipif for absent MISTRAL_API_KEY to avoid CI failure without secrets"
  - "agents/__init__.py broadened to except Exception for llm_agent — pre-existing IndentationError blocked collection"

patterns-established:
  - "Wave 0 scaffolding: write xfail test stubs before implementation exists"
  - "API-key-gated tests use @pytest.mark.skipif(not os.getenv(...)) to stay collectable"

requirements-completed: [STT-05]

# Metrics
duration: 3min
completed: 2026-03-17
---

# Phase 02 Plan 00: STT Test Scaffold & Dependencies Summary

**Pytest xfail test scaffold for STT-01..STT-05 with deepgram-sdk v3, mistralai, and langdetect pinned and installed**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-17T13:29:22Z
- **Completed:** 2026-03-17T13:32:30Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Replaced asyncio-script `test_stt_agent.py` with proper pytest module — 5 tests collected, 0 errors
- Pinned and installed deepgram-sdk>=3.1.0,<4.0, mistralai>=2.0.0, langdetect>=1.0.9 in venv
- All 5 test stubs show as xfail/skipped (exit code 0, no collection errors)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add STT dependencies to requirements.txt** - `0c5e1e1` (chore)
2. **Task 2: Rewrite test_stt_agent.py as pytest with xfail stubs** - `6121c74` (test)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified
- `kiro/voiquyr/requirements.txt` - Added deepgram-sdk, mistralai, langdetect pins
- `kiro/voiquyr/tests/test_stt_agent.py` - Rewritten as pytest xfail scaffold (5 test functions)
- `kiro/voiquyr/src/agents/stt_agent.py` - Guarded torch/torchaudio imports with try/except
- `kiro/voiquyr/src/agents/__init__.py` - Broadened except clause for llm_agent to catch SyntaxError

## Decisions Made
- Pinned deepgram-sdk to `<4.0` — the codebase uses v3 API surface (`listen.asyncprerecorded.v("1")`)
- Used `pytest.xfail()` call inside `test_full_stt_suite_passes` to force xfail even though the body trivially passes
- `test_voxtral_fallback` uses `@pytest.mark.skipif(not os.getenv("MISTRAL_API_KEY"))` — test is collectable but skipped in envs without the key

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] numpy not installed in venv**
- **Found during:** Task 2 (test collection)
- **Issue:** `import numpy as np` at test module level caused ModuleNotFoundError
- **Fix:** Ran `.venv/bin/pip install numpy`
- **Files modified:** None (venv only)
- **Verification:** Test collection succeeded
- **Committed in:** 6121c74 (Task 2 commit — venv state, not tracked in git)

**2. [Rule 3 - Blocking] torch/torchaudio not installed, blocking stt_agent.py import**
- **Found during:** Task 2 (test collection)
- **Issue:** `import torch` / `import torchaudio` at top of stt_agent.py caused ModuleNotFoundError, preventing `from src.agents.stt_agent import VoxtralModelManager, AudioChunk, LanguageDetector`
- **Fix:** Wrapped torch/torchaudio imports in try/except ImportError with `_TORCH_AVAILABLE` flag
- **Files modified:** `kiro/voiquyr/src/agents/stt_agent.py`
- **Verification:** `pytest tests/test_stt_agent.py --co -q` reports 5 collected
- **Committed in:** 6121c74 (Task 2 commit)

**3. [Rule 3 - Blocking] Pre-existing IndentationError in llm_agent.py blocked agents package import**
- **Found during:** Task 2 (test collection)
- **Issue:** `src/agents/__init__.py` had `except ImportError` which does not catch `SyntaxError`/`IndentationError`. `llm_agent.py` line 953 has wrong indentation, causing the entire package to fail to load.
- **Fix:** Changed `except ImportError` to `except Exception` for the llm_agent import block in `__init__.py`
- **Files modified:** `kiro/voiquyr/src/agents/__init__.py`
- **Verification:** Collection proceeds past the llm_agent import error
- **Committed in:** 6121c74 (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (all Rule 3 blocking)
**Impact on plan:** All fixes unblocked test collection. No scope creep. The llm_agent IndentationError is pre-existing and deferred to a dedicated fix plan.

## Issues Encountered
- `test_full_stt_suite_passes` initially showed as XPASS because `assert True` always passes. Fixed by calling `pytest.xfail()` explicitly inside the function body to force the xfail status regardless.

## User Setup Required

External services require manual configuration before Wave 1/2 tests can pass:
- `DEEPGRAM_API_KEY` — Deepgram Console → Settings → API Keys → Create Key
- `MISTRAL_API_KEY` — Mistral La Plateforme → API Keys (enables `test_voxtral_fallback`)

## Next Phase Readiness
- Test scaffold is ready for Wave 1 implementation (02-01-PLAN.md)
- All three STT libraries importable in venv
- Pre-existing IndentationError in `llm_agent.py` (line 953) should be fixed in a dedicated plan — logged as known issue
- API keys needed for integration tests to move from xfail to passing

---
## Self-Check: PASSED

- FOUND: `.planning/phases/02-stt/02-00-SUMMARY.md`
- FOUND: `kiro/voiquyr/tests/test_stt_agent.py`
- FOUND: `kiro/voiquyr/requirements.txt`
- FOUND commit `0c5e1e1` (chore: STT deps)
- FOUND commit `6121c74` (test: xfail stubs)

---
*Phase: 02-stt*
*Completed: 2026-03-17*
