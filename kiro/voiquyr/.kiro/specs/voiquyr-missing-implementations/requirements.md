# Requirements Document

## Introduction

The Voiquyr platform was assessed as ~55% complete in April 2026. Tasks 1–17 in the existing `euvoice-ai-platform` spec were marked complete, but a code analysis revealed that the implementations are stubs, mocks, or placeholders. No real phone call can be made through the platform today: the STT pipeline returns mock transcripts, the LLM returns hardcoded responses, the TTS synthesises sine waves, and the telephony layer never bridges audio to the voice pipeline. Billing is disconnected from Stripe, the frontend is incomplete, there are no developer SDKs, Kubernetes secrets contain `changeme` placeholders, there are no database migrations, and 42 modules have zero test coverage.

This document captures the concrete, testable requirements for replacing every stub with a real implementation — the minimum work needed for the platform to function end-to-end as described in its own documentation.

---

## Glossary

- **Voice_Pipeline**: The sequential chain STT → LLM → TTS that converts incoming audio into spoken responses.
- **STT_Agent**: The Speech-to-Text component responsible for transcribing audio to text using a real provider (Deepgram Nova-3 or Mistral Voxtral).
- **LLM_Agent**: The language model component responsible for generating conversational responses using a real provider (Mistral API or local Ollama).
- **TTS_Agent**: The Text-to-Speech component responsible for synthesising audio from text using a real provider (ElevenLabs Flash or Piper TTS).
- **Call_Controller**: The orchestration component that bridges telephony audio to the Voice_Pipeline and back.
- **Telephony_Bridge**: The integration layer connecting Twilio HTTP calls and/or Asterisk AudioSocket to the Call_Controller.
- **Billing_Engine**: The UCPM (Unified Cost Per Minute) billing component that records usage and charges customers via Stripe.
- **Command_Center**: The React/MUI frontend application used by operators to log in, monitor calls, and configure agents.
- **Python_SDK**: The pip-installable `voiquyr` Python package that wraps the platform API.
- **TypeScript_SDK**: The npm-installable `voiquyr` TypeScript/JavaScript package that wraps the platform API.
- **Quickstart**: The "first call in 5 minutes" developer guide that walks a new user from zero to a working call.
- **Alembic**: The database migration tool used to manage PostgreSQL schema changes.
- **CI_Pipeline**: The GitHub Actions continuous integration pipeline that runs tests and validates builds on every commit.
- **Prometheus_Scraper**: The Prometheus metrics endpoint that exposes platform telemetry for scraping.
- **Sealed_Secrets**: The Kubernetes secret management mechanism that replaces plaintext `changeme` placeholder values.
- **WebRTC_Demo**: The browser-based voice demo embedded on the landing page that lets visitors speak to a Voiquyr agent without signing up.
- **UCPM**: Unified Cost Per Minute — the single per-minute rate that bundles STT, LLM, and TTS costs.
- **Mock**: A stub implementation that returns hardcoded or synthetic data instead of calling a real provider.

---

## Requirements

### Requirement 1: Real Speech-to-Text Integration

**User Story:** As a platform operator, I want the STT_Agent to call a real speech recognition provider, so that callers' speech is accurately transcribed instead of returning hardcoded mock text.

#### Acceptance Criteria

1. WHEN an audio stream is received by the STT_Agent, THE STT_Agent SHALL send the audio to the configured provider (Deepgram Nova-3 or Mistral Voxtral) and return a real transcript string within 500ms of utterance end.
2. WHEN the environment variable `DEEPGRAM_API_KEY` is set, THE STT_Agent SHALL use Deepgram Nova-3 streaming transcription as the primary provider.
3. WHEN `DEEPGRAM_API_KEY` is absent and `MISTRAL_API_KEY` is set, THE STT_Agent SHALL fall back to Mistral Voxtral transcription without crashing.
4. IF the STT provider returns an error or times out after 5 seconds, THEN THE STT_Agent SHALL log the error with provider name and request ID, and return a structured error response to the Call_Controller.
5. THE STT_Agent SHALL contain zero code paths that return a hardcoded or randomly generated transcript string.
6. WHEN Arabic and English are mixed in a single utterance, THE STT_Agent SHALL produce a transcript with word-level language identification and achieve a Word Error Rate below 15% on Levantine Arabic + English mixed audio.
7. FOR ALL valid audio inputs, encoding the audio as PCM 16kHz mono and sending it to the STT_Agent SHALL produce a non-empty transcript string (round-trip property).

