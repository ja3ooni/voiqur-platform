# Voiquyr Master Execution Plan

**Version:** 1.0  
**Date:** April 2026  
**Author:** Compiled from PRD, competitive research, infrastructure research, marketing research, SEO research, and gaps analysis  
**Status:** LIVING DOCUMENT — update after each sprint

---

## Executive Summary

Voiquyr is an EU-native, open-source voice AI platform targeting regulated industries in Europe, Middle East, and Asia that cannot use US-based platforms (Vapi, Retell, Bland) due to GDPR, CLOUD Act exposure, and regional data sovereignty requirements.

**Platform status:** ~55% complete. Phase 1 (Foundation) shipped March 2026. The STT → LLM → TTS pipeline, telephony integration, billing, frontend, and production infrastructure are all pending.

**Market opportunity:** The Voice AI Agents market is growing from $2.4B (2024) to $47.5B by 2034 at 34.8% CAGR. $2.1B in VC was deployed into voice AI in 2024 alone. No EU-native platform exists as a credible competitor to Vapi.

**Hardware inventory:** Mac Mini M4 16GB (always-on inference), PC 40GB RAM (on-demand heavy workloads), MacBook Air M5 16GB (dev/testing), Hetzner CX32 8GB (ERPNext, cloud VPS).

**Pilot customers waiting:** MedGulf Insurance (Jordan, inbound claims + Arabic/English), Oman LNG via Shape Digital (enterprise voice automation), InfraTechton Aqaba (voice knowledge base).

**Positioning:** "The open-source, EU-native Vapi alternative" — the Supabase playbook applied to voice AI.

**Immediate critical path:** Complete voice pipeline (Sprint 1–2) before any marketing or community investment. Nothing else matters until one real phone call works end-to-end.

---

## Table of Contents

