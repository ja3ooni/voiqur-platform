# Tasks - Voiquyr Missing Implementations

## Task Overview

**Total Tasks**: 156 tasks across 4 phases
**Estimated Duration**: 16 weeks (4 months)

---

## Phase 1: Core Voice Pipeline (Tasks 1-52)

### Tasks 1-16: STT Integration

#### 1.1 Deepgram Provider Setup (Tasks 1-4)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 1 | Install Deepgram SDK (`pip install deepgram`) | 1h | P0 |
| 2 | Create `src/stt/providers/deepgram.py` provider class | 4h | P0 |
| 3 | Implement streaming transcription with ondrely mode | 8h | P0 |
| 4 | Add provider selection logic in `stt_agent.py` | 2h | P0 |

#### 1.2 Voxtral Fallback (Tasks 5-8)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 5 | Install Mistral SDK | 1h | P0 |
| 6 | Create `src/stt/providers/voxtral.py` provider class | 4h | P0 |
| 7 | Implement audio transcription API | 4h | P0 |
| 8 | Add fallback chain: Deepgram → Voxtral → Error | 2h | P0 |

#### 1.3 Error Handling (Tasks 9-12)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 9 | Implement 5-second timeout | 2h | P0 |
| 10 | Add structured error responses | 2h | P1 |
| 11 | Log provider name + request_id on errors | 1h | P1 |
| 12 | Create STTError exception class | 1h | P1 |

#### 1.4 Language Support (Tasks 13-16)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 13 | Add Arabic language detection | 2h | P1 |
| 14 | Add English/Arabic mixed speech support | 4h | P1 |
| 15 | Implement word-level language tags | 4h | P2 |
| 16 | Test mixed-language transcription | 2h | P1 |

### Tasks 17-32: LLM Integration

#### 2.1 Mistral API Setup (Tasks 17-20)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 17 | Verify Mistral SDK installed | 1h | P0 |
| 18 | Create `src/llm/providers/mistral.py` provider | 4h | P0 |
| 19 | Implement `MistralClient.chat()` integration | 4h | P0 |
| 20 | Test API key auth flow | 1h | P0 |

#### 2.2 Streaming Response (Tasks 21-24)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 21 | Implement token streaming | 4h | P0 |
| 22 | Create async iterator interface | 2h | P1 |
| 23 | Test first-sentence-before-full-response | 2h | P1 |
| 24 | Add streaming performance metrics | 2h | P2 |

#### 2.3 Ollama Fallback (Tasks 25-28)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 25 | Create `src/llm/providers/ollama.py` provider | 4h | P0 |
| 26 | Implement local endpoint detection | 1h | P0 |
| 27 | Add Ollama → Mistral fallback chain | 2h | P0 |
| 28 | Test offline inference | 2h | P1 |

#### 2.4 Remove Mock Code (Tasks 29-32)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 29 | Delete `_generate_mock_response()` method | 1h | P0 |
| 30 | Find and remove all mock response paths | 4h | P0 |
| 31 | Verify no hardcoded responses remain | 2h | P0 |
| 32 | Test idempotence of context | 2h | P1 |

### Tasks 33-48: TTS Integration

#### 3.1 ElevenLabs Setup (Tasks 33-36)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 33 | Install ElevenLabs SDK | 1h | P0 |
| 34 | Create `src/tts/providers/elevenlabs.py` | 4h | P0 |
| 35 | Implement `text_to_speech.stream()` | 6h | P0 |
| 36 | Verify <200ms first-chunk latency | 2h | P0 |

#### 3.2 Piper Fallback (Tasks 37-40)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 37 | Install Piper TTS | 2h | P0 |
| 38 | Create `src/tts/providers/piper.py` provider | 4h | P0 |
| 39 | Implement local synthesis | 4h | P0 |
| 40 | Add ElevenLabs → Piper fallback | 2h | P0 |

#### 3.3 Remove Sine Waves (Tasks 41-44)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 41 | Remove all sine wave generation code | 2h | P0 |
| 42 | Remove silence buffer returns | 1h | P0 |
| 43 | Verify no mock audio in codebase | 2h | P0 |
| 44 | Test STT→TTS round-trip property | 4h | P1 |