---

### Requirement 2: Real Large Language Model Integration

**User Story:** As a platform operator, I want the LLM_Agent to call a real language model API, so that agents generate contextually appropriate responses instead of returning hardcoded mock text.

#### Acceptance Criteria

1. WHEN a transcript is received by the LLM_Agent, THE LLM_Agent SHALL send the transcript and conversation history to the configured provider (Mistral API or local Ollama) and return a real generated response.
2. WHEN the environment variable `MISTRAL_API_KEY` is set, THE LLM_Agent SHALL use the Mistral Small API as the primary provider.
3. WHEN `MISTRAL_API_KEY` is absent and a local Ollama endpoint is configured, THE LLM_Agent SHALL route inference to the local Ollama instance without crashing.
4. WHEN the LLM_Agent sends a request, THE LLM_Agent SHALL stream tokens back to the TTS_Agent as they are generated, beginning TTS synthesis on the first complete sentence before the full response is available.
5. IF the LLM provider returns an error or does not respond within 10 seconds, THEN THE LLM_Agent SHALL log the error and return a structured error response to the Call_Controller.
6. THE LLM_Agent SHALL contain zero code paths that return a hardcoded response string.
7. WHEN the same conversation history is submitted twice, THE LLM_Agent SHALL produce responses that are semantically consistent with the conversation context on both calls (idempotence of context, not of output).

---

### Requirement 3: Real Text-to-Speech Integration

**User Story:** As a platform operator, I want the TTS_Agent to call a real speech synthesis provider, so that agents speak with natural voices instead of producing sine waves or silence.

#### Acceptance Criteria

1. WHEN a text string is received by the TTS_Agent, THE TTS_Agent SHALL send the text to the configured provider (ElevenLabs Flash or Piper TTS) and return real synthesised audio bytes.
2. WHEN the environment variable `ELEVENLABS_API_KEY` is set, THE TTS_Agent SHALL use ElevenLabs Flash as the primary provider and return the first audio chunk within 200ms.
3. WHEN `ELEVENLABS_API_KEY` is absent, THE TTS_Agent SHALL use the locally installed Piper TTS engine and return the first audio chunk within 300ms.
4. IF the TTS provider returns an error or does not respond within 8 seconds, THEN THE TTS_Agent SHALL log the error and return a structured error response to the Call_Controller.
5. THE TTS_Agent SHALL contain zero code paths that generate sine wave audio, silence buffers, or any audio that is not produced by a real synthesis provider or engine.
6. WHEN a text string is synthesised and the resulting audio is transcribed by the STT_Agent, THE resulting transcript SHALL match the original text with a Word Error Rate below 10% (round-trip property).

---

### Requirement 4: End-to-End Voice Pipeline Integration

**User Story:** As a platform operator, I want the STT_Agent, LLM_Agent, and TTS_Agent to be connected in a working pipeline, so that audio input produces audio output through real providers with no mock data at any stage.

#### Acceptance Criteria

1. WHEN a raw audio buffer is submitted to the Voice_Pipeline, THE Voice_Pipeline SHALL return synthesised audio bytes produced by real providers within 2,000ms under normal network conditions.
2. THE Voice_Pipeline SHALL contain zero mock data at any stage — no hardcoded transcripts, no hardcoded LLM responses, and no synthetic audio.
3. WHEN the Voice_Pipeline processes a spoken English sentence, THE Call_Controller SHALL receive audio bytes that, when played back, contain a coherent spoken response to the input.
4. WHEN the Voice_Pipeline processes a spoken Arabic sentence, THE Call_Controller SHALL receive audio bytes that contain a coherent Arabic spoken response.
5. IF any stage of the Voice_Pipeline fails, THEN THE Call_Controller SHALL receive a structured error object identifying which stage failed (STT, LLM, or TTS) and the reason.
6. WHEN the Voice_Pipeline is invoked with inputs of varying length (1 word to 200 words), THE pipeline SHALL complete without crashing and return either a valid audio response or a structured error (metamorphic property: longer inputs may increase latency but must not cause crashes).

---

### Requirement 5: Twilio Telephony Integration

**User Story:** As a platform operator, I want Twilio HTTP calls to be fully implemented, so that inbound and outbound phone calls can be handled by the platform.

#### Acceptance Criteria