- [Part 1: Infrastructure Architecture](#part-1-infrastructure-architecture-with-alternatives)
- [Part 2: Product Roadmap (Miro-Ready)](#part-2-product-roadmap-miro-ready-format)
- [Part 3: ClickUp Project Structure](#part-3-clickup-project-structure)
- [Part 4: Local Dev Setup Guide](#part-4-local-dev-setup-guide-macbook-air-m5)
- [Part 5: GTM Strategy](#part-5-gtm-strategy)
- [Part 6: SEO & AI Search Strategy](#part-6-seo--ai-search-engine-strategy)
- [Part 7: Open Questions & Decisions Needed](#part-7-open-questions--decisions-needed)

---

## Part 1: Infrastructure Architecture (with Alternatives)

### Current Hardware Inventory

| Device | Role | RAM | CPU | Always On? | Notes |
|--------|------|-----|-----|-----------|-------|
| Mac Mini M4 | Primary inference server | 16 GB unified | Apple M4 | Yes | CoreML/Metal acceleration; best self-hosted STT/LLM/TTS |
| PC (home) | Heavy Docker workloads | 40 GB | x86 | On-demand | Batch jobs, fine-tuning, large model testing |
| MacBook Air M5 | Dev / testing | 16 GB unified | Apple M5 | No | Development laptop; never in production path |
| Hetzner CX32 | Cloud VPS (ERPNext) | 8 GB | 4 vCPU Intel | Yes | Currently at capacity with ERPNext Docker |

**Key constraint:** Hetzner CX32 is effectively full. ERPNext Docker uses 5–6 GB of the 8 GB. Adding any voice AI workload to the CX32 is not viable without an upgrade.

---

### Voice Pipeline Architecture Options

All four options are presented for evaluation. No single recommendation — choose based on your priorities for cost, latency, data sovereignty, and operational complexity.

---

#### Option A: Full Self-Hosted on Mac Mini M4

| Component | Technology | Notes |
|-----------|-----------|-------|
| STT | whisper.cpp + CoreML (`base` or `medium` model) | 0.5s latency, 18–20x real-time factor |
| LLM | Ollama + Mistral 7B or Qwen2.5:7B (Q4_K_M) | 15–26 tokens/sec on M4 16GB |
| TTS | Piper TTS | 50–150ms per sentence, 900+ voices, 40+ languages |
| Telephony | Asterisk on Hetzner CX42 | AudioSocket module for real-time audio streaming |
| Orchestration | LiveKit Agents | Self-hosted real-time voice orchestration |
| Post-call workflows | n8n | CRM sync, SMS, calendar booking, logging |

**Monthly cost:** ~€3–5 (electricity only)  
**End-to-end latency:** 800ms–1,500ms  
**Concurrency:** 1–3 simultaneous calls on M4 16GB (limited by unified memory)

**Memory budget on M4 16GB (all services running simultaneously):**
- OS + overhead: ~2–3 GB
- whisper.cpp (base/medium): ~0.14–1.5 GB
- Mistral 7B Q4_K_M via Ollama: ~5–6 GB
- Piper TTS: ~200 MB
- PostgreSQL + Redis: ~500 MB
- LiveKit Agent: ~200 MB
- **Remaining:** ~4–6 GB ✅ Comfortable

**Pros:**
- Zero recurring API costs
- All data stays on-premises (maximum GDPR sovereignty)
- No internet dependency for inference
- Excellent for development and iteration
- Models improve as better quantizations are released

**Cons:**
- Higher latency (800ms–1.5s vs. 600–800ms for cloud)
- Voice quality gap vs. ElevenLabs (Piper is functional but not premium)
- Tied to home network uptime — single point of failure
- No Arabic-specific model without fine-tuning
- M4 concurrent call capacity limited to ~3 simultaneous

**STT model benchmarks on M4 (from [DEV Community M4 benchmark](https://dev.to/theinsyeds/whisper-speech-recognition-on-mac-m4-performance-analysis-and-benchmarks-2dlp)):**

| Model | Transcription time (10s audio) | Real-time factor | RAM |
|-------|-------------------------------|-----------------|-----|
| tiny | ~0.37s | 27x RT | 75 MB |
| base | ~0.54s | 18x RT | 140 MB |
| medium | ~0.50s (CoreML) | ~20x RT | 1.5 GB |
| large-v3-turbo | ~1.20s (CoreML) | ~8x RT | 1.5 GB |

**LLM benchmarks on M4 16GB (from [Reddit M4 Mac Mini test results](https://www.reddit.com/r/LocalLLaMA/comments/1gnefmi/mac_mini_m4_16gb_test_results/)):**

| Model | Tokens/sec | RAM | Conversational quality |
|-------|-----------|-----|----------------------|
| llama3.2:3b (Q8) | ~25 t/s | 3.5 GB | Excellent |
| Mistral 7B / llama3.1:8b (Q4_K_M) | ~15–21 t/s | 5–6 GB | Good |
| Qwen2.5:7B (Q4_K_M) | ~26 t/s | 5 GB | Excellent |
| llama2:13b | ~13–14 t/s | 8–9 GB | Usable |

---

#### Option B: Full Cloud APIs

| Component | Technology | Cost Reference |
|-----------|-----------|----------------|
| STT | Deepgram Nova-3 | $0.0077/min ([Deepgram pricing](https://deepgram.com/pricing)) |
| LLM | Mistral Small API | ~$0.10/M tokens input, $0.30/M tokens output ([Mistral pricing](https://pricepertoken.com/pricing-page/model/mistral-ai-mistral-large)) |
| TTS | ElevenLabs Flash | $0.05/1K chars, ~75ms latency ([ElevenLabs pricing](https://elevenlabs.io/pricing/api)) |
| Telephony | Asterisk on Hetzner (CX42) | Infrastructure cost only |
| Orchestration | LiveKit Agents or Pipecat | Self-hosted |

**Monthly cost (600 calls, ~10 min avg):** ~$12–15/month in API costs  
**End-to-end latency:** 600–800ms  
**Concurrency:** Limited only by API rate limits and Hetzner capacity

**Cost breakdown for 600 calls @ 10 min each (6,000 min/mo):**
- Deepgram Nova-3: 6,000 × $0.0077 = **$46.20/mo**
- ElevenLabs Flash: ~150 chars/response × 600 responses × $0.05/1K = **$4.50/mo**
- Mistral Small: 600 calls × ~500 tokens × $0.30/1M = **$0.09/mo**
- Twilio telephony (if used): 6,000 × ~$0.01/min = **$60/mo**
- **Total without Twilio:** ~$51/mo | **Total with Twilio:** ~$111/mo

**Pros:**
- Lowest operational complexity — no inference infrastructure to manage
- Highest voice quality (ElevenLabs) and STT accuracy (Deepgram)
- Best latency (600–800ms)
- Scales to any concurrency instantly
- Deepgram has EU region endpoints for GDPR compliance

**Cons:**
- Recurring cost scales directly with usage
- Data processed by third-party US-controlled infrastructure (even EU endpoints are CLOUD Act-affected companies)
- Provider outage = service outage
- ElevenLabs pricing rises significantly at volume

---

#### Option C: Hybrid — Dev Self-Hosted, Prod Cloud APIs

**Development environment (Mac Mini M4):** Full self-hosted stack
- whisper.cpp + CoreML + Ollama + Piper TTS
- Cost: Free (electricity only)
- Purpose: Development, testing, iteration — never in customer call path

**Production environment (Cloud APIs):**
- Deepgram Nova-3 + Mistral API + ElevenLabs Flash
- Cost: ~$12–20/mo for early pilot scale (pre-revenue)
- Purpose: Pilot customer calls, demos, MedGulf/Oman LNG/InfraTechton

**Monthly cost:** Free for dev; ~$12–20/mo for production  
**End-to-end latency:** Dev 800ms–1.5s; Prod 600–800ms  

**Pros:**
- Best of both worlds — free iteration, production quality when needed
- No changes to production if local config breaks
- Allows testing across both stacks for comparison
- Realistic path: start here, evaluate production costs at scale

**Cons:**
- Two separate configurations to maintain (env vars, Docker Compose files)
- Risk of subtle behavior differences between dev and prod pipelines
- Production still has cloud data residency concerns

---

#### Option D: Cloud STT + Self-Hosted LLM + Self-Hosted TTS (Cost-Optimized Hybrid)

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| STT | Deepgram Nova-3 | Best accuracy + streaming latency; EU endpoint available |
| LLM | Ollama (Mistral 7B or Qwen2.5:7B) on Mac Mini M4 | Inference stays on-premises; lowest cost |
| TTS | Piper TTS on Mac Mini M4 | Sub-150ms, free, 900+ voices |
| Telephony | Asterisk on Hetzner CX42 | |

**Monthly cost (6,000 min/mo):** ~$46.20 (Deepgram only)  
**End-to-end latency:** 600–900ms  
**Data residency:** STT audio leaves premises (Deepgram EU endpoint); LLM context and TTS stay local

**Pros:**
- Best balance of cost, latency, and data sovereignty
- Deepgram's streaming accuracy is significantly better than whisper.cpp for non-English (important for Arabic)
- LLM and TTS on-premises keeps conversation content private
- Lowest total cost at scale vs. full cloud (no ElevenLabs recurring cost)

**Cons:**
- STT audio still processed by a US-headquartered company (CLOUD Act risk, even on EU endpoints)
- Piper voice quality lower than ElevenLabs — may affect MedGulf pilot experience
- Requires Mac Mini M4 to remain always-on and reachable

---

#### Architecture Option Comparison Matrix

| Dimension | Option A: Full Self-Hosted | Option B: Full Cloud | Option C: Dev+Prod Hybrid | Option D: Cloud STT + Local LLM/TTS |
|-----------|---------------------------|---------------------|--------------------------|-------------------------------------|
| Monthly cost (6K min) | €3–5 | ~$111 (with Twilio) | Free dev / ~$20 prod | ~$46 |
| Latency (e2e) | 800ms–1.5s | 600–800ms | 600–800ms (prod) | 600–900ms |
| Voice quality | ★★★☆☆ | ★★★★★ | ★★★★★ (prod) | ★★★☆☆ |
| Data sovereignty | ✅ Full | ⚠️ US companies | ⚠️ US companies (prod) | ⚠️ STT only |
| Operational complexity | Medium | Low | Low-Medium | Medium |
| Concurrent calls | 1–3 | Unlimited | Unlimited (prod) | 1–3 (LLM/TTS bottleneck) |
| Arabic support | ⚠️ (whisper.cpp OK for Arabic) | ✅ Deepgram multilingual | ✅ (prod) | ✅ Deepgram |
| Dev cost | Free | Scales with use | Free | Scales (STT) |

---

### Hetzner Server Upgrade Options

**Current situation:** CX32 (€6.80/mo, 8 GB) is running ERPNext at near-capacity. Any voice AI workload requires upgrading.

#### Cloud VPS Options

| Model | vCPU | RAM | Storage | Price/mo | Verdict |
|-------|------|-----|---------|---------|---------|
| **CX32** (current) | 4 | 8 GB | 80 GB | ~€6.80 | Full — ERPNext at capacity |
| **CX42** | 8 | 16 GB | 160 GB | ~€16.40 | ✅ Recommended minimum upgrade — ERPNext + Asterisk + n8n |
| **CAX31** (ARM Ampere) | 8 | 16 GB | 160 GB | ~€12.49 | ✅ Cheaper than CX42; ARM64 runs Docker/Asterisk fine; no ML acceleration |
| **CAX41** (ARM Ampere) | 16 | 32 GB | 320 GB | ~€24.49 | Headroom for future growth; ARM64 |
| **CX52** | 16 | 32 GB | 320 GB | ~€32.40 | Intel shared; more compute than CAX41 |

**Note:** Hetzner increased prices ~30–35% on April 1, 2026. Prices above reflect post-increase rates. Sources: [Achromatic Hetzner comparison](https://www.achromatic.dev/blog/hetzner-server-comparison), [CostGoat pricing](https://costgoat.com/pricing/hetzner).

#### Dedicated Server Options (If Moving Full Pipeline to Hetzner)

| Model | CPU | RAM | Storage | GPU | Price/mo | Use Case |
|-------|-----|-----|---------|-----|---------|---------|
| AX41-NVMe | AMD Ryzen 5 3600 | 64 GB | 2×512 GB NVMe | None | €42.80 | Full self-hosted CPU inference; 5–8 t/s for 7B LLM — slow for real-time |
| **EX44** | Intel i5-13500 | 64 GB | 2×512 GB NVMe | None | €44.00 | Better CPU for inference; same price range |
| AX52 | AMD Ryzen 7 7700 | 64 GB | 2×1 TB NVMe | None | €64.00 | Higher throughput CPU inference |
| EX101 | Intel i9-13900 | 64 GB | 2×1.92 TB NVMe | None | €89.00 | Fast CPU inference (acceptable for 1–2 concurrent calls) |
| **GEX44** | Intel i5-13500 | 64 GB | 2×1.92 TB NVMe | RTX 4000 SFF Ada (20 GB) | €184 + €79 setup | GPU inference: ~50–80 t/s for 7B; real-time 1–5 concurrent calls |
| **GEX131** | Intel Xeon Gold 5412U | TBD | TBD | RTX PRO 6000 Blackwell (96 GB) | TBD (>€400) | Production GPU inference at scale |

**GEX44 notes:** RTX 4000 SFF Ada is power-limited to 70W (vs. standard RTX 4000). Suitable for 1–5 simultaneous voice calls with GPU-accelerated inference. Faster-whisper large-v3-turbo: ~0.5–1s per utterance. Mistral 7B: ~50–80 t/s. Source: [Hetzner GEX44 page](https://www.hetzner.com/dedicated-rootserver/gex44/).

**GEX131 notes:** RTX PRO 6000 Blackwell Max-Q with 96 GB GDDR7 ECC. Pricing TBD but expected >€400/mo. Would enable vLLM, larger models (34B+), and high concurrency. Source: [Hetzner GPU matrix](https://www.hetzner.com/dedicated-rootserver/matrix-gpu/).

#### Hetzner Decision Matrix

| Goal | Recommendation | Cost | Notes |
|------|---------------|------|-------|
| Minimum viable — ERPNext + Asterisk | CX42 | €16.40/mo | ERPNext + Asterisk + n8n + Redis comfortable |
| ERPNext + Asterisk + cheaper ARM | CAX31 | €12.49/mo | ARM64 fine for Docker workloads; no ML |
| Full cloud-hosted pipeline without home server | GEX44 dedicated GPU | €184 + €79 setup | GPU inference for 1–5 concurrent calls |
| Maximum future-proofing / enterprise scale | GEX131 (Blackwell) | >€400/mo | High concurrency, vLLM, 70B models |
| Separate telephony-only server | CX22 | ~€3.99/mo | Asterisk + Redis only; inference elsewhere |

---

### Telephony Options

#### Asterisk vs FreeSWITCH Comparison

| Dimension | Asterisk | FreeSWITCH |
|-----------|----------|------------|
| Architecture | Monolithic (single-thread media) | Modular, multi-threaded, event-driven |
| Concurrent calls (8-core VPS) | ~1,500–2,000 | ~3,000–5,000 |
| Memory per call | ~2–4 MB | ~1–2 MB |
| WebRTC support | Via PJSIP (works, needs config) | Via Sofia + Verto module (more polished) |
| SIP RFC compliance | Good | Excellent |
| AI/LLM integration | AGI, ARI, AMI (Python, Node.js) | ESL (Event Socket Library), Lua, JS |
| Real-time audio to AI | AudioSocket module (Asterisk-native) | mod_audio_stream |
| Docker support | Works, unofficial images | Works, official images available |
| Learning curve | Moderate (extensions.conf) | Steep (XML dialplan, ESL) |
| GUI ecosystem | FreePBX, VitalPBX (mature, large community) | FusionPBX (less polished) |
| Community size | Very large, broad | Smaller, telecom-specialist |
| Commercial backing | Sangoma | SignalWire |
| ERPNext integration | ✅ More connectors for Frappe/ERPNext | Limited |
| Best for | SMB PBX, IVR, modest AI voice calls | CPaaS, WebRTC, carrier-grade, AI at scale |

Sources: [DEV Community comparison](https://dev.to/sheerbittech/freeswitch-vs-asterisk-which-voip-platform-is-right-for-you-5gcn), [Samcom Technologies 2026 guide](https://www.samcomtechnologies.com/blog/asterisk-vs-freeswitch-in-2026-which-voip-platform-should-you-choose)

**For <500 concurrent AI calls:** Asterisk is recommended due to better documentation for AI integration, easier Docker deployment, ERPNext compatibility, and sufficient call capacity for current scale.

**Choose FreeSWITCH if:**
- You need >1,000 concurrent AI calls
- You need native browser-based WebRTC (Verto module)
- You are building a multi-tenant CPaaS product at carrier scale

**Kamailio:** Used as the SIP proxy layer in the BYOC adapter (P1-01). Sits in front of Asterisk/FreeSWITCH to handle SIP routing, load balancing, and carrier ingress. Not a replacement for either — it works with both.

---

### Real-Time Voice Orchestration Options

The real-time STT → LLM → TTS loop requires a dedicated orchestration layer. This is NOT a role for n8n (which is sequential and has 16–18s latency for multi-tool workflows).

| Option | Description | Best For | Complexity |
|--------|-------------|----------|------------|
| **LiveKit Agents** | Python-based real-time voice agent framework; integrates Deepgram, OpenAI, ElevenLabs; self-hostable | Self-hosted production deployments | Medium |
| **Pipecat** (by Daily) | Python framework for AI voice and video pipelines; composable pipeline model | Custom pipeline architectures | Medium |
| **Custom FastAPI + WebSocket** | Build your own WebSocket server with asyncio audio streaming | Full control; maximum flexibility | High |
| **Voiquyr's existing call_controller.py** | The platform's existing call controller (partially implemented) | Already in codebase — complete this first | Low (extend existing) |

**n8n's correct role:** Post-call workflows ONLY — never in the real-time path.

```
n8n: CORRECT usage
[Call ends] → [Asterisk AMI event webhook] → [n8n workflow]
                                                    ↙      ↓       ↘
                                             CRM      Calendar    Send SMS
                                             update   booking     transcript

n8n: INCORRECT usage
[Audio in] → [n8n STT node] → [n8n LLM node] → [n8n TTS node]
                    ← 16–18 second latency — unusable ←
```

Source: [n8n community thread](https://community.n8n.io/t/is-n8n-suitable-for-real-time-ai-voice-agent-orchestration-with-self-hosted-models-latency-concerns/278487)

---

### Architecture Diagram (ASCII)

**Recommended Architecture — Mac Mini M4 + Hetzner CX42 + Selective Cloud APIs:**

```
┌─────────────────────────────────────────────────────────────────┐
│  CALLERS / CLIENTS                                              │
│  Phone (PSTN) │ WebRTC Browser │ SIP Softphone │ WebSocket App │
└──────────────────────────┬──────────────────────────────────────┘
                           │ SIP / WebRTC / WebSocket
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  HETZNER CX42 (16 GB) — Cloud VPS (ERPNext region)            │
│  ─ ERPNext Docker (business operations)                        │
│  ─ Asterisk Docker (SIP/telephony gateway)                     │
│     └─ AudioSocket → routes audio to Mac Mini M4               │
│  ─ Kamailio (SIP proxy + BYOC adapter)                         │
│  ─ Twilio SIP trunk termination                                │
│  ─ n8n (post-call: CRM, SMS, calendar, logging)               │
│  ─ Redis (session state, pub/sub)                              │
└──────────────────────────┬──────────────────────────────────────┘
                           │ SIP / WebRTC / AudioSocket
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  MAC MINI M4 16GB (always-on, home/office)                     │
│                                                                 │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐          │
│  │  STT Agent  │──▶│  LLM Agent  │──▶│  TTS Agent  │          │
│  │  whisper.cpp│   │  Ollama     │   │  Piper TTS  │          │
│  │  + CoreML   │   │  Mistral 7B │   │  50–150ms   │          │
│  │  ~500ms     │   │  Qwen2.5:7B │   │             │          │
│  └─────────────┘   └─────────────┘   └─────────────┘          │
│         │                │                │                     │
│  Semantic VAD      Tool Calling      TTS Streaming             │
│  Code-Switch       Flash Mode        Voice Cloning             │
│  Language Det.     Dialog Mgr        Emotion Agent             │
│                                                                 │
│  ─ LiveKit Agent server (real-time voice orchestration)        │
│  ─ Voiquyr FastAPI backend (platform services)                 │
│  ─ PostgreSQL (primary database)                               │
│  ─ Redis (cache + queue)                                       │
└──────────────────────────┬──────────────────────────────────────┘
                           │ Selective API calls (STT or TTS override)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  CLOUD APIS (selective use — configurable per deployment)       │
│  ─ Deepgram Nova-3 (if whisper.cpp latency insufficient)       │
│    $0.0077/min; EU endpoint at eu.deepgram.com                 │
│  ─ ElevenLabs Flash (if voice quality > cost priority)         │
│    ~75ms; $0.05/1K chars                                       │
│  ─ Mistral API (fallback if Mac Mini is offline)              │
│    Mistral Small ~$0.30/1K calls                               │
└──────────────────────────┬──────────────────────────────────────┘
                           │ Heavy workloads only
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  HOME PC (40 GB RAM) — on-demand only                          │
│  ─ Docker workloads (model fine-tuning, batch jobs)            │
│  ─ faster-whisper batch transcription (CUDA if GPU present)    │
│  ─ Larger model testing (13B–34B via Ollama)                   │
│  ─ Dataset preparation for Arabic dialect fine-tuning          │
└─────────────────────────────────────────────────────────────────┘
```

**Latency budget breakdown (from [Introl voice AI infrastructure guide](https://introl.com/blog/voice-ai-infrastructure-real-time-speech-agents-asr-tts-guide-2025)):**

| Component | Cloud (optimistic) | Self-hosted M4 (realistic) |
|-----------|-------------------|---------------------------|
| STT (streaming, end-of-utterance) | ~150ms (Deepgram) | ~300–500ms (whisper.cpp) |
| LLM (first token streaming) | ~200–350ms (Mistral API) | ~200–400ms (Ollama stream) |
| TTS (first audio chunk) | ~75ms (ElevenLabs Flash) | ~50–150ms (Piper) |
| Network overhead | ~50–100ms | ~10–20ms (local) |
| **Total (typical)** | **~600–800ms** | **~600–1,100ms** |

**Note on streaming optimization:** With Ollama token streaming → Piper sentence-level TTS, **Time-to-First-Audio** can be reduced to ~400–600ms even with a 7B model by starting TTS on the first complete sentence before the full LLM response is generated.

---

## Part 2: Product Roadmap (Miro-Ready Format)

### Current State: ~55% Complete

| Phase | Scope | Status | Phases |
|-------|-------|--------|--------|
| Phase 1: Foundation | Config, DB connections, JWT auth, health endpoint | ✅ Complete (2026-03-17) | FOUND-01 through FOUND-09 |
| Phase 2: STT | Deepgram/Voxtral real transcription, no mock data | 🔴 Not started | STT-01 through STT-05 |
| Phase 3: LLM | Mistral API real inference, multi-turn, tool calling | 🔴 Not started | LLM-01 through LLM-05 |
| Phase 4: TTS | ElevenLabs/XTTS-v2 real synthesis | 🔴 Not started | TTS-01 through TTS-05 |
| Phase 5: Telephony | Twilio HTTP calls, call controller bridging | 🔴 Not started | TEL-01 through TEL-06 |
| Phase 6: Billing & Integrations | Stripe UCPM production, CRM, messaging | 🔴 Not started | BILL-01/02, CRM-01/02, MSG-01/02/03 |
| Phase 7: Frontend & Command Center | Login, WebSocket config, monitoring | 🔴 Not started | FE-01 through FE-04 |
| Phase 8: Unit Tests | 42 zero-coverage modules | 🔴 Not started | TEST-01 through TEST-08 |
| Phase 9: Integration & E2E Tests | DB fixtures, full call flow, compliance | 🔴 Not started | TEST-09 through TEST-11 |
| Phase 10: Production Readiness | K8s secrets, migrations, CI/CD, metrics | 🔴 Not started | PROD-01 through PROD-07 |

**Parallelization note:** Phases 6 and 7 depend only on Phase 1 (complete) and can run in parallel with Phases 2–5.

---

### Sprint-by-Sprint Roadmap (Paste into Miro as sticky notes or frames)

| Sprint | Duration | Theme | Goals | Deliverables | Dependencies | Success Criteria |
|--------|----------|-------|-------|-------------|-------------|-----------------|
| **Sprint 1** | Weeks 1–2 | Core Voice Pipeline | Connect real STT, LLM, TTS; remove all mock data | Working STT → LLM → TTS chain; no mock responses anywhere | DEEPGRAM_API_KEY, MISTRAL_API_KEY, ELEVENLABS_API_KEY | Audio in → transcript out (real); transcript → LLM response (real); LLM text → audio bytes (real) |
| **Sprint 2** | Weeks 3–4 | Telephony & E2E Call | Twilio integration; bridge audio to pipeline; make first real phone call | First real end-to-end call through the platform | Sprint 1 complete; TWILIO credentials | One real phone number calls the platform; STT processes speech; LLM responds; TTS speaks back |
| **Sprint 3** | Weeks 5–6 | BYOC & Advanced Voice | Kamailio SIP adapter; semantic VAD; code-switching; Flash Mode | Asterisk/FreeSWITCH trunk registration works; VAD <5% false interruption; Arabic+English code-switch | Sprint 2 complete | BYOC call routes through custom SIP trunk; code-switched utterance transcribed correctly |
| **Sprint 4** | Weeks 7–8 | Billing & Integrations | Stripe UCPM production billing; multi-currency; CRM hooks; webhook service | Stripe charges per UCPM rate with webhook verification; Salesforce creates contact after call | Sprint 1 complete (parallel) | Real Stripe charge processed for a test call; CRM contact created automatically post-call |
| **Sprint 5** | Weeks 9–10 | Frontend & Dashboard | Login page full MUI form; WebSocket URL from env; Command Center; analytics dashboard | Working login → dashboard flow; real-time call stats visible | Sprint 1 complete (parallel); PostgreSQL | Developer can log in, view dashboard, configure an agent through the UI |
| **Sprint 6** | Weeks 11–12 | Testing & QA | Unit tests for 42 zero-coverage modules; integration tests; compliance E2E | 70%+ unit test coverage; DB fixture suite; GDPR compliance E2E passing | Sprint 1–5 complete | CI pipeline green; compliance test verifies no data leaves EU when EU_DATA_RESIDENCY=true |
| **Sprint 7** | Weeks 13–14 | Production Readiness | K8s Helm secrets (not changeme); DB migrations; CI/CD pipeline; Prometheus monitoring | Sealed-secrets or External Secrets Operator; Alembic migrations run cleanly; GitHub Actions pipeline | Sprint 6 complete | Zero `changeme` secrets in production; deployment via Helm succeeds; Prometheus scrapers active |
| **Sprint 8** | Weeks 15–16 | Developer Experience | Python SDK; TypeScript SDK; publish to PyPI/npm; quickstart docs | `pip install voiquyr` works; `npm install voiquyr` works; "First call in 5 minutes" guide works end-to-end | Sprint 7 complete | External developer follows quickstart guide and makes a real call within 30 minutes |
| **Sprint 9** | Weeks 17–18 | Soft Launch | GitHub repo public (if licensing resolved); web demo; "first call in 5 min" guide; Design Partner onboarding | Public GitHub; demo video; MedGulf/Oman LNG/InfraTechton onboarded | Sprint 8 complete; licensing decision | At least one pilot customer making real calls through the platform |
| **Sprint 10** | Weeks 19–20 | GA & Marketing | Product Hunt; Hacker News Show HN; comparison pages; pilot customer go-live | PH launch; HN post; 3 comparison pages live; pilot case study drafted | Sprint 9 complete | 200+ GitHub stars; 100+ signups; one pilot customer in production |

---

### Priority Matrix (10 Gaps Ranked)

From the gaps analysis — ranked by priority for action:

| Priority | Gap | Effort | Impact | When |
|----------|-----|--------|--------|------|
| 1 | Complete the voice pipeline (STT → LLM → TTS real data) | 4–6 weeks | ☠️ Existential — nothing works without this | Sprint 1–2 |
| 2 | First-call-in-5-minutes experience | 2 weeks after pipeline | 🔑 Primary acquisition driver | Sprint 8 |
| 3 | Live web demo on homepage (WebRTC) | 1 week after pipeline | 🚀 Viral potential, conversion | Sprint 9 |
| 4 | Resolve licensing conflict + make repo public | 1 day decision | 🔓 Unlocks OSS community, distribution | Before Sprint 9 |
| 5 | Python + TypeScript SDK | 2–3 weeks | 📦 Developer adoption in their ecosystem | Sprint 8 |
| 6 | Discord + Twitter + docs site | 1 week setup | 🏗️ Community infrastructure | Sprint 9 |
| 7 | Pricing page with validated math | 1 week | 💰 Trust, conversion | Sprint 9 |
| 8 | First pilot live + published case study | Parallel with pipeline | 🏆 Enterprise credibility | Sprint 9 |
| 9 | Content + SEO (comparison pages, blog) | Ongoing | 🔍 Discovery, organic growth | Sprint 10+ |
| 10 | Published latency benchmarks vs competitors | After pipeline | 📊 Technical credibility | Sprint 10 |

---

## Part 3: ClickUp Project Structure

### Space: Voiquyr Platform

---

#### Folder: Sprint 1 — Core Voice Pipeline (Weeks 1–2)

**Theme:** Remove all mock data. Connect real STT, LLM, and TTS providers.

---

**List: STT Integration**

| Task | Description | Priority | Effort (hrs) | Dependencies |
|------|-------------|----------|-------------|-------------|
| Implement Deepgram streaming STT | Replace mock STT with Deepgram SDK asynclive streaming. Given WAV audio stream input, return real transcript string within 500ms. Remove all mock transcript returns. | Urgent | 8 | DEEPGRAM_API_KEY |
| Implement Voxtral fallback STT | When DEEPGRAM_API_KEY absent, fall back to Mistral Voxtral SDK. Must not crash; must return real transcript. | High | 4 | MISTRAL_API_KEY |
| Implement Code-Switch Handler | Arabic/English code-switched speech transcription with word-level language identification. Target: <15% WER on Levantine Arabic + English mixed audio. | High | 12 | Deepgram multilingual model |
| Add STT latency instrumentation | Log STT latency (ms) per request to Prometheus. Alert if p95 > 500ms. | Normal | 3 | Prometheus setup |
| Unit tests for STT agent | Test real Deepgram integration, Voxtral fallback, error handling, timeout behavior. | High | 6 | STT implementation |

---

**List: LLM Integration**

| Task | Description | Priority | Effort (hrs) | Dependencies |
|------|-------------|----------|-------------|-------------|
| Remove _generate_mock_response() | Delete the mock response generator entirely. Replace all call sites with real MistralClient.chat() calls. Verify no mock code remains via grep. | Urgent | 4 | MISTRAL_API_KEY |
| Implement multi-turn conversation | Full messages history passed to Mistral on each turn. Implement ConversationMemory class that maintains session-scoped message history. | Urgent | 8 | LLM mock removal |
| Implement ToolCaller integration | Tool calls from Mistral LLM execute via ToolCaller; results flow back into next LLM turn as tool_result messages. | High | 10 | Multi-turn conversation |
| Implement Flash Mode (speculative inference) | Begin LLM inference on partial transcript when STT confidence > 85%. Reconcile if final transcript differs. Targets 80ms TTFT reduction. | Normal | 16 | STT, LLM real integration |
| Unit tests for LLM agent | Test real Mistral API calls, tool calling, multi-turn context, Flash Mode reconciliation. | High | 8 | LLM implementation |

---

**List: TTS Integration**

| Task | Description | Priority | Effort (hrs) | Dependencies |
|------|-------------|----------|-------------|-------------|
| Replace XTTSv2ModelManager mock with ElevenLabs SDK | synthesize() must return real audio bytes from ElevenLabs API, not a sine-wave buffer. Remove all sine-wave fallback code. | Urgent | 6 | ELEVENLABS_API_KEY |
| Implement TTS streaming over WebSocket | Stream TTS audio chunks to client via WebSocket in real-time (not batch). ElevenLabs streaming API already supports this. | High | 8 | ElevenLabs integration |
| Implement XTTS-v2 self-hosted path (optional toggle) | Allow switching to local XTTS-v2 via config flag. Note: 1.5–4s TTFB; only for voice-cloning use cases. | Low | 16 | XTTS-v2 model download |
| Implement Piper TTS self-hosted path (optional toggle) | Allow switching to local Piper TTS via config flag. Sub-150ms, free, 900+ voices. | Normal | 8 | Piper installation |
| Unit tests for TTS agent | Test real ElevenLabs API, streaming, voice selection, error handling. | High | 5 | TTS implementation |

---

**List: End-to-End Pipeline Validation**

| Task | Description | Priority | Effort (hrs) | Dependencies |
|------|-------------|----------|-------------|-------------|
| E2E pipeline test: audio file → audio response | Given an audio input file, run through full pipeline (STT → LLM → TTS), assert non-empty audio bytes returned. No mocks. | Urgent | 4 | All Sprint 1 tasks |
| Latency Validator integration | Run Latency Validator synthetic tests every 5 minutes. Alert to Slack/email if p95 > 500ms. | High | 3 | Pipeline E2E |
| Remove all remaining mock data | Audit entire codebase with `grep -r "mock\|mock_\|fake\|dummy\|sine_wave"`. Remove every instance or replace with real implementation. | Urgent | 6 | All Sprint 1 tasks |

---

#### Folder: Sprint 2 — Telephony & E2E Call (Weeks 3–4)

**Theme:** Real phone calls through the platform. First call is the milestone.

---

**List: Twilio Integration**

| Task | Description | Priority | Effort (hrs) | Dependencies |
|------|-------------|----------|-------------|-------------|
| Implement Twilio make_call() | Real HTTP POST to api.twilio.com/Calls. Given valid credentials, returns a call SID. Remove any mock HTTP client. | Urgent | 6 | TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN |
| Implement Twilio send_sms() | Real SMS via Twilio API. Returns message SID. Used for post-call SMS follow-up workflows. | High | 3 | Twilio credentials |
| Configure Twilio Media Stream WebSocket | Set up Twilio webhook to stream real-time audio to call_controller.py WebSocket endpoint. | Urgent | 8 | Twilio account, call_controller.py |
| Test Twilio Media Stream → STT pipeline | Audio frames from Twilio WebSocket routed to STT agent in real-time. Transcript produced. | Urgent | 4 | Media stream config, STT |

---

**List: Call Controller**

| Task | Description | Priority | Effort (hrs) | Dependencies |
|------|-------------|----------|-------------|-------------|
| Implement call_controller audio bridging | Twilio Media Stream audio → STT agent → LLM agent → TTS agent → audio back to Twilio stream. Full bidirectional real-time audio bridge. | Urgent | 16 | Sprint 1 complete, Twilio media stream |
| Implement human handoff | When LLM detects frustration signal or unresolvable query, transfer call to human operator SIP extension. | High | 8 | Call controller |
| Implement SIP trunk failover | If primary SIP trunk fails, failover to alternate trunk within 5 seconds. No active calls dropped. | Normal | 12 | Asterisk config, multiple SIP trunks |
| Make the first real phone call | Execute and document the first real end-to-end call: real phone number → Twilio → Voiquyr → AI response → caller hears audio. Record the call. Document any issues. | Urgent | 4 | All Sprint 2 tasks |

---

**List: Asterisk Docker on Hetzner**

| Task | Description | Priority | Effort (hrs) | Dependencies |
|------|-------------|----------|-------------|-------------|
| Deploy Asterisk Docker on Hetzner CX42 | Docker Compose for Asterisk + AudioSocket. Configure SIP trunk pointing to Twilio. NAT traversal setup. | High | 8 | CX42 upgrade |
| Configure AudioSocket module | AudioSocket routes audio to/from Mac Mini M4 FastAPI backend in real-time. Test round-trip audio latency. | High | 6 | Asterisk running |
| Configure Twilio SIP trunk → Asterisk | Inbound PSTN calls route Twilio → Asterisk → AudioSocket → Mac Mini. Outbound: Mac Mini → Asterisk → Twilio → PSTN. | Urgent | 6 | Asterisk + Twilio |

---

#### Folder: Sprint 3 — BYOC & Advanced Voice (Weeks 5–6)

**Theme:** Kamailio SIP adapter, semantic VAD, Arabic code-switching, Flash Mode.

---

**List: BYOC SIP Adapter**

| Task | Description | Priority | Effort (hrs) | Dependencies |
|------|-------------|----------|-------------|-------------|
| Deploy Kamailio on Hetzner | Docker deployment of Kamailio SIP proxy. Configure as ingress for BYOC carrier trunks. | High | 12 | Hetzner CX42 |
| Implement SIP trunk registration via BYOC adapter | Customer provides Asterisk/FreeSWITCH trunk configuration. BYOC adapter registers it. Calls route through customer's carrier. | High | 16 | Kamailio |
| Implement codec transcoding | G.711, G.722, Opus codec transcoding via RTPEngine. Required for carriers that don't support Opus. | High | 10 | RTPEngine |
| Test MedGulf BYOC trunk configuration | Configure and test Jordanian SIP carrier trunk for MedGulf Insurance pilot. | High | 4 | BYOC adapter working |

---

**List: Advanced Voice Features**

| Task | Description | Priority | Effort (hrs) | Dependencies |
|------|-------------|----------|-------------|-------------|
| Implement Semantic VAD | Prosody + intent analysis for intelligent turn detection. Target: <50ms latency, <5% false interruption rate. Replace timer-based VAD. | High | 20 | STT real integration |
| Implement code-switching handler | Word-level language identification for Arabic/English mixed speech. Target: <15% WER. | High | 16 | Deepgram multilingual |
| Implement Flash Mode speculative inference | Begin LLM inference at 85%+ STT confidence. Reconcile on final transcript. ~80ms TTFT reduction. | Normal | 16 | LLM integration |
| Benchmark VAD false interruption rate | Run 100-call benchmark against reference test set. Report p50/p95 false interruption rate. Target: <5%. | Normal | 6 | Semantic VAD implementation |

---

#### Folder: Sprint 4 — Billing & Integrations (Weeks 7–8)

**Theme:** Real Stripe billing, CRM integration, webhook service.

---

**List: Stripe Billing**

| Task | Description | Priority | Effort (hrs) | Dependencies |
|------|-------------|----------|-------------|-------------|
| Implement Stripe UCPM billing (production) | Remove mock billing. Real Stripe charges per UCPM rate. Webhook signature verification. | Urgent | 12 | STRIPE_API_KEY |
| Implement multi-currency billing | Display amounts in customer's local currency (EUR, AED, INR, SGD, JPY) using real-time exchange rates. | High | 8 | Stripe production |
| Implement Stripe auto-refunds | When call fails mid-session due to platform error, automatically issue prorated Stripe refund. | High | 6 | Stripe production billing |
| Validate €0.04/min UCPM target | Calculate real per-minute cost: Deepgram + Mistral + ElevenLabs + Twilio + Hetzner infrastructure. Confirm or revise UCPM target. Document publicly. | Urgent | 4 | Real API cost data |

**UCPM Cost Breakdown Analysis (for validation):**

| Component | Cost/min at $0.0077/min rate | Notes |
|-----------|------------------------------|-------|
| Deepgram Nova-3 STT | $0.0077 | Per minute of audio |
| Mistral Small LLM | ~$0.0001 | ~500 tokens @ $0.30/M tokens output |
| ElevenLabs Flash TTS | ~$0.0075 | ~150 chars @ $0.05/1K chars |
| Twilio telephony | $0.0085–$0.013 | Varies by country |
| Hetzner CX42 infra | ~$0.0003 | Amortized over 6,000 min/mo |
| **Total provider cost** | **~$0.024–$0.029/min** | At 6,000 min/mo |
| **Target UCPM: €0.04/min** | **Margin: ~25–40%** | Depends on FX rate EUR/USD |

---

**List: CRM & Messaging**

| Task | Description | Priority | Effort (hrs) | Dependencies |
|------|-------------|----------|-------------|-------------|
| Implement Salesforce CRM integration | OAuth2 auth; post-call creates Salesforce contact record and case automatically. | Normal | 16 | Salesforce sandbox credentials |
| Implement webhook service | Reliable webhook delivery for post-call events (transcript, duration, sentiment, tool_calls). Retry logic, dead-letter queue. | High | 10 | Sprint 2 call controller |
| Implement n8n workflow template: CRM sync | n8n workflow: receive call-end webhook → look up contact → update CRM → log transcript. Pre-built template for customers. | Normal | 6 | Webhook service, n8n |
| Implement n8n workflow template: SMS follow-up | n8n: call-end → send SMS via Twilio with transcript summary or confirmation. | Normal | 4 | Webhook service |

---

#### Folder: Sprint 5 — Frontend & Dashboard (Weeks 9–10)

**Theme:** Working UI — login, WebSocket config, Command Center, analytics.

---

**List: Frontend**

| Task | Description | Priority | Effort (hrs) | Dependencies |
|------|-------------|----------|-------------|-------------|
| Implement login page (full MUI form) | POST to /auth/login → JWT → Redux auth dispatch → redirect to dashboard. bcrypt password validation. | Urgent | 8 | JWT auth (Phase 1 complete) |
| Fix WebSocket URL from environment | Read REACT_APP_API_URL from env, not hardcoded. audioStreamService.ts uses env var. | Urgent | 2 | Frontend codebase |
| Implement dashboard with real analytics | Real-time call volume, duration, sentiment, resolution rate from PostgreSQL. Redux connected. | High | 16 | Call controller, DB |
| Implement visual conversation flow builder | Drag-and-drop conversation nodes, branching conditions, publish without code. | Normal | 40 | Backend flow API |
| Implement Command Center pages | Dashboard, Config, FlashSimulator pages render with real-time data. Backend routers (auth, sip_trunks, calls, health) all respond. | High | 20 | All backend routes |

---

#### Folder: Sprint 6 — Testing & QA (Weeks 11–12)

**Theme:** Achieve 70%+ test coverage across 42 zero-coverage modules.

---

**List: Unit Tests**

| Task | Description | Priority | Effort (hrs) | Dependencies |
|------|-------------|----------|-------------|-------------|
| Unit tests: STT agent | Deepgram integration, Voxtral fallback, code-switch handler, latency logging | High | 8 | Sprint 1 |
| Unit tests: LLM agent | Mistral API, multi-turn, tool calling, Flash Mode, error handling | High | 8 | Sprint 1 |
| Unit tests: TTS agent | ElevenLabs, streaming, Piper path, XTTS-v2 path, error handling | High | 6 | Sprint 1 |
| Unit tests: Billing | Stripe UCPM charges, webhook verification, auto-refund, multi-currency | High | 8 | Sprint 4 |
| Unit tests: Auth | JWT issuance, bcrypt validation, protected route enforcement | High | 4 | Phase 1 complete |
| Unit tests: Call controller | Audio bridging, human handoff, SIP failover | High | 8 | Sprint 2 |
| Unit tests: BYOC adapter | SIP trunk registration, codec transcoding, Kamailio integration | Normal | 8 | Sprint 3 |
| Unit tests: Webhook service | Delivery, retry logic, dead-letter queue | Normal | 4 | Sprint 4 |

---

**List: Integration & E2E Tests**

| Task | Description | Priority | Effort (hrs) | Dependencies |
|------|-------------|----------|-------------|-------------|
| DB fixture suite | PostgreSQL test fixtures for users, calls, sessions, billing records. Docker Compose test environment. | High | 8 | All sprints |
| Integration test: full call flow | Audio file → STT → LLM → TTS → audio output in test environment. No external APIs (mock them). | High | 12 | All sprints |
| E2E compliance test | Given EU_DATA_RESIDENCY=true, verify no data leaves EU-resident endpoint. Automated GDPR audit. | Urgent | 8 | All sprints |
| E2E test: Stripe webhook | Simulate Stripe webhook events (payment_succeeded, payment_failed); verify system response. | High | 4 | Sprint 4 |

---

#### Folder: Sprint 7 — Production Readiness (Weeks 13–14)

**Theme:** K8s secrets, DB migrations, CI/CD, monitoring. Zero `changeme` values.

---

**List: Infrastructure & Security**

| Task | Description | Priority | Effort (hrs) | Dependencies |
|------|-------------|----------|-------------|-------------|
| Replace all K8s `changeme` secrets | Audit every K8s secret. Implement sealed-secrets OR external-secrets-operator OR Vault. Document the chosen approach. | Urgent | 12 | Sprint 6 |
| Implement Alembic DB migrations | All schema changes managed via Alembic migration files. `alembic upgrade head` runs cleanly from scratch. | High | 8 | PostgreSQL |
| Set up GitHub Actions CI/CD pipeline | On push to main: lint → test → build Docker image → deploy to staging. On tag: deploy to production. | High | 12 | Sprint 6 tests |
| Configure Prometheus + Grafana | Scrape FastAPI metrics, Asterisk call metrics, STT/LLM/TTS latency histograms. Grafana dashboards. | High | 8 | All services running |
| Configure Jaeger distributed tracing | Trace requests through STT → LLM → TTS → response. Identify latency hotspots. | Normal | 6 | All services |
| Istio service mesh configuration | mTLS between platform services. Traffic policies. Rate limiting. | Normal | 12 | Kubernetes cluster |
| Helm chart hardening | Values.yaml reviewed; no hardcoded secrets; README for deployment. | High | 6 | All K8s config |

---

#### Folder: Sprint 8 — Developer Experience (Weeks 15–16)

**Theme:** Python SDK, TypeScript SDK, PyPI/npm publish, quickstart guide.

---

**List: SDKs**

| Task | Description | Priority | Effort (hrs) | Dependencies |
|------|-------------|----------|-------------|-------------|
| Python SDK — core client | voiquyr.Client class; create_agent(), make_call(), stream_audio(). Async support. 5–10 line integration. | Urgent | 16 | Sprint 7 (stable API) |
| Python SDK — publish to PyPI | Package metadata, README, changelog. `pip install voiquyr` works. CI auto-publishes on tag. | Urgent | 4 | Python SDK |
| TypeScript SDK — core client | VoiquyrClient class; same core methods. ES modules + CommonJS. Type definitions. | High | 20 | Sprint 7 (stable API) |
| TypeScript SDK — publish to npm | `npm install voiquyr` works. Includes type declarations. CI auto-publishes on tag. | High | 4 | TypeScript SDK |
| SDK documentation | Auto-generated API docs from docstrings/JSDoc. Hosted at docs.voiquyr.ai. | High | 8 | Both SDKs |

---

**List: Developer Experience**

| Task | Description | Priority | Effort (hrs) | Dependencies |
|------|-------------|----------|-------------|-------------|
| "First call in 5 minutes" quickstart guide | Single `pip install voiquyr` → set 3 env vars → `voiquyr call start --phone +1234567890` → hear AI respond. Works for real. | Urgent | 8 | Python SDK |
| Docker Compose quickstart | `docker compose up` → running platform with pre-configured test keys. No manual config. | High | 6 | Docker images |
| Quickstart for MacBook Air M5 setup | Step-by-step guide for the specific dev hardware. (Detailed in Part 4.) | High | 4 | All infrastructure |
| OpenAPI spec publication | FastAPI auto-generates OpenAPI. Publish at docs.voiquyr.ai/api. Update with every release. | High | 2 | FastAPI backend |

---

#### Folder: Sprint 9 — Soft Launch (Weeks 17–18)

**Theme:** GitHub public, web demo, pilot customers onboarded.

---

**List: Launch Preparation**

| Task | Description | Priority | Effort (hrs) | Dependencies |
|------|-------------|----------|-------------|-------------|
| Resolve licensing conflict | README says Apache 2.0; LICENSE says private. MUST resolve before making repo public. (See Part 7.) | Urgent | 2 (decision) | Founder/legal |
| Make GitHub repo public (after licensing decision) | Optimize README: demo GIF, badges, quickstart, architecture diagram. GitHub Topics configured. | High | 4 | Licensing decision |
| Submit to GitHub awesome-lists | awesome-european-ai, awesome-ai-voice, awesome-conversational-ai, awesome-ai-tools, awesome-self-hosted | High | 4 | Public GitHub repo |
| Build web-based voice demo | WebRTC voice demo embedded on voiquyr.com homepage. Visitors talk to Voiquyr without signing up. | High | 20 | Voice pipeline complete |
| Record demo call videos | Real conversations: English (appointment scheduling), Arabic (insurance query), German (customer support). Upload to YouTube. | High | 8 | Demo working |
| Set up Discord server | Channels: #welcome, #general-help, #bug-reports, #feature-requests, #showcase, #announcements, #random. Community feature enabled. | Normal | 4 | Launch decision |
| Set up @voiquyr Twitter/X account | Brand account. Post first "build in public" thread. Link to GitHub. | Normal | 2 | Launch decision |

---

**List: Pilot Customer Onboarding**

| Task | Description | Priority | Effort (hrs) | Dependencies |
|------|-------------|----------|-------------|-------------|
| MedGulf Insurance onboarding | Configure Arabic + English agent. Set up inbound claims flow. Test Jordanian Arabic dialect accuracy. GDPR DPA signed. | Urgent | 20 | Sprint 2–3 complete |
| Oman LNG onboarding (via Shape Digital) | Enterprise voice automation use case. Configure agent for LNG knowledge base queries. SLA agreed. | High | 16 | Sprint 2 complete |
| InfraTechton Aqaba onboarding | Voice interface for consulting knowledge base. Configure RAG tool calls. | Normal | 12 | Sprint 2 complete |
| Pilot monitoring setup | Prometheus alerts for each pilot customer's SLA metrics. Dedicated Slack channel for each pilot. | High | 4 | Prometheus |

---

#### Folder: Sprint 10 — GA & Marketing (Weeks 19–20)

**Theme:** Product Hunt, Hacker News, comparison pages, pilot go-live.

---

**List: GTM Execution**

| Task | Description | Priority | Effort (hrs) | Dependencies |
|------|-------------|----------|-------------|-------------|
| Product Hunt launch | Find experienced Hunter (1,000+ followers, dev tool experience). Build 300–500 person supporter list. Launch kit: social copy, graphics, 60-second demo video. Launch day: 12:01 AM PST. | High | 40 (prep) | Sprint 9 |
| Hacker News Show HN post | "Show HN: Voiquyr – Open-source, EU-native Voice AI platform (Vapi alternative)". Tuesday 8–11 AM UTC. Founder in thread all day. Live demo link required. | High | 8 (prep + day) | Public GitHub, demo |
| Create comparison page: vs Vapi | voiquyr.ai/compare/voiquyr-vs-vapi. Full feature matrix, pricing comparison, FAQ schema. Honest about Vapi's strengths. | High | 8 | Website multi-page |
| Create comparison page: vs Retell | voiquyr.ai/compare/voiquyr-vs-retell | High | 6 | Website |
| Create comparison page: vs Bland | voiquyr.ai/compare/voiquyr-vs-bland-ai | Normal | 6 | Website |
| Submit to AlternativeTo, G2, Capterra, Futurepedia | Product listed as alternative to Vapi, Retell, Bland. G2 profile created. Capterra: AI Voice Assistants + Contact Center AI categories. | High | 4 | Launch |
| Publish first pilot case study | MedGulf Insurance: call volume, resolution rate, cost savings, Arabic accuracy metrics, customer quote. | High | 8 | MedGulf go-live |
| Publish latency benchmarks | Head-to-head latency: Voiquyr vs Vapi vs Retell vs Synthflow. p50/p95/p99 from Latency Validator. | High | 6 | Pipeline stable |

---

#### Folder: Infrastructure Setup

**Tasks for hardware and cloud configuration outside the sprint cadence.**

| Task | Description | Priority | Effort (hrs) | Timeline |
|------|-------------|----------|-------------|---------|
| Upgrade Hetzner CX32 → CX42 | Migrate ERPNext Docker to CX42 (16 GB RAM). Verify ERPNext runs with headroom. | Urgent | 4 | Before Sprint 2 |
| Install Ollama on Mac Mini M4 | Install Ollama. Download Mistral 7B Q4_K_M and Qwen2.5:7B. Benchmark tokens/sec. | Urgent | 2 | Before Sprint 1 |
| Install whisper.cpp + CoreML on Mac Mini M4 | Compile whisper.cpp with CoreML flag. Test base and medium models. Benchmark latency. | High | 4 | Before Sprint 1 |
| Install Piper TTS on Mac Mini M4 | Install Piper. Download voice models (English + Arabic if available). Test synthesis latency. | High | 2 | Before Sprint 1 |
| Deploy Asterisk Docker on Hetzner CX42 | Docker Compose: Asterisk + AudioSocket. SIP trunk config. NAT traversal. | High | 8 | Sprint 2 |
| Configure PostgreSQL + Redis (Mac Mini) | Production-grade PostgreSQL and Redis on Mac Mini. Persistent volumes. Backup strategy. | Urgent | 4 | Before Sprint 1 |
| Configure domain + SSL | voiquyr.com (Cloudflare). SSL for API subdomain. DNS for api.voiquyr.com. | High | 2 | Before Sprint 9 |
| Set up Cloudflare WAF rules | Allow GPTBot, PerplexityBot, ClaudeBot, OAI-SearchBot. Verify in Security > Bots. | High | 1 | Before Sprint 10 |

---

#### Folder: Marketing & GTM

**Tasks that run in parallel with development — begin Week 1.**

| Task | Description | Priority | Effort (hrs) | Timeline |
|------|-------------|----------|-------------|---------|
| Register voiquyr.ai domain | Evaluate voiquyr.com vs voiquyr.ai (see Part 7). Register chosen domain. | Urgent | 1 | Week 1 |
| Add robots.txt with AI crawler permissions | Allow GPTBot, PerplexityBot, ClaudeBot, anthropic-ai, Google-Extended, Googlebot. Add sitemap reference. | High | 1 | Week 1 |
| Create llms.txt at voiquyr.com/llms.txt | Markdown file guiding LLMs to key content. Include positioning, key pages, compliance facts. | High | 2 | Week 1 |
| Add schema.org JSON-LD (SoftwareApplication) | Add to homepage. Include featureList, offers, sameAs links. | High | 2 | Week 2 |
| Create Crunchbase company profile | Complete profile: funding (if any), team, description (use canonical brand facts). | High | 1 | Week 2 |
| Create LinkedIn Company Page | Full profile: description, specialties, employees. Post weekly updates. | High | 1 | Week 2 |
| Create Wikidata entity | Add entity: company, product, location, founding date. | Normal | 1 | Week 3 |
| Publish first blog post | "GDPR-Compliant Voice AI: Why Architecture Matters More Than Certifications". Technical, no pitch. Target HN. | High | 8 | Week 3-4 |
| Write EU Sovereignty white paper | "Voice AI and the EU AI Act: A Compliance Guide for Enterprises". PDF + web version. Lead magnet. | Normal | 16 | Month 2 |
| Create email waitlist landing page | Simple form at voiquyr.com: "Get notified at launch." Goal: 500 signups pre-launch. | High | 4 | Week 1 |
| Set up Google Search Console | Verify voiquyr.com. Submit sitemap. Monitor impressions. | High | 1 | Week 1 |
| Define 20 Golden Prompts | Test across ChatGPT, Perplexity, Claude, Gemini weekly. Track Voiquyr mentions. Build scorecard. | High | 2 | Week 1 |

---

#### Folder: Ongoing Operations

**Recurring tasks — set up as recurring ClickUp tasks.**

| Task | Frequency | Description | Owner |
|------|-----------|-------------|-------|
| Monitor Prometheus alerts | Daily | Check p95 latency, error rates, API uptime. | DevOps |
| Update Golden Prompts scorecard | Weekly | Test 20 AI search prompts across ChatGPT, Perplexity, Claude, Gemini. Log results. | Marketing |
| Community support (Discord + GitHub Issues) | Daily | Respond to all Discord #general-help and GitHub issues within 4 hours. | DevRel |
| Weekly "build in public" Twitter thread | Weekly | Share one technical update, milestone, or learning. Include screenshot/number. | Founder |
| API provider cost review | Monthly | Pull Deepgram, Mistral, ElevenLabs, Twilio invoices. Verify UCPM margin. | Finance |
| Update comparison page pricing | Quarterly | Verify competitor pricing is current. Update voiquyr.ai/compare/* pages. | Marketing |
| Backup PostgreSQL + Redis | Daily | Automated backup to Hetzner Object Storage. Test restore quarterly. | DevOps |
| Pilot customer SLA review | Weekly | Review call volume, resolution rate, error rate for MedGulf, Oman LNG, InfraTechton. | Product |
| Security dependency audit | Monthly | Run `pip audit` + `npm audit`. Patch critical CVEs within 48 hours. | Engineering |
| GDPR compliance report | Monthly | Run compliance report generator. Verify EU data residency enforcement. Store for audit. | Compliance |

---

## Part 4: Local Dev Setup Guide (MacBook Air M5)

This guide gets a new developer from zero to a working voice call on the MacBook Air M5 dev laptop. The M5 is for development only — never in the production call path.

---

### Prerequisites

Install these before anything else:

```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install required tools
brew install python@3.11 node git postgresql redis

# Install Docker Desktop
# Download from: https://www.docker.com/products/docker-desktop/
# M5 = Apple Silicon — download the "Apple Silicon" version

# Verify versions
python3.11 --version     # Should be 3.11.x
node --version           # Should be 18.x or higher
docker --version         # Should be 24.x+
git --version            # Any recent version

# Install Ollama for local LLM (optional — for Option A/D architecture)
curl -fsSL https://ollama.ai/install.sh | sh
# Then pull a model:
ollama pull mistral:7b-instruct-q4_K_M
# Or for faster responses:
ollama pull qwen2.5:7b
```

---

### Step 1: Clone and Configure

```bash
# Clone the repository
git clone https://github.com/ja3ooni/voiqur-platform.git voiquyr
cd voiquyr

# Create Python virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
cd ..

# Verify installation
python -c "import fastapi, deepgram, mistralai, elevenlabs; print('All dependencies OK')"
```

---

### Step 2: Local Services (Docker Compose)

Create `docker-compose.dev.yml` in the project root:

```yaml
version: '3.9'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: voiquyr_dev
      POSTGRES_USER: voiquyr
      POSTGRES_PASSWORD: dev_password_change_in_prod
    ports:
      - "5432:5432"
    volumes:
      - postgres_dev_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U voiquyr -d voiquyr_dev"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_dev_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  n8n:
    image: n8nio/n8n:latest
    ports:
      - "5678:5678"
    environment:
      N8N_BASIC_AUTH_ACTIVE: "true"
      N8N_BASIC_AUTH_USER: admin
      N8N_BASIC_AUTH_PASSWORD: dev_n8n_password
      DB_TYPE: postgresdb
      DB_POSTGRESDB_HOST: postgres
      DB_POSTGRESDB_DATABASE: n8n
      DB_POSTGRESDB_USER: voiquyr
      DB_POSTGRESDB_PASSWORD: dev_password_change_in_prod
    depends_on:
      postgres:
        condition: service_healthy

volumes:
  postgres_dev_data:
  redis_dev_data:
```

```bash
# Start local services
docker compose -f docker-compose.dev.yml up -d

# Verify services are running
docker compose -f docker-compose.dev.yml ps

# Check PostgreSQL
docker exec -it voiquyr_postgres_1 psql -U voiquyr -d voiquyr_dev -c "\dt"

# Check Redis
docker exec -it voiquyr_redis_1 redis-cli ping
# Expected output: PONG
```

---

### Step 3: Environment Variables

Create `.env` in the project root (never commit this file):

```bash
# ============================================================
# VOIQUYR LOCAL DEVELOPMENT ENVIRONMENT
# Copy this to .env and fill in your API keys
# NEVER commit .env to git — it's in .gitignore
# ============================================================

# ─── DATABASE ──────────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://voiquyr:dev_password_change_in_prod@localhost:5432/voiquyr_dev
REDIS_URL=redis://localhost:6379/0

# ─── AUTH ──────────────────────────────────────────────────
JWT_SECRET_KEY=your-256-bit-jwt-secret-here-minimum-32-characters
JWT_ALGORITHM=HS256
JWT_EXPIRY_HOURS=24

# ─── SPEECH-TO-TEXT ────────────────────────────────────────
DEEPGRAM_API_KEY=your_deepgram_api_key_here
# Get free key at: https://deepgram.com
# Free tier: 12,000 minutes/year

# STT fallback (Mistral Voxtral)
# Uses MISTRAL_API_KEY below when DEEPGRAM_API_KEY absent

# ─── LLM ───────────────────────────────────────────────────
MISTRAL_API_KEY=your_mistral_api_key_here
# Get at: https://console.mistral.ai

# Local LLM via Ollama (optional — for Option A/D architecture)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral:7b-instruct-q4_K_M
USE_LOCAL_LLM=false  # Set to true to use Ollama instead of Mistral API

# ─── TEXT-TO-SPEECH ────────────────────────────────────────
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
# Get at: https://elevenlabs.io
# Free tier: 10,000 chars/month

# Local TTS via Piper (optional — for Option A/D architecture)
USE_LOCAL_TTS=false  # Set to true to use Piper instead of ElevenLabs
PIPER_VOICE_MODEL=en_US-amy-medium  # Path to Piper voice model

# ─── TELEPHONY ─────────────────────────────────────────────
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_twilio_auth_token_here
TWILIO_PHONE_NUMBER=+1xxxxxxxxxx
# Get at: https://www.twilio.com
# Free trial: $15.50 credit

# ─── BILLING ───────────────────────────────────────────────
STRIPE_API_KEY=sk_test_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
STRIPE_UCPM_PRICE_ID=price_xxxxxxxxxxxxxxxxxxxxxxxx
# Get at: https://stripe.com
# Use test keys (sk_test_*) for development

# ─── COMPLIANCE ────────────────────────────────────────────
EU_DATA_RESIDENCY=false  # Set to true to enforce EU-only data processing
DATA_RESIDENCY_REGION=eu  # eu | me | asia

# ─── PLATFORM ──────────────────────────────────────────────
ENVIRONMENT=development
LOG_LEVEL=DEBUG
API_HOST=0.0.0.0
API_PORT=8000

# ─── FRONTEND ──────────────────────────────────────────────
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000

# ─── CRMONBOARDING (optional) ──────────────────────────────
# SALESFORCE_CLIENT_ID=your_salesforce_client_id
# SALESFORCE_CLIENT_SECRET=your_salesforce_client_secret
```

---

### Step 4: Run the Platform

```bash
# Activate virtual environment (if not already active)
source .venv/bin/activate

# Run database migrations
alembic upgrade head

# Start FastAPI backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# In a new terminal — start frontend
cd frontend
npm start
# Opens at http://localhost:3000

# Verify health endpoint
curl http://localhost:8000/health
# Expected: {"redis": "ok", "postgres": "ok", "status": "healthy"}

# View API documentation
open http://localhost:8000/docs
```

---

### Step 5: Make Your First Test Call (Local Pipeline Validation)

This tests the voice pipeline without a real phone call:

```bash
# Option 1: Test via API with a sample audio file
# First, get a sample WAV file (English speech)
curl -o test_audio.wav \
  "https://www2.cs.uic.edu/~i101/SoundFiles/StarWars60.wav"

# Send to the STT + LLM + TTS pipeline
curl -X POST http://localhost:8000/api/v1/voice/test-pipeline \
  -H "Authorization: Bearer $(curl -s -X POST http://localhost:8000/auth/login \
    -H 'Content-Type: application/json' \
    -d '{"email":"test@voiquyr.com","password":"testpassword"}' | jq -r '.access_token')" \
  -F "audio=@test_audio.wav" \
  --output response_audio.wav

# If successful, response_audio.wav contains the AI's spoken response
# Play it:
afplay response_audio.wav  # macOS

# Option 2: Use the Python SDK (after Sprint 8)
pip install voiquyr
python3 -c "
import voiquyr
client = voiquyr.Client(api_key='your_api_key')
result = client.voice.test_pipeline(audio_file='test_audio.wav')
print(f'Transcript: {result.transcript}')
print(f'Response: {result.llm_response}')
print(f'Audio saved to: {result.audio_path}')
"
```

---

### Step 6: Development Workflow

```bash
# Hot reload is enabled by default via --reload flag in uvicorn

# Run tests
pytest tests/ -v

# Run tests with coverage report
pytest tests/ --cov=app --cov-report=html
# Open htmlcov/index.html in browser

# Lint code
ruff check app/
black app/ --check  # Check formatting
black app/          # Auto-format

# Type checking
mypy app/

# Frontend hot reload
# Already active at http://localhost:3000 when `npm start` is running

# Watch for changes in tests
pytest --watch tests/  # Requires pytest-watch: pip install pytest-watch

# Rebuild Docker services after config changes
docker compose -f docker-compose.dev.yml restart

# Reset database (WARNING: deletes all local data)
docker compose -f docker-compose.dev.yml down -v
docker compose -f docker-compose.dev.yml up -d
alembic upgrade head

# Monitor real-time logs
tail -f logs/voiquyr.log
# Or via Docker:
docker compose -f docker-compose.dev.yml logs -f
```

---

### Mac Mini M4 Production Setup

The Mac Mini M4 runs the production inference stack. This is a separate configuration from the MacBook Air M5 dev environment.

#### Docker Compose for Mac Mini Production

Create `docker-compose.prod.yml` on the Mac Mini:

```yaml
version: '3.9'

services:
  voiquyr-api:
    image: ghcr.io/ja3ooni/voiqur-platform:latest
    env_file: .env.production
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs

  postgres:
    image: postgres:16-alpine
    env_file: .env.production
    volumes:
      - postgres_prod_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis_prod_data:/data
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    volumes:
      - grafana_data:/var/lib/grafana
    restart: unless-stopped

volumes:
  postgres_prod_data:
  redis_prod_data:
  grafana_data:
```

#### Ollama Installation + Model Download on Mac Mini

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull recommended models for voice AI on M4 16GB
# Option 1: Best quality/speed balance
ollama pull mistral:7b-instruct-q4_K_M

# Option 2: Fastest responses (lower quality)
ollama pull qwen2.5:7b

# Option 3: Fastest possible (3B model — use for low-latency priority)
ollama pull llama3.2:3b

# Benchmark on your M4 (run each and note tokens/sec)
ollama run mistral:7b-instruct-q4_K_M "Respond in exactly one sentence: What is voice AI?"
ollama run qwen2.5:7b "Respond in exactly one sentence: What is voice AI?"

# Verify Ollama API
curl http://localhost:11434/api/generate \
  -d '{"model": "qwen2.5:7b", "prompt": "Hello", "stream": false}'
```

#### whisper.cpp Compilation with CoreML on Mac Mini

```bash
# Install dependencies
brew install cmake python@3.11

# Clone whisper.cpp
git clone https://github.com/ggerganov/whisper.cpp.git
cd whisper.cpp

# Download model (base for fastest, medium for best quality)
bash ./models/download-ggml-model.sh base
# Or:
bash ./models/download-ggml-model.sh medium

# Compile with CoreML support (critical for M4 Neural Engine acceleration)
cmake -B build -DWHISPER_COREML=1
cmake --build build -j$(sysctl -n hw.ncpu)

# Generate CoreML model (first time only — takes a few minutes)
pip install ane_transformers openai-whisper coremltools
./models/generate-coreml-model.sh base
# Or:
./models/generate-coreml-model.sh medium

# Test benchmark
./build/bin/whisper-cli \
  -m models/ggml-base.bin \
  -f samples/jfk.wav \
  --print-realtime

# Expected output (base model on M4):
# whisper_model_load: model size  = 140.31 MB
# [realtime: 18x] [latency: 0.5s]

# The Python binding for integration with FastAPI
pip install pywhispercpp  # Or use subprocess to call whisper-cli
```

#### Piper TTS Installation on Mac Mini

```bash
# Download Piper binary for macOS (Apple Silicon)
# https://github.com/rhasspy/piper/releases
curl -L "https://github.com/rhasspy/piper/releases/latest/download/piper_macos_aarch64.tar.gz" \
  -o piper_macos.tar.gz
tar -xzf piper_macos.tar.gz
chmod +x piper/piper

# Download voice models
mkdir -p piper/voices

# English (US) voice
curl -L "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx" \
  -o piper/voices/en_US-amy-medium.onnx
curl -L "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json" \
  -o piper/voices/en_US-amy-medium.onnx.json

# Arabic voice (if available)
# Check: https://huggingface.co/rhasspy/piper-voices/tree/main/ar

# Test synthesis (should produce WAV in <150ms)
echo "Hello, I am Voiquyr, your EU-native voice AI assistant." | \
  ./piper/piper \
  --model piper/voices/en_US-amy-medium.onnx \
  --output_file test_tts.wav

# Play to verify
afplay test_tts.wav
```

#### Asterisk Docker on Hetzner (Reference)

```bash
# SSH to Hetzner CX42
ssh root@hetzner-cxX42-ip

# Create Asterisk Docker Compose
cat > docker-compose.asterisk.yml << 'EOF'
version: '3.9'

services:
  asterisk:
    image: andrius/asterisk:latest
    network_mode: host  # Required for SIP NAT traversal
    volumes:
      - ./asterisk/conf:/etc/asterisk
      - ./asterisk/sounds:/var/lib/asterisk/sounds
      - ./asterisk/logs:/var/log/asterisk
    restart: unless-stopped
    environment:
      - ASTERISK_UID=1000
      - ASTERISK_GID=1000

  # AudioSocket receives audio from Asterisk and forwards to Mac Mini
  audiosocket-proxy:
    image: audiosocket/proxy:latest
    ports:
      - "9093:9093"
    environment:
      UPSTREAM_HOST: YOUR_MAC_MINI_IP  # Mac Mini's IP or dynamic DNS
      UPSTREAM_PORT: 8000
      UPSTREAM_PATH: /ws/audio
    restart: unless-stopped

EOF

docker compose -f docker-compose.asterisk.yml up -d
```

---

## Part 5: GTM Strategy

### Positioning

**Primary:** "The open-source, EU-native Vapi alternative"  
→ This is the "open-source Firebase alternative" playbook that got Supabase to $5B.

**One-liner:** "Voice AI your compliance team will actually sign off on."

**Positioning statement (full):**  
For enterprises and developers in EU, Middle East, and Asia who need voice AI that actually stays in their jurisdiction, Voiquyr is the open-source voice AI platform that delivers real-time conversational agents with native GDPR/AI Act compliance and bring-your-own-carrier flexibility. Unlike Vapi and Retell, Voiquyr is EU-native (no CLOUD Act exposure), self-hostable, and supports Arabic dialects and code-switching out of the box.

**Competitive differentiation (things no competitor can authentically claim):**

| Claim | Why Only Voiquyr | Evidence |
|-------|-----------------|---------|
| EU data residency by architecture | US companies (Vapi, Retell, Bland) subject to CLOUD Act regardless of EU servers | GDPR Article 44 analysis |
| Arabic dialect recognition (5 dialects) | None of the major platforms support Arabic out of the box | PRD P1-04 |
| Bring Your Own Carrier (any SIP) | Vapi uses Twilio only; Retell: Twilio/Telnyx only; Bland: enterprise only | PRD P1-01 |
| Open-source Apache 2.0 (if licensing resolved) | Vapi, Retell, Bland, Synthflow all proprietary | LICENSE decision pending |
| EU AI Act compliance validation | No competitor has this feature at all | PRD P0-10 |

---

### Phase 0: Pre-Launch (Now → Pipeline Complete)

**Goal:** Build 500-person email waitlist and early community while product ships.

**Timeline:** Weeks 1–8 (parallel with Sprint 1–4)

| Action | Channel | Detail | Timeline |
|--------|---------|--------|---------|
| Start @voiquyr Twitter/X | Twitter/X | First post: "Building the EU-native alternative to Vapi. Here's why it matters. [thread]" | Week 1 |
| Email waitlist landing page | voiquyr.com | Simple form: problem statement, 3 differentiators, "Get notified at launch." | Week 1 |
| Create Discord server | Discord | Private initially — invite 20–30 people from network. Open after Sprint 9. | Week 2 |
| "Build in public" thread series | Twitter/LinkedIn | Weekly: progress update with real screenshot/number/insight | Every week |
| First blog post — no pitch | Blog / HN | "GDPR-Compliant Voice AI: Why Architecture Matters More Than Certifications" | Week 3 |
| Second blog post | Blog / HN | "Arabic Code-Switching in Voice AI: Why Standard STT Fails" | Week 5 |
| Third blog post | Blog / HN | "BYOC Telephony: Why We Built a Kamailio SIP Adapter Instead of Using Twilio" | Week 7 |
| Fourth blog post | Blog / HN | "The CLOUD Act vs GDPR: Why Your Voice AI Data Isn't Safe in a US Cloud" | Week 9 |

**"Build in public" content format (Twitter):**
> "Week 4: First real transcription from Deepgram running through the pipeline. Here's what happened when we sent Arabic audio through. [screenshot of actual terminal output]"

> "We benchmarked our STT → LLM → TTS latency against Vapi and Retell. Here's the raw data: [chart] Spoiler: we're not best on every metric. Here's why."

> "Today we made our first real phone call through Voiquyr. 14 seconds of audio. Sounds terrible. We're shipping anyway. Here's the recording: [audio file]"

---

### Phase 1: Soft Launch (Pipeline Working → First 100 Users)

**Goal:** 100 developers using the product; 200 GitHub stars; first community PR.

**Timeline:** Weeks 17–20 (Sprint 9–10 window)

| Action | Channel | Detail |
|--------|---------|--------|
| Make GitHub repo public (Apache 2.0) | GitHub | Optimized README: demo GIF, badges, quickstart, architecture diagram, GitHub Topics |
| GitHub Topics to add | GitHub | `voice-ai`, `speech-recognition`, `text-to-speech`, `conversational-ai`, `open-source`, `self-hosted`, `gdpr`, `eu-ai-act`, `python`, `fastapi`, `telephony`, `sip`, `call-center`, `arabic-nlp`, `voice-cloning`, `deepgram`, `mistral`, `elevenlabs` |
| Submit to awesome-lists | GitHub | awesome-selfhosted, awesome-ai-voice, awesome-conversational-ai, awesome-ai-tools, awesome-european-ai |
| Show HN post | Hacker News | ONE shot — make it count. Tuesday 8–11 AM UTC. Title under 55 chars. Live demo link required. Founder in thread all day. |
| "First call in 5 minutes" tutorial | Blog + YouTube | Screen recording. Real terminal. Show actual errors. No polished production. |
| Publish Python SDK to PyPI | PyPI | `pip install voiquyr` |
| Publish TypeScript SDK to npm | npm | `npm install voiquyr` |
| Open Discord to public | Discord | Seed with 20–30 developers first; monitor for first 48 hours |
| Submit to AlternativeTo, G2, Capterra | Directories | List as alternative to Vapi, Retell, Bland, Synthflow |

**HN Show HN post structure:**
```
Title: Show HN: Voiquyr – Open-source EU voice AI platform (Vapi alternative)
                  ← 55 characters ←

Body (maker's first comment — write as a human):
Hey HN! I'm [name], building Voiquyr after spending years in EU enterprise 
infrastructure where every voice AI evaluation ended the same way: "GDPR?"
The answer was always: "Ask your DPO."

Here's what we built:
- Full voice pipeline (STT/LLM/TTS) on EU-region infrastructure by design
- Bring your own SIP carrier — no forced Twilio migration
- Arabic dialect recognition (5 dialects) for MEA enterprise deployments
- Apache 2.0 — self-host or use our cloud

What doesn't work yet: [be honest — list known gaps]
What's coming next: [one concrete next sprint goal]

Live demo: [link]
GitHub: [link]
Docs: [link]

Happy to answer any questions — I'll be here all day.
```

---

### Phase 2: Product Hunt Launch + Content Engine (Users 100 → 1,000)

**Goal:** 1,000 signups; 500+ GitHub stars; Top 5 Product of the Day; first paying customer.

**Timeline:** Weeks 21–28 (4–8 weeks after soft launch)

#### Product Hunt Launch Playbook

**4 weeks before launch:**
- Find an experienced Hunter with 1,000+ followers who has launched developer tools (search PH for hunters with dev tool launches: Flo Merian `fmerian` is one example)
- Build supporter list of 300–500 people: Discord members, Twitter followers, early users, angel investors
- Create launch-specific landing page (not homepage): problem → solution → demo → CTA
- Prepare launch day kit: social copy, graphics, 60-second demo video, FAQ document

**Launch day schedule (CET timezone):**
- 12:01 AM PST (09:01 AM CET): Go live on Product Hunt
- 09:00 AM CET: Twitter Spaces reminder tweet
- 09:30 AM CET: Blog post live — "Why We Built an EU-Native Alternative to Vapi"
- 09:35 AM CET: Launch tweet with demo video
- 09:40 AM CET: Share with angel investors, EU tech communities, Discord
- 09:45 AM CET: Twitter Spaces live (founders discuss the product, answer questions)
- All day: One person owns PH thread — replies to every comment
- All day: Engage every commenter on Twitter/LinkedIn/Discord

**PH tagline options (test with 5 people who haven't seen the product):**
- "Open-source voice AI with EU data sovereignty"
- "The EU-native alternative to Vapi — self-hosted, Apache 2.0"
- "Voice AI that stays in Europe. Open source. Sub-500ms."
- "Build voice agents that your legal team won't block"

**PH maker's comment:** Write as a human. Include: what changed, why it matters, one concrete use case a developer will recognize, CTA that can be tried without signup. Avoid roadmap promises.

#### Content Engine (Ongoing After Soft Launch)

**Comparison pages (highest-converting content for developer tools):**

| URL | Target Keywords | Monthly Search Potential | Priority |
|-----|----------------|------------------------|---------|
| voiquyr.ai/compare/voiquyr-vs-vapi | "Vapi alternative", "open source Vapi", "Voiquyr vs Vapi" | 1,000–3,000 | #1 |
| voiquyr.ai/compare/voiquyr-vs-retell | "Retell AI alternative", "Voiquyr vs Retell" | 500–1,000 | #2 |
| voiquyr.ai/compare/voiquyr-vs-bland-ai | "Bland AI alternative", "Voiquyr vs Bland" | 300–700 | #3 |
| voiquyr.ai/compare/voiquyr-vs-synthflow | "Synthflow alternative" | 200–400 | #4 |
| voiquyr.ai/vapi-alternatives | "Vapi alternatives", "best Vapi alternative 2026" | Broad | Hub page |
| voiquyr.ai/gdpr-voice-ai-alternatives | "GDPR voice AI platform", "EU voice AI API" | 500–1,000 | Unique moat |

**Tutorial series ("Build X with Voiquyr"):**
1. "Build a Customer Support Voice Agent in 10 Minutes" (Python)
2. "Add Arabic Voice AI to Your Call Center" (unique differentiator — zero competition)
3. "Deploy GDPR-Compliant Voice AI on Hetzner in 15 Minutes" (EU sovereignty + self-hosting)
4. "Replace Vapi with Voiquyr: Migration Guide" (captures switching intent)
5. "Connect Voiquyr to Your Existing Asterisk PBX" (BYOC differentiator)

**YouTube channel strategy:**
- 1 video/week minimum
- Format: Loom-style screen recordings, real terminal, real errors (no studio polish)
- Topics: quickstarts, integration tutorials, architecture explainers, competitor comparisons
- Include copy-paste code in video description + GitHub Gist link
- Open with outcome: "By the end of this video, you will have a GDPR-compliant Arabic voice agent running on your Hetzner server."

---

### Phase 3: EU Market Penetration (Users 1,000 → 10,000)

**Goal:** Voiquyr becomes the default voice AI for EU-conscious organizations.

**Timeline:** Months 3–6 after launch

#### EU Sovereignty Marketing (The Unique Angle No Competitor Has)

**Core message:** "Voiquyr is the only voice AI platform with zero US jurisdiction exposure. EU-native. Self-hosted. Your voice data never touches a US-controlled server."

**Target personas and channel mapping:**

| Persona | Message | Channel |
|---------|---------|---------|
| DPO (Data Protection Officer) | "No CLOUD Act exposure. Customer-controlled encryption. Monthly compliance reports. GDPR Article 44 by design." | LinkedIn, GDPR conference talks, compliance newsletters |
| CISO | "ISO 27001-ready. Full audit trail. Self-hosted in your own infrastructure. EU AI Act risk classification built in." | Security conferences, CISO roundtables, LinkedIn |
| CTO / Engineering Lead | "Open source. Self-host on Hetzner. No vendor lock-in. Apache 2.0. Python SDK. Works with your existing PBX." | HN, dev conferences, Twitter |
| Contact Center Director | "€0.04/min all-in. Keep your existing Asterisk/FreeSWITCH. Arabic + 24 EU languages. BYOC." | Industry conferences, trade publications, LinkedIn |

**EU-specific content calendar:**
- White paper: "Voice AI and the EU AI Act: A Compliance Guide for Enterprises" (PDF lead magnet)
- Blog: "The CLOUD Act vs GDPR: Why US Voice AI Platforms Can't Protect Your Data"
- Landing page: voiquyr.ai/eu-sovereignty (dedicated EU compliance positioning)
- Case study: "How MedGulf Insurance Deployed GDPR-Compliant Arabic Voice AI" (after pilot go-live)
- Webinar: "EU AI Act + Voice: What Changes in August 2026" (compliance deadline content)

#### Conference Strategy (EU Focus)

| Conference | When | Why | Tactic |
|------------|------|-----|--------|
| WeAreDevelopers World Congress (Berlin) | July 2026 | 10,000+ developers, EU-heavy | Submit talk: "Building EU-Sovereign Voice AI Infrastructure" |
| AI & Big Data Expo Europe (Amsterdam) | Sep/Oct 2026 | Enterprise AI buyers | Booth + demo station with live Arabic voice agent |
| KubeCon EU | 2027 | Cloud-native infrastructure audience | Talk: "Running Voice AI Pipelines on K8s with GDPR Constraints" |
| Web Summit (Lisbon) | Nov 2026 | Startup showcase, media | ALPHA startup program application |
| Local meetups (Berlin, Frankfurt, Amsterdam) | Ongoing | Grassroots developer community | Host "Voice AI Hack Night" events |
| Junction Helsinki | Nov 2026 | EU hackathon | Sponsor with Voiquyr API credits; winner features |
| HackZurich | Sep 2026 | EU hackathon | Same |

#### Hackathon Strategy (The Twilio Playbook)

- Sponsor EU hackathons with Voiquyr API credits as prizes: Junction Helsinki, HackZurich, START Hack
- Run a "Voiquyr Voice AI Challenge" — build the best voice agent using Voiquyr, €5,000 in prizes
- Feature winning projects on blog and social — creates content + community simultaneously
- GroupMe was built on Twilio at a hackathon in 2011. The same pattern can work for Voiquyr.

---

### Phase 4: Community Flywheel (Months 6–12)

**Goal:** Self-sustaining community that creates content, integrations, and growth without direct input.

| Initiative | Detail | Model |
|-----------|--------|-------|
| **Launch Week format** | Quarterly: ship one feature per day for a week. PH/HN/Twitter/blog coordinated across all channels. | Supabase model |
| **Voiquyr Builders program** | Community members who create tutorials, integrations, and starter kits get featured, early access, and swag. | SupaSquad model |
| **Integration ecosystem** | Official SDKs for Next.js, Django, Flask, Express. Community connectors for n8n, Make.com, Zapier. | Twilio model |
| **YouTube creator partnerships** | Reach out to voice AI YouTubers who currently create Vapi tutorials. Offer early access + support to create Voiquyr content. | Community-led |
| **Voiquyr Templates** | Pre-built voice agent templates: appointment scheduler, customer support, lead qualification, survey bot, Arabic concierge, EU insurance claims. | Vercel template model |
| **Open-source contributor program** | Highlight contributors in release notes, contributor page, social. First 50 contributors get swag. | Vercel/Supabase model |

---

### Budget Estimate (Bootstrap Mode)

| Category | Monthly Cost | Notes |
|----------|-------------|-------|
| Hosted demo infrastructure (cloud) | €200–500 | Hetzner VPS for public demo; ElevenLabs API for demo calls |
| Domain + hosting (docs, blog) | €50 | Cloudflare Workers / Vercel; Mintlify docs |
| Discord Nitro (server boost) | €10 | Server features: custom invite link, better audio quality |
| Conference attendance (amortized) | €500 avg | 2–3 EU conferences per year; travel + potential booth |
| Hackathon sponsorship (amortized) | €400 avg | 2 hackathons per year; prize credits |
| Content creation tools | €100 | Screen Studio (Mac), Descript, Canva Pro |
| Free tier API credits for users | €500–2,000 | Deepgram + ElevenLabs costs for free trial minutes |
| Press releases (AB Newswire) | €80–160 | 1–2 releases per month |
| **Total (bootstrap mode)** | **€1,840–3,720/mo** | |

**If funded, add:**
- Full-time DevRel hire: €60–80K/year
- Conference sponsorships: €20–50K/year
- Paid YouTube creator partnerships: €2–5K/quarter
- Google Ads (EU-targeted GDPR compliance keywords): €1–2K/month

---

### Success Metrics by Phase

| Phase | Timeline | Key Targets |
|-------|----------|-------------|
| Pre-launch | Now → Sprint 8 | 500 email waitlist signups; 200 Twitter followers |
| Soft launch | Month 1 (Sprint 9) | 100 developers; 200 GitHub stars; first community PR; 1 Discord member makes a call |
| PH launch | Month 2–3 | 1,000 signups; 500+ GitHub stars; Top 5 Product of the Day |
| EU penetration | Month 3–6 | 5,000 users; 1,500 GitHub stars; 1 paying enterprise; 1 published case study |
| Community flywheel | Month 6–12 | 10,000+ users; 3,000+ GitHub stars; 3 paying enterprises; 10+ community contributors; 50+ community tutorials/videos |

---

## Part 6: SEO & AI Search Engine Strategy

### Site Audit Summary

**Current state (voiquyr.com):** Single-page site on Cloudflare Pages. Navigation anchors only: The Problem, Platform, Compare, Pricing. One CTA: "Become a Design Partner."

**Existing differentiators articulated on the site (good — preserve these):**
- Hard data residency by architecture (not certification) — GDPR Article 44
- Region-locked edge nodes: Frankfurt · Bahrain · Mumbai · Singapore
- UAE PDPL, India DPDP Act ready
- Generic SIP adapter (any carrier — Tata, Jio, Mobily, du)
- Arabic dialect support (Egyptian, Gulf, Levantine, Maghrebi, MSA)
- Speculative inference (flash mode) — 40% latency reduction
- Unified local billing (EUR / AED / INR / SGD / JPY)

**SEO problems (all fixable):**

| Problem | Impact | Fix |
|---------|--------|-----|
| Single-page site = 1 keyword opportunity | Critical | Add multi-page structure: /blog, /compare, /docs |
| No robots.txt | AI crawlers may be blocked | Add robots.txt (template below) |
| No sitemap.xml | Google/AI crawlers can't discover pages | Add sitemap.xml (template below) |
| No structured data (schema.org) | Not cited by AI search engines | Add JSON-LD (template below) |
| No llms.txt | LLMs can't navigate key content | Add llms.txt (template below) |
| Comparison tables not individually indexed | Low SEO value | Make them separate pages |

---

### Immediate Technical SEO Actions (Week 1 — Do These First)

#### robots.txt Template

Add at `voiquyr.com/robots.txt`:

```
# Voiquyr robots.txt
# Updated: April 2026

# ─── AI Crawlers — Allow all public content ─────────────
User-agent: GPTBot
Allow: /

User-agent: OAI-SearchBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: anthropic-ai
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: Googlebot
Allow: /

User-agent: Bingbot
Allow: /

User-agent: DuckDuckBot
Allow: /

# ─── All other crawlers ──────────────────────────────────
User-agent: *
Allow: /
Disallow: /api/
Disallow: /admin/
Disallow: /_next/

Sitemap: https://voiquyr.com/sitemap.xml
```

**Cloudflare note:** In Security > Bots, verify GPTBot, PerplexityBot, ClaudeBot are not rate-limited. Test with: `curl -A "GPTBot" https://voiquyr.com/`

#### llms.txt Template

Add at `voiquyr.com/llms.txt`:

```markdown
# Voiquyr

> The only Voice AI platform built for enterprises where data residency is a legal requirement — not a checkbox. EU-native, open-source, GDPR Article 44 compliant by architecture.

Voiquyr is an alternative to Vapi, Retell AI, Bland AI, and Synthflow built specifically for regulated industries in Europe, the Middle East, and Asia where voice data cannot leave the jurisdiction. Unlike US-based competitors, Voiquyr is not subject to CLOUD Act jurisdiction requests when self-hosted on EU infrastructure.

## Core Pages

### Platform Overview
- [Platform](https://voiquyr.com/#platform): Full stack Voice AI — STT, LLM, TTS, telephony, orchestration in one platform

### Compliance & Data Sovereignty
- [GDPR Compliance](https://voiquyr.com/gdpr): How Voiquyr achieves GDPR Article 44 compliance by architecture, not certificate
- [EU Sovereignty](https://voiquyr.com/eu-sovereignty): Data residency, CLOUD Act exposure, and why architecture matters

### Comparisons
- [Voiquyr vs Vapi](https://voiquyr.com/compare/voiquyr-vs-vapi): Feature, compliance, and pricing comparison
- [Voiquyr vs Retell AI](https://voiquyr.com/compare/voiquyr-vs-retell): Feature, compliance, and pricing comparison
- [Voiquyr vs Bland AI](https://voiquyr.com/compare/voiquyr-vs-bland-ai): Feature, compliance, and pricing comparison
- [Vapi Alternatives](https://voiquyr.com/vapi-alternatives): Comprehensive roundup

### Pricing
- [Pricing](https://voiquyr.com/#pricing): Per-minute pricing in EUR, AED, INR, SGD. €0.04/min UCPM.

### Documentation
- [Docs](https://docs.voiquyr.ai): Full developer documentation, API reference, quickstart guides

## Key Facts

- Website: https://voiquyr.com
- Founded: 2024
- Headquarters: European Union
- License: Apache 2.0 (open-source)
- GitHub: https://github.com/ja3ooni/voiqur-platform
- Edge nodes: Frankfurt (EU), Bahrain (GCC), Mumbai (India), Singapore (SE Asia)
- Compliance: GDPR Article 44, UAE PDPL, India DPDP Act 2023, EU AI Act
- Languages: Arabic (5 dialects: Egyptian, Gulf, Levantine, Maghrebi, MSA), Hindi + 12 regional languages, EU low-resource languages via EuroHPC LoRA fine-tuning
- Telephony: Generic SIP adapter (Asterisk, FreeSWITCH, Kamailio, Tata, Jio, Mobily, du)
- Pricing: €0.04/min UCPM; local currency billing (EUR/AED/INR/SGD/JPY)

## Category

Voice AI Platform / AI Voice Agent API / Open-Source Voice AI / GDPR-Compliant Voice AI

## Alternative To

Vapi (vapi.ai), Retell AI (retellai.com), Bland AI (bland.ai), Synthflow (synthflow.ai), ElevenLabs Conversational AI
```

#### Schema.org JSON-LD Template

Add to every page `<head>`:

```json
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "Voiquyr",
  "description": "Open-source, EU-native Voice AI platform for enterprises requiring GDPR compliance and data sovereignty. Real-time conversational voice agents with region-locked edge nodes in Frankfurt, Bahrain, Mumbai, and Singapore. Alternative to Vapi, Retell AI, and Bland AI for regulated industries.",
  "url": "https://voiquyr.com",
  "applicationCategory": "DeveloperApplication",
  "operatingSystem": "Web, Linux, macOS",
  "offers": {
    "@type": "Offer",
    "priceCurrency": "EUR",
    "price": "0.04",
    "priceSpecification": {
      "@type": "UnitPriceSpecification",
      "price": "0.04",
      "priceCurrency": "EUR",
      "unitText": "per minute"
    }
  },
  "featureList": [
    "GDPR Article 44 compliant by architecture",
    "EU data residency",
    "Arabic dialect recognition (5 dialects)",
    "Self-hostable on any infrastructure",
    "Generic SIP adapter (BYOC)",
    "Open-source Apache 2.0",
    "EU AI Act compliance validation",
    "Voice cloning",
    "Speculative inference (Flash Mode)",
    "Multi-currency billing (EUR/AED/INR/SGD/JPY)"
  ],
  "sameAs": [
    "https://github.com/ja3ooni/voiqur-platform",
    "https://www.linkedin.com/company/voiquyr",
    "https://www.producthunt.com/products/voiquyr",
    "https://twitter.com/voiquyr"
  ]
}
```

Also add `Organization` schema at root level and `FAQPage` schema to any FAQ section.

#### sitemap.xml Template

Add at `voiquyr.com/sitemap.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://voiquyr.com/</loc>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://voiquyr.com/compare/voiquyr-vs-vapi</loc>
    <changefreq>monthly</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>https://voiquyr.com/compare/voiquyr-vs-retell</loc>
    <changefreq>monthly</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>https://voiquyr.com/compare/voiquyr-vs-bland-ai</loc>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://voiquyr.com/vapi-alternatives</loc>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://voiquyr.com/gdpr-voice-ai-alternatives</loc>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://voiquyr.com/eu-sovereignty</loc>
    <changefreq>monthly</changefreq>
    <priority>0.9</priority>
  </url>
  <!-- Add all blog posts and docs pages -->
</urlset>
```

---

### Keyword Strategy

Five clusters with priority rankings for Voiquyr's specific positioning:

#### Cluster A — Platform Discovery (Awareness Stage)

| Keyword | Est. Monthly Volume | Competition | Voiquyr Priority |
|---------|--------------------|-----------|----|
| `voice AI API` | 10,000+ | Very High | Content cluster only |
| `voice AI platform` | 8,000+ | Very High | Content cluster only |
| `AI voice agent` | 10,000+ | Very High | Content cluster only |
| `open source voice AI` | 2,000+ | Medium | **Priority — direct match** |
| `self-hosted voice AI` | 800+ | Low-Medium | **Priority — direct match** |
| `voice AI for developers` | 2,000+ | Medium | Docs and tutorials |

#### Cluster B — Competitor Alternatives (High Intent, Decision Stage)

| Keyword | Est. Monthly Volume | Competition | Priority |
|---------|--------------------|-----------|----|
| `Vapi alternative` | 1,000–3,000 | Medium | **#1 Priority** |
| `Retell AI alternative` | 500–1,000 | Low | **#2 Priority** |
| `Bland AI alternative` | 300–700 | Low | **#3 Priority** |
| `open source Vapi alternative` | 100–300 | Very Low | **Win now — 0 competition** |
| `Vapi self hosted` | 100–300 | Very Low | **Win now** |
| `Vapi vs Retell` | 500–1,000 | Low | Comparison page |

#### Cluster C — Compliance & GDPR (Voiquyr's Unique Moat)

| Keyword | Est. Monthly Volume | Competition | Priority |
|---------|--------------------|-----------|----|
| `GDPR voice AI` | 500–1,000 | Low | **Win now** |
| `GDPR compliant voice AI API` | 200–500 | Very Low | **Win now** |
| `EU voice AI platform` | 100–300 | Very Low | **Win now** |
| `voice AI data residency Europe` | <100 | None | **Win now — 0 competition** |
| `voice AI EU AI Act` | <100 | None | **Win now** |
| `voice AI DPDP India` | <100 | None | **Win now — 0 competition** |
| `voice AI UAE PDPL` | <100 | None | **Win now — 0 competition** |

#### Cluster D — Arabic / Regional Language Voice AI

| Keyword | Est. Monthly Volume | Competition | Priority |
|---------|--------------------|-----------|----|
| `Arabic voice AI API` | 100–500 | Very Low | **Win now** |
| `Arabic dialect speech recognition API` | <100 | None | **Win now** |
| `multilingual voice AI Middle East` | <100 | None | **Win now** |
| `Gulf Arabic speech to text API` | <100 | None | **Win now** |

#### Cluster E — Comparison Queries

| Query | Target Content |
|-------|----------------|
| `Vapi vs Retell` | Comparison page + include Voiquyr |
| `best voice AI API 2026` | Roundup post |
| `voice AI platform comparison` | Comparison hub page |
| `Synthflow alternatives` | Alternatives page |
| `ElevenLabs Conversational AI alternative` | Alternatives page |

**SEO strategy:** Win Clusters C and D immediately (zero competition). Build content for Cluster B (high intent, moderate competition). Use Cluster A for AI search visibility through content distribution.

---

### Comparison Page Strategy

**Priority pages to create (in order):**

1. **voiquyr.com/compare/voiquyr-vs-vapi** (highest priority — 1,000–3,000 monthly searches)
2. **voiquyr.com/compare/voiquyr-vs-retell** (500–1,000 monthly searches)
3. **voiquyr.com/compare/voiquyr-vs-bland-ai** (300–700 monthly searches)

**Comparison page structure template:**

```
H1: Voiquyr vs [Competitor]: [Clear framing]
    Example: "Voiquyr vs Vapi: The GDPR-Native Alternative for EU Enterprises"

[Above-the-fold CTA — Design Partner signup link]

## Quick Summary (60–90 words — AI reads this first)
  Direct answer: Voiquyr is the choice when [EU compliance, Arabic, BYOC needed].
  [Competitor] is better for [US-based teams, faster onboarding, established ecosystem].

## Feature Comparison Table (8–12 rows)
  Side-by-side with checkmarks. Include nuanced notes per cell, not just binary.

## Where Voiquyr Wins
  3–5 bullet points with concrete evidence

## Where [Competitor] Wins
  2–3 honest points — credibility requires acknowledging competitor strengths
  (Pages that admit competitor strengths convert better AND rank better)

## Pricing Comparison
  Side-by-side at current rates (update quarterly)

## Who Should Choose Voiquyr
  Clear persona/use-case descriptions

## Who Should Choose [Competitor]
  Honest recommendations — builds trust

## Customer Testimonials / Social Proof
  Real quotes (after pilots go live)

## FAQ Section (use FAQPage schema)
  5–8 Q&As in natural language that mirror developer search queries

[Bottom CTA with contrasting background]
```

**Voiquyr vs Vapi — Core Comparison Matrix (from site data):**

| Capability | Vapi | Retell AI | Bland AI | Synthflow | Voiquyr |
|-----------|------|-----------|----------|-----------|---------|
| True Region-Locked Data Routing | ✗ | ✗ | ✗ | ✗ | ✓ EU + ME + Asia |
| BYOC — Any SIP Carrier | ✗ (Twilio only) | ✗ (Twilio/Telnyx) | Enterprise only | Twilio/BYO | ✓ Generic SIP |
| Arabic Dialect Recognition | ✗ | ✗ | ✗ | ✗ | ✓ 5 Dialects |
| EU Low-Resource Language Fine-Tuning | ✗ | ✗ | ✗ | ✗ | ✓ LoRA Adapters |
| Local Currency Billing | USD only | USD only | USD only | USD only | ✓ EUR/AED/INR/SGD |
| Sovereignty by Architecture | Cert only | Cert only | Self-hosted (complex) | ✗ | ✓ By Design |
| GDPR DPA included | Optional | Optional | Self-managed | Optional | ✓ Per jurisdiction |
| Open-source core | ✗ | ✗ | ✗ | ✗ | ✓ (if Apache 2.0) |
| EU AI Act compliance | ✗ | ✗ | ✗ | ✗ | ✓ (validator built-in) |
| Realistic price/min | $0.13–0.31 | $0.09–0.25 | $0.14–0.20 | $0.11–0.16 | €0.04 (target) |
| End-to-end latency | Sub-500ms | ~780ms | ~800ms | ~420ms | 600–900ms (target) |

---

### GEO/LLMEO Playbook

**The most important insight:** 85% of brand mentions in AI answers come from third-party sources — not the brand's own website. Source: [Foundation Inc GEO guide](https://foundationinc.co/lab/generative-engine-optimization).

**AI citation hierarchy:**

| Platform | Citation Share | Action Required |
|----------|---------------|----------------|
| Reddit | ~23% of top AI citations | Participate genuinely in r/selfhosted, r/privacy, r/devops, r/AIAgents |
| YouTube | ~13% | Create problem-solution tutorial videos |
| Wikipedia | ~6% | Build notability first; add Wikidata entity now |
| Forbes/TechCrunch | ~5% | PR outreach after traction |
| G2/Capterra/TrustRadius | High for product queries | Create G2 profile immediately |
| GitHub | Critical for dev tools | Public repo with great README |

**Golden Prompts — test weekly across ChatGPT, Perplexity, Claude, Gemini:**

Decision stage:
- "What is the best GDPR-compliant voice AI API?"
- "Best open-source Vapi alternative for Europe"
- "Voice AI platform with EU data residency"
- "Vapi alternative for GDPR compliance"
- "Best voice AI API for Arabic language"
- "Voice AI platform comparison Vapi Retell Bland"

Competitor comparison:
- "Vapi vs alternatives for EU companies"
- "Is Vapi GDPR compliant?"
- "Retell AI alternatives"

**Build a weekly GEO scorecard:** Is Voiquyr mentioned? What position? What sources are cited? Track improvement over 90 days.

**Off-site presence strategy:**

| Platform | Priority | Action |
|----------|---------|--------|
| Reddit | 🔴 Critical | Participate in r/selfhosted, r/privacy, r/devops, r/AIAgents, r/VoiceTechnology. 10+ genuine helpful comments before posting about Voiquyr. |
| GitHub | 🔴 Critical | Public repo, comprehensive README, awesome-list submissions |
| G2 | 🔴 High | Create profile immediately (even without reviews — it gets cited) |
| YouTube | 🔴 High | Problem-solution tutorial videos; target developer search queries |
| Crunchbase | 🟡 High | Complete company profile |
| LinkedIn Company | 🟡 High | Complete profile; weekly posts |
| AlternativeTo | 🟡 High | List as alternative to Vapi, Retell, Bland, Synthflow |
| Capterra | 🟡 Medium | AI Voice Assistants category |
| Stack Overflow | 🟡 Medium | Answer GDPR voice AI, self-hosted voice AI questions |
| Wikidata | 🟢 Medium | Add entity (company, product, location, founding date) |
| dev.to | 🟢 Medium | Technical tutorials |
| Press releases | 🟢 Low | AB Newswire ($80/release): 3–5 targeted releases |

---

### 90-Day SEO Action Plan

#### Month 1 — Foundation (Days 1–30)

**Technical (Week 1 — do this first):**
- [ ] Add `robots.txt` with all AI crawler permissions (template above)
- [ ] Create `sitemap.xml` and reference in robots.txt
- [ ] Verify Cloudflare WAF is not blocking AI crawlers
- [ ] Add Organization schema.org JSON-LD to homepage
- [ ] Add SoftwareApplication schema.org JSON-LD to homepage
- [ ] Create `llms.txt` at voiquyr.com/llms.txt
- [ ] Create "Brand Facts" canonical document (consistent entity data across all platforms)
- [ ] Set up Google Search Console; verify domain; submit sitemap

**Content (Week 2–4):**
- [ ] Create first comparison page: `/compare/voiquyr-vs-vapi`
- [ ] Create `/vapi-alternatives` hub page
- [ ] Create first GEO-optimized blog post: "GDPR-Compliant Voice AI: Why Architecture Matters More Than Certifications"
- [ ] Add FAQPage schema to homepage comparison section

**Off-site (Week 2–4):**
- [ ] Submit Voiquyr to AlternativeTo (list as Vapi, Retell, Bland, Synthflow alternatives)
- [ ] Create Crunchbase company profile
- [ ] Create LinkedIn Company Page
- [ ] Create G2 profile (even without reviews)
- [ ] Create Wikidata entity
- [ ] Submit PR to `awesome-european-ai` GitHub list ([github.com/jmbarrancoml/awesome-european-ai](https://github.com/jmbarrancoml/awesome-european-ai))
- [ ] Submit PR to `awesome-ai-voice` ([github.com/wildminder/awesome-ai-voice](https://github.com/wildminder/awesome-ai-voice))

**Measurement:**
- [ ] Define 20 Golden Prompts; test baseline across ChatGPT, Perplexity, Claude, Gemini
- [ ] Set up UTM tracking for AI referrer traffic (chatgpt.com, perplexity.ai referrals)

#### Month 2 — Content + Community (Days 31–60)

**Content:**
- [ ] `/compare/voiquyr-vs-retell` comparison page
- [ ] `/compare/voiquyr-vs-bland-ai` comparison page
- [ ] Blog: "How to Self-Host a Vapi Alternative for EU Compliance" (technical tutorial)
- [ ] Blog: "Arabic Dialect Recognition in Voice AI: A Technical Deep Dive" (targets Cluster D)
- [ ] Update homepage: proper semantic HTML structure (sequential H1→H2→H3)

**Directories:**
- [ ] Submit to Futurepedia, There's An AI For That, Peerlist Launchpad
- [ ] Submit to Capterra (AI Voice Assistants category)
- [ ] Submit to StackShare

**Community:**
- [ ] Start participating in r/selfhosted and r/privacy (10+ non-promotional comments first)
- [ ] Publish first technical article on dev.to
- [ ] Publish first YouTube video: "GDPR-Compliant Voice Agent in 5 Minutes with Voiquyr"

**Press:**
- [ ] Distribute first press release via AB Newswire: "Voiquyr Launches EU-Native Open-Source Voice AI Platform for GDPR-Regulated Industries"

#### Month 3 — Amplification (Days 61–90)

**Content:**
- [ ] `/compare/voiquyr-vs-synthflow` comparison page
- [ ] `/open-source-voice-ai` hub page
- [ ] Blog: "Voice AI Latency: How Speculative Inference Cuts Perceived Lag by 40%"
- [ ] Blog: "EU AI Act and Voice Agents: What Developers Need to Know Before August 2026"

**Hacker News:**
- [ ] Launch "Show HN: Voiquyr — Open-source, GDPR-native Voice AI platform"
  - GitHub repo must be public and polished
  - Docs must be live
  - Live demo required
  - Prepare to respond in real-time for 3 hours post-launch

**AI search check:**
- [ ] Re-run all 20 Golden Prompts — measure improvement vs. Month 1 baseline
- [ ] Identify which sources AI is citing; target gaps
- [ ] If Perplexity cites a list that doesn't include Voiquyr, get on that list

**Metrics to track monthly:**
- Number of AI search citations (manual test of Golden Prompts)
- Organic impressions (Google Search Console)
- Referral traffic from ChatGPT, Perplexity, Claude
- G2 profile views and reviews
- GitHub stars
- Direct signups from organic/AI channels

---

## Part 7: Open Questions & Decisions Needed

### 1. Licensing Decision (CRITICAL — Blocking)

**Status:** ❌ BLOCKING — must resolve before Sprint 9 (making repo public)

**The conflict:** The repository README states Apache 2.0 license. The root LICENSE file states "Private — all rights reserved."

**Options:**

| Option | License | OSS Community | Enterprise Sales | Revenue Impact |
|--------|---------|-------------|----------------|---------------|
| **A — Go Apache 2.0** | Apache 2.0 | ✅ Full OSS adoption possible | ✅ Enterprise can audit code | Users can self-host for free; monetize hosted service + enterprise support |
| **B — Go AGPL-3.0** | AGPL-3.0 | ✅ Strong copyleft protection | ⚠️ Some enterprises avoid AGPL | Forces SaaS users to open-source; protects revenue model |
| **C — Stay Private** | Proprietary | ❌ No OSS community strategy | ✅ Full IP control | All revenue from SaaS; no open-source flywheel |
| **D — BSL 1.1 (time-limited)** | BSL 1.1 | ⚠️ Not a true OSS license | ⚠️ Controversial | Converts to OSS after 4 years; Hashicorp model |
| **E — Dual-license** | Apache 2.0 (community) + commercial | ✅ Community edition | ✅ Enterprise edition | Community free; enterprise features paid |

**Recommendation from research:** Apache 2.0 maximizes developer adoption (Supabase model). But this is a business decision that depends on revenue model. Resolve with legal counsel within Week 1.

---

### 2. Pricing Validation (BLOCKING for launch)

**Status:** ❌ BLOCKING for transparent pricing page

**The claim:** €0.04/min UCPM target.

**Cost breakdown (calculated above):**

| Component | Cost/min | Source |
|-----------|---------|--------|
| Deepgram Nova-3 STT | $0.0077 | [Deepgram pricing](https://deepgram.com/pricing) |
| ElevenLabs Flash TTS | ~$0.0075 | [ElevenLabs pricing](https://elevenlabs.io/pricing/api) |
| Mistral Small LLM | ~$0.0001 | [Price per token](https://pricepertoken.com/pricing-page/model/mistral-ai-mistral-large) |
| Twilio telephony (US) | ~$0.0085–0.013 | Twilio pricing |
| Hetzner infra (amortized) | ~$0.0003 | Based on CX42 at 6K min/mo |
| **Total cost** | **~$0.024–0.029/min** | |
| **Target UCPM at €0.04** | **€0.037 (~$0.040)** | USD/EUR at 0.92 |
| **Implied margin** | **~25–40%** | Depends on FX and volume |

**Decision:** Is 25–40% margin acceptable? At higher volumes, Deepgram and ElevenLabs pricing improves with enterprise plans. Validate with real pilot call data before publishing the pricing page.

**Alternative pricing models to consider:**

| Model | Structure | Pros | Cons |
|-------|-----------|------|------|
| UCPM (current plan) | €0.04/min flat | Simple, predictable | Low margin at current scale |
| Tiered UCPM | €0.06/min (PAYG), €0.04/min (1K+ min/mo) | Higher early margin | More complex |
| Component pricing | STT + LLM + TTS billed separately | Transparent (Retell model) | Users see all costs |
| Subscription + overage | €199/mo = 5,000 min; €0.04 overage | Predictable MRR | Requires minimum commitment |
| Enterprise custom | Negotiated | High margin | Slow sales cycle |

---

### 3. Infrastructure Decisions

**Decision matrix — choose one architecture option:**

| Criteria | Option A: Full Self-Hosted | Option B: Full Cloud | Option C: Hybrid | Option D: Cloud STT + Local LLM/TTS |
|----------|---------------------------|---------------------|-----------------|--------------------------------------|
| GDPR compliance | ✅ Maximum | ⚠️ US companies | ⚠️ Prod = US | ⚠️ STT only |
| Cost at 6K min/mo | €3–5 | ~$111 | ~$20 prod | ~$46 |
| Development velocity | Slower (local deps) | Fastest | Fast | Fast |
| Production latency | 800ms–1.5s | 600–800ms | 600–800ms | 600–900ms |
| Arabic STT quality | ⚠️ (whisper.cpp) | ✅ Deepgram | ✅ Deepgram | ✅ Deepgram |
| Operational risk | Mac Mini uptime | API provider risk | API provider risk (prod) | API + Mac Mini risk |

**Hetzner upgrade decision:**

| Option | Cost | Action |
|--------|------|--------|
| Upgrade CX32 → CX42 (minimum) | €16.40/mo | **Do this now** — unblocks Asterisk deployment |
| Upgrade CX32 → CAX31 ARM | €12.49/mo | Cheaper; ARM fine for Docker workloads |
| Skip cloud VPS; move everything to GEX44 | €184 + €79 setup | Only if budget allows and home-server reliability is a concern |

---

### 4. Domain Strategy

**Options:**

| Domain | Pros | Cons | Cost |
|--------|------|------|------|
| **voiquyr.com** (current) | Already owned/used; Google favors .com for enterprise trust | Generic TLD | Already registered |
| **voiquyr.ai** | Signals AI product; developers associate .ai with AI tools; ElevenLabs uses .io; competitors use various TLDs | More expensive; must register | ~$50–100/year depending on registrar |
| **Both** | voiquyr.com primary; voiquyr.ai redirects to .com | Cost of owning both; potential confusion | ~$60–110/year for both |

**Recommendation from SEO research:** For developer trust and enterprise sales, .com is still the gold standard. If voiquyr.ai is available at a reasonable price, register it and redirect to voiquyr.com. Primary brand domain: voiquyr.com.

---

### 5. Secrets Management Decision

**Status:** K8s secrets currently use `changeme` placeholder values. Must resolve before Sprint 7.

| Option | Complexity | Cost | Best For |
|--------|-----------|------|---------|
| **Sealed Secrets** (Bitnami) | Low | Free | Small team; GitOps workflow |
| **External Secrets Operator** | Medium | Free (requires external store) | Teams with existing AWS/GCP/Azure secrets |
| **HashiCorp Vault** | High | Free (OSS) / $$ (enterprise) | Enterprise customers requiring Vault |
| **Doppler** | Low | $10–$24/mo | Simple SaaS secrets management |

**Recommendation:** Start with Sealed Secrets (lowest complexity, GitOps-compatible). Migrate to External Secrets Operator when enterprise customers require their own secret stores.

---

### 6. MedGulf Arabic Dialect Requirement (BLOCKING pilot)

**Status:** ❌ BLOCKING MedGulf pilot sign-off

**The question (OQ-3 from PRD):** MedGulf requires Jordanian Arabic (Levantine dialect). Is the current Arabic agent + code-switch handler sufficient, or is dialect-specific fine-tuning needed?

**Options:**

| Option | Approach | Effort | Expected WER |
|--------|---------|--------|-------------|
| Deepgram Nova-3 multilingual | Use $0.0092/min multilingual model | Zero extra work | ~15–20% WER (Arabic) |
| whisper.cpp medium + Arabic prompt | Add Arabic language prompt to whisper.cpp | 1 day | ~12–18% WER |
| Fine-tuned Whisper for Levantine | Fine-tune Whisper on Jordanian Arabic dataset | 2–4 weeks + dataset | ~8–12% WER |
| Commercial Arabic STT (Microsoft Azure, Google) | Use Azure Cognitive Services Arabic STT | 1 week integration | ~10–15% WER |
| AssemblyAI or Speechmatics | Specialized multilingual STT providers | 1 week | Varies |

**Decision needed:** Test Deepgram Nova-3 multilingual on a Jordanian Arabic sample call before investing in fine-tuning. If WER is <15%, proceed with Deepgram. If >15%, evaluate fine-tuning.

---

### 7. Shape Digital Partnership Classification

**Status:** Open question (OQ-6 from PRD) — not blocking

**Oman LNG references "Shape Digital" as a partner. Classification affects pricing:**

| Classification | Pricing Model | Revenue Implications |
|----------------|--------------|---------------------|
| Reseller | Wholesale UCPM rate; Shape Digital adds margin | Lower direct revenue; faster market reach |
| Systems Integrator | Project-based integration fee; customer pays Voiquyr directly | Higher direct revenue; SI earns services margin |
| Direct Customer | Standard enterprise UCPM | Simplest model |

**Action:** Clarify with Shape Digital before onboarding Oman LNG. Draft reseller agreement template if reseller model.

---

### 8. Aqaba / MedGulf Launch Sequencing

**Given the 3 pilots waiting, the recommended launch sequence:**

| Priority | Customer | Why First |
|----------|---------|-----------|
| 1 | **MedGulf Insurance** | Arabic + English = validates code-switch handler; most technically challenging; best case study potential for unique differentiator |
| 2 | **InfraTechton Aqaba** | Simpler use case (knowledge base); good for validating RAG tool calls; lower risk |
| 3 | **Oman LNG** | Enterprise complexity; Shape Digital partnership to clarify; use MedGulf learnings first |

---

## Sources & Citations

All pricing, benchmarks, and competitive data sourced from the following research documents and external references:

**Internal research documents:**
- `/home/user/workspace/voiqur-platform-prd.md` — Product Requirements Document ([ja3ooni/voiqur-platform](https://github.com/ja3ooni/voiqur-platform))
- `/home/user/workspace/voiqur_gaps_and_marketing_campaign.md` — Gaps analysis and marketing campaign plan
- `/home/user/workspace/voice_ai_competitors_research.md` — Voice AI competitive landscape research (April 2026)
- `/home/user/workspace/devtool_marketing_research.md` — Developer tool marketing strategies
- `/home/user/workspace/infra_research.md` — Self-hosted infrastructure research
- `/home/user/workspace/seo_ai_search_strategy.md` — SEO and AI search strategy

**Infrastructure pricing:**
- [Achromatic Hetzner comparison](https://www.achromatic.dev/blog/hetzner-server-comparison)
- [CostGoat Hetzner pricing](https://costgoat.com/pricing/hetzner)
- [Hetzner GEX44](https://www.hetzner.com/dedicated-rootserver/gex44/)
- [Hetzner GPU matrix](https://www.hetzner.com/dedicated-rootserver/matrix-gpu/)

**STT benchmarks:**
- [DEV Community M4 whisper benchmark](https://dev.to/theinsyeds/whisper-speech-recognition-on-mac-m4-performance-analysis-and-benchmarks-2dlp)
- [Home Assistant Community faster-whisper on macOS](https://community.home-assistant.io/t/even-faster-whisper-for-local-voice-low-latency-stt/864762)
- [mac-whisper-speedtest GitHub](https://github.com/anvanvan/mac-whisper-speedtest)

**LLM benchmarks:**
- [Reddit M4 Mac Mini test results](https://www.reddit.com/r/LocalLLaMA/comments/1gnefmi/mac_mini_m4_16gb_test_results/)
- [AppleInsider Ollama MLX](https://appleinsider.com/articles/26/03/31/ollama-is-supercharged-by-mlxs-unified-memory-use-on-apple-silicon)

**TTS benchmarks:**
- [CTAIO 5-engine voice test](https://ctaio.dev/en/labs/my-ai-clone/voice-cloning/)
- [ElevenLabs API pricing](https://elevenlabs.io/pricing/api)

**Telephony:**
- [DEV Community Asterisk vs FreeSWITCH](https://dev.to/sheerbittech/freeswitch-vs-asterisk-which-voip-platform-is-right-for-you-5gcn)
- [Samcom Technologies 2026 comparison](https://www.samcomtechnologies.com/blog/asterisk-vs-freeswitch-in-2026-which-voip-platform-should-you-choose)
- [n8n community voice AI thread](https://community.n8n.io/t/is-n8n-suitable-for-real-time-ai-voice-agent-orchestration-with-self-hosted-models-latency-concerns/278487)

**Voice AI latency:**
- [Introl voice AI infrastructure guide 2025](https://introl.com/blog/voice-ai-infrastructure-real-time-speech-agents-asr-tts-guide-2025)
- [Simplismart sub-400ms blog](https://simplismart.ai/blog/real-time-voice-ai-sub-400ms-latency)

**API pricing:**
- [Deepgram pricing](https://deepgram.com/pricing)
- [Price Per Token — Mistral](https://pricepertoken.com/pricing-page/model/mistral-ai-mistral-large)

**Competitive research:**
- [Retell AI — retellai.com](https://www.retellai.com)
- [Vapi — vapi.ai](https://vapi.ai)
- [Synthflow — synthflow.ai](https://synthflow.ai)
- [Vocode — vocode.dev](https://vocode.dev)
- [ElevenLabs — elevenlabs.io](https://elevenlabs.io)

**Market size:**
- Voice AI Agents Market 2024–2034: $2.4B → $47.5B, CAGR 34.8% (Entrepreneur Loop)
- AI Voice Market 2025: $15.54B; 2033 projection: $50.05B at 15.74% CAGR

**GTM / marketing:**
- [Supabase Launch Week](https://supabase.com/blog/supabase-how-we-launch)
- [Twilio developer content playbook](https://www.decibel.vc/articles/the-developer-content-playbook-that-fuels-twilios-plg-at-scale)
- [Vercel/Next.js growth](https://www.reo.dev/blog/how-developer-experience-powered-vercels-200m-growth)
- [HN Show HN tactics](https://www.markepear.dev/blog/dev-tool-hacker-news-launch)
- [Product Hunt dev tool launch](https://www.permit.io/blog/producthunt-howto)

**SEO / GEO:**
- [Foundation Inc GEO guide](https://foundationinc.co/lab/generative-engine-optimization)
- [Xeo Marketing — 20 directories shaping AI citations](https://xeo.marketing/ai-citations-explained-the-20-directories-that-shape-how-ai-recommends-your-brand/)
- [Recomaze robots.txt for AI crawlers](https://audit.recomaze.ai/blog/robots-txt-guide-for-ai-crawlers)
- [GetCito llms.txt guide](https://getcito.com/step-by-step-to-create-and-implement-llms-txt-file)
- [Search Engine Land schema markup in AI search](https://searchengineland.com/schema-markup-ai-search-no-hype-472339)
- [Intergrowth comparison pages](https://intergrowth.com/content-marketing/competitor-comparison-pages/)
- [voiquyr.com](https://voiquyr.com)

---

*Last updated: April 2026 | Next review: After Sprint 2 (first real phone call milestone)*