#### 3.4 Voice Features (Tasks 45-48)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 45 | Add voice ID selection | 2h | P1 |
| 46 | Implement language parameter | 2h | P1 |
| 47 | Add emotion-aware synthesis | 4h | P2 |
| 48 | Test multi-language synthesis | 2h | P1 |

### Tasks 49-52: Pipeline Integration

#### 4.1 Chain Connection (Tasks 49-50)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 49 | Create `src/voice/pipeline.py` orchestrator | 8h | P0 |
| 50 | Connect STT→LLM→TTS in order | 4h | P0 |

#### 4.2 Testing & Optimization (Tasks 51-52)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 51 | Full E2E test with real audio | 4h | P0 |
| 52 | Optimize E2E latency <2,000ms | 4h | P1 |

---

## Phase 2: Telephony & Billing (Tasks 53-104)

### Tasks 53-68: Twilio Integration

#### 5.1 Inbound Calls (Tasks 53-56)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 53 | Create `src/telephony/twilio_bridge.py` | 6h | P0 |
| 54 | Implement `/twilio/voice` webhook | 4h | P0 |
| 55 | Add TwiML response generator | 4h | P0 |
| 56 | Test inbound call flow | 2h | P0 |

#### 5.2 Signature Validation (Tasks 57-60)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 57 | Implement signature validation | 4h | P0 |
| 58 | Return 403 on invalid signature | 1h | P0 |
| 59 | Log all rejections | 1h | P1 |
| 60 | Test signature verification | 2h | P0 |

#### 5.3 Media Streaming (Tasks 61-64)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 61 | Create media stream handler | 6h | P0 |
| 62 | Implement audio ↔ Call Controller bridge | 4h | P0 |
| 63 | Add real-time streaming | 4h | P0 |
| 64 | Test media stream latency | 2h | P1 |

#### 5.4 Outbound Calls (Tasks 65-68)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 65 | Implement `/twilio/calls` endpoint | 4h | P0 |
| 66 | Add Twilio REST API integration | 4h | P0 |
| 67 | Test outbound call initiation | 2h | P0 |
| 68 | Add status callbacks | 2h | P1 |

### Tasks 69-80: Asterisk Integration

#### 6.1 AudioSocket Handler (Tasks 69-72)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 69 | Create `src/telephony/asterisk_bridge.py` | 6h | P0 |
| 70 | Implement TCP connection handler | 6h | P0 |
| 71 | Add frame parser/serializer | 4h | P0 |
| 72 | Test connection handling | 2h | P0 |

#### 6.2 Audio Processing (Tasks 73-76)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 73 | Forward frames to Call Controller | 4h | P0 |
| 74 | Return synthesized audio frames | 4h | P0 |
| 75 | Test audio round-trip | 2h | P0 |
| 76 | Measure latency <1,500ms | 1h | P1 |

#### 6.3 Session Management (Tasks 77-80)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 77 | Handle unexpected disconnects | 2h | P0 |
| 78 | Log disconnection events | 1h | P1 |
| 79 | Send call-ended to Billing | 2h | P0 |
| 80 | Test cleanup on disconnect | 2h | P0 |

### Tasks 81-92: Stripe Billing

#### 7.1 API Integration (Tasks 81-84)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 81 | Update `stripe_service.py` with real API | 4h | P0 |
| 82 | Implement usage record creation | 4h | P0 |
| 83 | Add test/key detection logic | 2h | P0 |
| 84 | Test real Stripe charges | 2h | P0 |

#### 7.2 Webhook Processing (Tasks 85-88)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 85 | Implement `/webhooks/stripe` endpoint | 4h | P0 |
| 86 | Add webhook signature verification | 2h | P0 |
| 87 | Implement idempotency check | 2h | P0 |
| 88 | Test webhook processing | 2h | P0 |

#### 7.3 Refunds (Tasks 89-92)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 89 | Implement refund API | 4h | P0 |
| 90 | Add 3x retry with exponential backoff | 2h | P0 |
| 91 | Record refund reason | 1h | P1 |
| 92 | Test refund flow | 2h | P0 |

### Tasks 93-104: Currency & UCPM