1. WHEN a Twilio webhook delivers an inbound call event to the platform, THE Telephony_Bridge SHALL accept the call, establish a media stream, and route audio to the Call_Controller.
2. WHEN the Call_Controller produces audio bytes, THE Telephony_Bridge SHALL stream those bytes back to the Twilio media stream in real time.
3. WHEN the environment variables `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_PHONE_NUMBER` are set, THE Telephony_Bridge SHALL be able to initiate an outbound call to a target phone number via the Twilio REST API.
4. IF a Twilio webhook request arrives with an invalid or missing signature, THEN THE Telephony_Bridge SHALL reject the request with HTTP 403 and log the rejection.
5. WHEN a call ends, THE Telephony_Bridge SHALL send a call-ended event to the Billing_Engine with the call duration in seconds.
6. THE Telephony_Bridge SHALL contain zero stub implementations that return hardcoded TwiML without processing real audio.

---

### Requirement 6: Asterisk AudioSocket Bridge

**User Story:** As a platform operator, I want the Asterisk AudioSocket integration to be fully implemented, so that calls routed through an on-premise Asterisk PBX are bridged to the Voice_Pipeline.

#### Acceptance Criteria

1. WHEN Asterisk establishes an AudioSocket connection to the platform, THE Telephony_Bridge SHALL accept the TCP connection and begin reading raw audio frames.
2. WHEN audio frames are received from the AudioSocket connection, THE Telephony_Bridge SHALL forward them to the Call_Controller for processing by the Voice_Pipeline.
3. WHEN the Call_Controller returns synthesised audio bytes, THE Telephony_Bridge SHALL write those bytes back to the AudioSocket connection in the correct frame format.
4. IF the AudioSocket connection is dropped unexpectedly, THEN THE Telephony_Bridge SHALL log the disconnection, clean up the session, and send a call-ended event to the Billing_Engine.
5. WHEN an Asterisk call is active, THE Telephony_Bridge SHALL maintain audio round-trip latency below 1,500ms measured from audio frame receipt to synthesised audio frame write.

---

### Requirement 7: Production Stripe Billing

**User Story:** As a business operations manager, I want the Billing_Engine to process real Stripe charges, so that customers are billed accurately for platform usage.

#### Acceptance Criteria

1. WHEN a call ends and the Billing_Engine receives a call-ended event, THE Billing_Engine SHALL calculate the UCPM charge for the call duration and create a real Stripe usage record via the Stripe API.
2. WHEN the environment variable `STRIPE_SECRET_KEY` is set to a live key, THE Billing_Engine SHALL use the Stripe production API endpoint; WHEN it is set to a test key, THE Billing_Engine SHALL use the Stripe test API endpoint.
3. WHEN a Stripe webhook delivers a payment event, THE Billing_Engine SHALL verify the webhook signature using `STRIPE_WEBHOOK_SECRET` before processing the event.
4. IF a Stripe API call fails, THEN THE Billing_Engine SHALL retry the call up to 3 times with exponential backoff and log each attempt.
5. THE Billing_Engine SHALL contain zero code paths that simulate a Stripe charge without calling the Stripe API.
6. WHEN a refund is triggered for a failed interaction, THE Billing_Engine SHALL issue a real Stripe refund via the Stripe API within 24 hours and record the refund reason.

---

### Requirement 8: Real-Time Exchange Rate Integration

**User Story:** As a business operations manager, I want the Billing_Engine to fetch live exchange rates, so that multi-currency invoices reflect accurate conversion rates.

#### Acceptance Criteria

1. WHEN the Billing_Engine calculates a charge in a non-EUR currency (AED, INR, SGD, JPY), THE Billing_Engine SHALL fetch the current exchange rate from a live rate API (European Central Bank or equivalent) rather than using a hardcoded rate.
2. WHEN the exchange rate API is unavailable, THE Billing_Engine SHALL use the most recently cached rate and log a warning indicating the rate age.
3. WHEN an exchange rate changes by more than 5% relative to the rate used in the previous billing cycle, THE Billing_Engine SHALL queue a 30-day advance notice notification to affected customers.
4. THE Billing_Engine SHALL contain zero hardcoded exchange rate constants used in production charge calculations.

---

### Requirement 9: Command Center Login and Authentication

**User Story:** As a platform operator, I want the Command Center login page to be fully functional, so that I can authenticate and access the dashboard.

#### Acceptance Criteria