#### 8.1 Exchange Rates (Tasks 93-96)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 93 | Create `currency_manager.py` | 4h | P0 |
| 94 | Integrate ECB/external rate API | 4h | P0 |
| 95 | Add Redis caching | 2h | P0 |
| 96 | Test rate fetching | 2h | P0 |

#### 8.2 Rate Change Notification (Tasks 97-100)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 97 | Track previous rate | 2h | P1 |
| 98 | Detect >5% change | 2h | P1 |
| 99 | Queue notification on change | 4h | P2 |
| 100 | Test change detection | 2h | P1 |

#### 8.3 UCPM Calculator (Tasks 101-104)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 101 | Update `ucpm_calculator.py` | 4h | P0 |
| 102 | Implement tiered pricing | 2h | P0 |
| 103 | Add multi-currency support | 4h | P0 |
| 104 | Test UCPM calculation | 2h | P0 |

---

## Phase 3: Developer Platform (Tasks 105-130)

### Tasks 105-112: Python SDK

#### 9.1 Package Setup (Tasks 105-108)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 105 | Create `voiquyr/` package structure | 4h | P0 |
| 106 | Implement VoiquyrClient class | 6h | P0 |
| 107 | Add request/response handling | 4h | P0 |
| 108 | Test basic API calls | 2h | P0 |

#### 9.2 Methods (Tasks 109-112)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 109 | Implement `make_call()` | 4h | P0 |
| 110 | Implement `list_agents()` | 2h | P0 |
| 111 | Implement audio streaming | 4h | P1 |
| 112 | Add VoiquyrError exception | 2h | P0 |

### Tasks 113-120: TypeScript SDK

#### 10.1 Package Setup (Tasks 113-116)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 113 | Create `@voiquyr/sdk` package | 4h | P0 |
| 114 | Add TypeScript definitions | 4h | P0 |
| 115 | Implement VoiquyrClient | 6h | P0 |
| 116 | Test basic API calls | 2h | P0 |

#### 10.2 Publishing (Tasks 117-120)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 117 | Configure npm publishing | 2h | P0 |
| 118 | Publish to npm (beta) | 1h | P0 |
| 119 | Verify install + usage | 2h | P0 |
| 120 | Create README with examples | 2h | P1 |

### Tasks 121-126: Command Center

#### 11.1 Dashboard (Tasks 121-123)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 121 | Connect WebSocket for live updates | 4h | P0 |
| 122 | Display active calls, total, duration | 4h | P0 |
| 123 | Implement reconnection logic | 2h | P1 |

#### 11.2 Agent Config (Tasks 124-126)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 124 | List agents from API | 4h | P0 |
| 125 | Create/edit agent form | 6h | P0 |
| 126 | Test CRUD operations | 2h | P0 |

### Tasks 127-130: Documentation

#### 12.1 Guides (Tasks 127-130)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 127 | Create Quickstart guide | 4h | P0 |
| 128 | Document environment setup | 2h | P0 |
| 129 | Write API reference | 6h | P1 |
| 130 | Create WebRTC demo page | 8h | P1 |

---

## Phase 4: Production Readiness (Tasks 131-156)

### Tasks 131-138: Database Migrations

#### 13.1 Alembic Setup (Tasks 131-134)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 131 | Initialize Alembic | 2h | P0 |
| 132 | Create initial migration | 4h | MIGRATION |
| 133 | Test upgrade/downgrade | 2h | P0 |
| 134 | Add agent table migration | 4h | P0 |

#### 13.2 Additional Migrations (Tasks 135-138)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 135 | Add call table migration | 4h | P0 |
| 136 | Add usage_records table | 2h | P0 |
| 137 | Test in CI pipeline | 2h | P0 |
| 138 | Remove `Base.metadata.create_all()` | 2h | P0 |

### Tasks 139-146: CI/CD

#### 14.1 GitHub Actions (Tasks 139-142)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 139 | Create `.github/workflows/ci.yml` | 6h | P0 |
| 140 | Add pytest execution | 2h | P0 |
| 141 | Add Alembic in CI | 2h | P0 |
| 142 | Add Docker build | 4h | P0 |

#### 14.2 Publishing (Tasks 143-146)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 143 | Add image push on merge | 2h | P0 |
| 144 | Add test on PR | 2h | P0 |
| 145 | Add coverage check | 2h | P1 |
| 146 | Configure branch protection | 2h | P1 |