1. WHEN a user submits the login form with valid credentials, THE Command_Center SHALL send the credentials to the authentication API, receive a JWT token, store it in a secure HTTP-only cookie or localStorage, and redirect to the dashboard.
2. WHEN a user submits the login form with invalid credentials, THE Command_Center SHALL display a descriptive error message without exposing internal error details.
3. THE Command_Center login form SHALL include all required MUI form fields (email input, password input, submit button) with client-side validation for empty fields and invalid email format.
4. WHEN the application starts, THE Command_Center SHALL read the WebSocket server URL from the environment variable `REACT_APP_WS_URL` rather than a hardcoded string.
5. IF the JWT token is expired or absent, THEN THE Command_Center SHALL redirect the user to the login page before rendering any protected route.

---

### Requirement 10: Real-Time Dashboard

**User Story:** As a platform operator, I want the Command Center dashboard to display live call statistics, so that I can monitor platform activity in real time.

#### Acceptance Criteria

1. WHEN the dashboard is loaded by an authenticated user, THE Command_Center SHALL establish a WebSocket connection to the platform and display the current count of active calls, total calls today, and average call duration.
2. WHEN a new call starts or ends, THE Command_Center SHALL update the active call count within 2 seconds without requiring a page refresh.
3. WHEN the WebSocket connection is lost, THE Command_Center SHALL display a visible reconnecting indicator and attempt to reconnect automatically with exponential backoff.
4. THE Command_Center dashboard SHALL not display hardcoded or static placeholder statistics.

---

### Requirement 11: Agent Configuration UI

**User Story:** As a platform operator, I want a working agent configuration interface in the Command Center, so that I can create and update voice agents without editing configuration files directly.

#### Acceptance Criteria

1. WHEN an authenticated user navigates to the agent configuration page, THE Command_Center SHALL display a list of existing agents fetched from the platform API.
2. WHEN a user fills in the agent configuration form and submits it, THE Command_Center SHALL send the configuration to the platform API and display a success or error message based on the API response.
3. WHEN a user edits an existing agent's configuration and saves, THE Command_Center SHALL send an update request to the platform API and reflect the updated values in the UI.
4. THE agent configuration form SHALL include fields for agent name, STT provider selection, LLM provider selection, TTS provider selection, and system prompt.

---

### Requirement 12: Python SDK

**User Story:** As a developer, I want a pip-installable Python SDK, so that I can integrate Voiquyr into my Python application without manually constructing HTTP or WebSocket requests.

#### Acceptance Criteria

1. THE Python_SDK SHALL be installable via `pip install voiquyr` from PyPI.
2. WHEN a developer instantiates the `VoiquyrClient` class with a valid API key, THE Python_SDK SHALL authenticate with the platform API and expose methods for initiating calls, listing agents, and streaming audio.
3. WHEN a developer calls `client.make_call(to="+1234567890", agent_id="...")`, THE Python_SDK SHALL initiate an outbound call via the platform API and return a call object with a call ID.
4. IF the platform API returns an error, THEN THE Python_SDK SHALL raise a typed `VoiquyrError` exception with the HTTP status code and error message.
5. FOR ALL valid API key strings, constructing a `VoiquyrClient` and calling `client.list_agents()` SHALL return a list object (round-trip property: create client → list agents → result is iterable).
6. THE Python_SDK SHALL include a README with a working code example that makes a real API call in under 20 lines of Python.

---

### Requirement 13: TypeScript/JavaScript SDK

**User Story:** As a developer, I want an npm-installable TypeScript SDK, so that I can integrate Voiquyr into my JavaScript or TypeScript application without manually constructing HTTP or WebSocket requests.

#### Acceptance Criteria

1. THE TypeScript_SDK SHALL be installable via `npm install voiquyr` from the npm registry.
2. WHEN a developer instantiates the `VoiquyrClient` class with a valid API key, THE TypeScript_SDK SHALL authenticate with the platform API and expose typed methods for initiating calls, listing agents, and streaming audio.
3. WHEN a developer calls `client.makeCall({ to: "+1234567890", agentId: "..." })`, THE TypeScript_SDK SHALL initiate an outbound call via the platform API and return a typed call object with a call ID.
4. IF the platform API returns an error, THEN THE TypeScript_SDK SHALL throw a typed `VoiquyrError` with the HTTP status code and error message.
5. THE TypeScript_SDK SHALL export TypeScript type definitions for all public interfaces and be usable in a TypeScript project without `@ts-ignore` suppressions.
6. THE TypeScript_SDK SHALL include a README with a working code example that makes a real API call in under 20 lines of TypeScript.

---

### Requirement 14: Developer Quickstart Guide

**User Story:** As a new developer, I want a "first call in 5 minutes" quickstart guide, so that I can make a real call through the platform within 5 minutes of reading the guide.

#### Acceptance Criteria

1. THE Quickstart SHALL be a single document that guides a developer from zero to a completed real call using only the Python_SDK or TypeScript_SDK and a valid API key.
2. WHEN a developer follows the Quickstart step by step on a machine with Python 3.10+ or Node.js 18+ installed, THE Quickstart SHALL result in a real call being initiated within 5 minutes.
3. THE Quickstart SHALL require no more than 3 terminal commands and no manual configuration file editing.
4. THE Quickstart SHALL include a `docker compose up` command that starts all required local services with pre-configured test credentials.
5. WHEN the `docker compose up` command completes, THE platform SHALL be reachable at `http://localhost:8000/health` and return HTTP 200.

---

### Requirement 15: Kubernetes Secrets Remediation

**User Story:** As a DevOps engineer, I want all Kubernetes secrets to contain real or properly managed values, so that the platform can be deployed to production without manual secret replacement.

#### Acceptance Criteria

1. THE platform's Kubernetes Helm charts SHALL contain zero occurrences of the string `changeme` in any secret value field.
2. WHEN the Helm chart is deployed, THE deployment SHALL use either Kubernetes Sealed Secrets or an External Secrets Operator to inject secret values from a secure store.
3. THE Helm chart README SHALL document the required secret keys and the process for populating them before deployment.
4. IF a required secret is missing at deployment time, THEN THE Helm chart SHALL fail with a descriptive error message identifying the missing secret key rather than deploying with an empty or placeholder value.

---

### Requirement 16: Database Migrations

**User Story:** As a DevOps engineer, I want Alembic database migrations to manage all schema changes, so that the database schema can be applied, upgraded, and rolled back reliably.

#### Acceptance Criteria

1. THE platform SHALL include an Alembic migration directory with at least one initial migration that creates all tables required by the application models.
2. WHEN `alembic upgrade head` is run against a fresh PostgreSQL database, THE command SHALL complete without errors and produce a schema that matches the application's ORM models.
3. WHEN `alembic downgrade -1` is run after `alembic upgrade head`, THE command SHALL revert the most recent migration without errors.
4. THE CI_Pipeline SHALL run `alembic upgrade head` as part of every build to verify migration integrity.
5. THE platform SHALL contain zero code that calls `Base.metadata.create_all()` in production startup paths; schema creation SHALL be managed exclusively through Alembic migrations.

---

### Requirement 17: CI/CD Pipeline

**User Story:** As a developer, I want a GitHub Actions CI/CD pipeline, so that every commit is automatically tested and validated before merging.

#### Acceptance Criteria

1. THE CI_Pipeline SHALL run on every pull request and push to the main branch.
2. WHEN the CI_Pipeline runs, THE CI_Pipeline SHALL execute the full unit test suite and fail the build if any test fails.
3. WHEN the CI_Pipeline runs, THE CI_Pipeline SHALL run `alembic upgrade head` against a test PostgreSQL instance and fail the build if migrations fail.
4. WHEN the CI_Pipeline runs, THE CI_Pipeline SHALL build the Docker image and fail the build if the image build fails.
5. WHEN all CI_Pipeline checks pass on the main branch, THE CI_Pipeline SHALL push the built Docker image to the configured container registry.
6. THE CI_Pipeline configuration SHALL be stored as a YAML file in `.github/workflows/` and require no manual steps to execute.

---

### Requirement 18: Prometheus Metrics

**User Story:** As a DevOps engineer, I want Prometheus metrics to be actively scraped from the platform, so that I can monitor system health and performance in Grafana.

#### Acceptance Criteria