### Tasks 147-152: Metrics

#### 15.1 Prometheus (Tasks 147-150)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 147 | Create `src/monitoring/metrics.py` | 4h | P0 |
| 148 | Add counter/histogram definitions | 4h | P0 |
| 149 | Implement `/metrics` endpoint | 2h | P0 |
| 150 | Test scrape response | 2h | P0 |

#### 15.2 K8s Integration (Tasks 151-152)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 151 | Add ServiceMonitor | 2h | P1 |
| 152 | Configure scrape annotations | 2h | P1 |

### Tasks 153-156: Security & Tests

#### 16.1 Kubernetes Secrets (Tasks 153-154)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 153 | Remove all `changeme` values | 4h | P0 |
| 154 | Add Sealed Secrets or ESO | 6h | P0 |

#### 16.2 Test Coverage (Tasks 155-156)
| ID | Task | Estimate | Priority |
|----|------|----------|----------|
| 155 | Write tests for 42 zero-coverage modules | 16h | P0 |
| 156 | Achieve 70% line coverage | 8h | P0 |

---

## Dependencies Map

```
Task 1 ──► Task 2 ──► Task 3 ──► Task 4
                         │
                         ▼ (requires)
Task 9 ◄── Task 10 ◄── Task 11 ◄── Task 12

Task 17 ──► Task 18 ──► Task 19 ──► Task 20
  │
  └──► Task 29 ◄── Task 30 ◄── Task 31 ◄── Task 32

Task 33 ──► Task 34 ──► Task 35 ──► Task 36
  │
  └──► Task 41 ◄── Task 42 ◄── Task 43 ◄── Task 44

Task 49 ◄── Task 50 ◄── [All Phase 1 tasks complete]

Task 53 ──► Task 54 ──► Task 55 ──► Task 56
  │            │
  └──► Task 57 ◄── Task 58 ◄── Task 59 ◄── Task 60

Task 81 ◄── Task 82 ◄── Task 83 ◄── Task 84
  │
  └──► Task 85 ◄── Task 86 ◄── Task 87 ◄── Task 88

Task 105 ──► Task 107 ──► Task 109 ──► Task 110
  │
  └──► Task 113 ◄── Task 114 ◄── Task 115 ◄── Task 116

Task 131 ◄── Task 132 ◄── Task 133 ◄── Task 134
  │
  └──► Task 139 ◄── Task 140 ◄── Task 141 ◄── Task 142

Task 147 ◄── Task 148 ◄── Task 149 ◄── Task 150
```

---

## Task Status Legend

| Status | Description |
|--------|-------------|
| P0 | Must have - blocking |
| P1 | Should have - important |
| P2 | Nice to have - enhancement |

---

## Sprint Assignment

### Sprint 1.1 (Week 1)
Tasks: 1, 2, 17, 18

### Sprint 1.2 (Week 2)
Tasks: 3, 4, 5, 6, 19, 20

### Sprint 1.3 (Week 3)
Tasks: 7, 8, 9, 33, 34, 35

### Sprint 1.4 (Week 4)
Tasks: 10, 36, 49, 50, 51, 52

### Sprint 2.1 (Week 5)
Tasks: 53, 54, 55, 56, 57

### Sprint 2.2 (Week 6)
Tasks: 58, 69, 70, 71, 72

### Sprint 2.3 (Week 7)
Tasks: 81, 82, 83, 84, 85

### Sprint 2.4 (Week 8)
Tasks: 86, 93, 94, 95, 101

### Sprint 3.1 (Week 9)
Tasks: 105, 106, 107, 108

### Sprint 3.2 (Week 10)
Tasks: 109, 110, 111, 112, 113

### Sprint 3.3 (Week 11)
Tasks: 114, 121, 122, 124

### Sprint 3.4 (Week 12)
Tasks: 115, 125, 127, 130

### Sprint 4.1 (Week 13)
Tasks: 131, 132, 133, 134

### Sprint 4.2 (Week 14)
Tasks: 135, 139, 140, 141

### Sprint 4.3 (Week 15)
Tasks: 142, 147, 148, 149

### Sprint 4.4 (Week 16)
Tasks: 150, 153, 155, 156

---

Last Updated: April 2026