1. THE platform SHALL expose a `/metrics` HTTP endpoint that returns Prometheus-format metrics.
2. WHEN a call is processed, THE Prometheus_Scraper SHALL record the following metrics: `voiquyr_calls_total` (counter), `voiquyr_call_duration_seconds` (histogram), `voiquyr_stt_latency_seconds` (histogram), `voiquyr_llm_latency_seconds` (histogram), `voiquyr_tts_latency_seconds` (histogram).
3. WHEN the Prometheus server scrapes the `/metrics` endpoint, THE endpoint SHALL respond within 500ms.
4. THE platform's Kubernetes deployment SHALL include a `ServiceMonitor` or Prometheus scrape annotation so that the Prometheus server discovers and scrapes the endpoint automatically.
5. THE platform SHALL contain zero metric registrations that are defined but never incremented during normal call processing.

---

### Requirement 19: Unit Test Coverage

**User Story:** As a developer, I want unit tests for all platform modules, so that regressions are caught automatically and the codebase can be refactored with confidence.

#### Acceptance Criteria

1. THE platform SHALL achieve a minimum of 70% line coverage across all Python modules as measured by `pytest --cov`.
2. WHEN `pytest` is run, THE test suite SHALL complete without errors or failures on a machine with the required environment variables set to test values.
3. THE 42 modules currently identified as having zero test coverage SHALL each have at least one unit test that exercises the module's primary function.
4. WHEN a module's primary function is a data transformation (e.g., audio format conversion, UCPM calculation, currency conversion), THE test suite SHALL include at least one property-based test using Hypothesis that verifies an invariant or round-trip property of that transformation.
5. THE CI_Pipeline SHALL fail if overall line coverage drops below 70%.

---

### Requirement 20: Integration and End-to-End Tests

**User Story:** As a QA engineer, I want integration and end-to-end tests that exercise the full call flow, so that regressions in the assembled system are caught before deployment.

#### Acceptance Criteria

1. THE platform SHALL include a database fixture suite that seeds a test PostgreSQL instance with the minimum data required to run integration tests (at least one tenant, one agent, and one user).
2. WHEN the integration test suite is run with real provider credentials, THE test suite SHALL execute a full call flow (audio in → STT → LLM → TTS → audio out) and assert that the output audio is non-empty and non-silent.
3. WHEN the integration test suite is run with `EU_DATA_RESIDENCY=true`, THE test suite SHALL assert that no API calls are made to endpoints outside the EU region.
4. WHEN the integration test suite is run, THE test suite SHALL verify that a Stripe test charge is created for a completed call and that the charge amount matches the expected UCPM calculation.
5. THE integration test suite SHALL be runnable with a single command (`make test-integration` or equivalent) documented in the project README.

---

### Requirement 21: WebRTC Landing Page Demo

**User Story:** As a prospective customer, I want to speak to a Voiquyr agent directly on the landing page without signing up, so that I can experience the platform's capabilities before committing to an account.

#### Acceptance Criteria

1. WHEN a visitor navigates to the platform's landing page, THE landing page SHALL display a "Try it now" button that initiates a WebRTC voice session with a live Voiquyr agent.
2. WHEN the visitor clicks the button and grants microphone permission, THE WebRTC_Demo SHALL establish a connection within 3 seconds and begin processing the visitor's speech through the real Voice_Pipeline.
3. WHEN the visitor speaks, THE WebRTC_Demo SHALL play back the agent's synthesised audio response within 2,000ms of the visitor finishing their utterance.
4. THE WebRTC_Demo SHALL function in Chrome, Firefox, and Safari without requiring any plugin or extension installation.
5. IF the visitor's browser does not support WebRTC, THEN THE landing page SHALL display a fallback message with a public demo phone number.

---

### Requirement 22: Public Demo Phone Number

**User Story:** As a prospective customer, I want to call a public phone number to speak with a Voiquyr demo agent, so that I can experience the platform from a real phone without any technical setup.

#### Acceptance Criteria

1. THE platform SHALL maintain at least one publicly listed phone number that connects callers to a live Voiquyr demo agent 24 hours a day, 7 days a week.
2. WHEN a caller dials the demo number, THE Telephony_Bridge SHALL answer the call within 5 seconds and route audio to the Voice_Pipeline.
3. WHEN the demo agent responds, THE caller SHALL hear synthesised speech produced by the real TTS_Agent within 2,000ms of finishing their utterance.
4. THE demo phone number SHALL be displayed on the platform's landing page and in the Quickstart documentation.
5. WHEN the demo agent's underlying Voice_Pipeline is unavailable, THE Telephony_Bridge SHALL play a pre-recorded fallback message rather than dropping the call silently.

---

### Requirement 23: Platform API Contract and Versioning

**User Story:** User Story: As an SDK and integration developer, I want a stable, well‑defined platform API, so that my integrations do not break when the backend evolves.

#### Acceptance Criteria
THE platform SHALL expose a versioned HTTP API under the base path /v1/ for all public endpoints used by the Python_SDK, TypeScript_SDK, Command_Center, and WebRTC_Demo.

ALL API responses that represent an error (HTTP 4xx and 5xx) SHALL use a common JSON envelope with fields code (machine‑readable string), message (human‑readable), and request_id (for log correlation).

ALL authenticated requests to the platform API SHALL use a single authentication scheme specified in the documentation (for example, Authorization: Bearer <API_KEY> or Authorization: Bearer <JWT>), and the scheme SHALL be identical across all SDKs and docs.

WHEN backward‑incompatible changes to any /v1/ endpoint are required, THE platform team SHALL introduce a new versioned base path (for example /v2/) and maintain /v1/ behavior unchanged for at least 90 days.

THE platform API reference documentation SHALL list all public endpoints, request/response schemas, and error codes, and SHALL be updated whenever new fields are added (additive changes) or new versions are introduced.

---

### Requirement 24: Security, Privacy, and Data Protection

**User Story:** User Story: As a security and compliance owner, I want clear security and data‑handling guarantees, so that customer conversations and billing data remain protected.

#### Acceptance Criteria
ALL external access to the platform API, Command_Center, WebRTC_Demo, and Telephony_Bridge webhooks (including Twilio webhooks) SHALL be served exclusively over HTTPS with TLS 1.2 or higher; HTTP (unencrypted) endpoints SHALL return redirects or errors and SHALL NOT process call or billing data.

ALL authentication secrets, API keys (Twilio, Stripe, Deepgram, Mistral, ElevenLabs), and database credentials SHALL be stored only in Kubernetes Sealed_Secrets or an External Secrets Operator–managed store and SHALL NOT appear in the source repository in plaintext.

THE platform SHALL implement Twilio webhook signature verification for all Twilio callbacks using the X-Twilio-Signature header and the account auth token, rejecting requests with invalid signatures with HTTP 403.

THE Billing_Engine and Stripe webhook handlers SHALL be idempotent: each Stripe event ID SHALL be processed at most once, and charge‑creating API calls SHALL use idempotency keys to prevent duplicate charges under retry conditions.

THE platform SHALL implement configurable data retention policies such that raw audio, transcripts, and LLM prompts/responses can be purged after a tenant‑defined retention period, and test fixtures SHALL verify that purging removes data from both primary tables and associated logs or search indices.

WHEN EU_DATA_RESIDENCY=true is set, THE platform SHALL route STT, LLM, and TTS requests only to EU‑hosted endpoints for providers that support EU regions, and SHALL block or fail fast on non‑EU endpoints, logging the attempted region for audit purposes.

---

### Requirement 25: Service Level Objectives and Backpressure

**User Story:** User Story: As a platform SRE, I want explicit SLOs and overload behavior, so that we can monitor quality and protect the system under high load.

#### Acceptance Criteria
THE platform SHALL define and document the following Service Level Indicators (SLIs):

api_availability: proportion of successful HTTP requests (2xx) to /v1/* endpoints,

voice_pipeline_latency: end‑to‑end time from audio frame receipt to first TTS audio frame,

error_rate: proportion of calls ending in structured errors vs successful completions.

THE platform SHALL target the following minimum SLOs over a rolling 30‑day window:

99.5% availability for /v1/* API endpoints,

95% of voice turns (from end of caller utterance to first agent audio frame) completing in under 1,500ms for telephony and WebRTC calls.

WHEN concurrent active calls exceed a configurable threshold (for example, 80% of provisioned capacity), THE platform SHALL apply backpressure by rejecting new API call initiation requests with HTTP 429 (Too Many Requests) and a retry‑after hint, while preserving in‑progress calls.

THE Prometheus /metrics endpoint SHALL expose SLIs needed to compute these SLOs (including counters for successful vs failed requests, and histograms for voice pipeline latency), and the platform SHALL provide example Grafana dashboards that visualize SLO burn rates.

WHEN the platform is operating in a degraded state (for example, a provider outage or internal dependency failure), THE Call_Controller SHALL prefer explicit, fast failure with structured errors over hanging requests, and the Command_Center dashboard SHALL surface a visible “Degraded” status with the affected component (STT, LLM, TTS, Telephony, Billing).


