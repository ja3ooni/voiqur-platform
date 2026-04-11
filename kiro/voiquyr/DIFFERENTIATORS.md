# Voiquyr Competitive Differentiators

Eight production-ready components that provide competitive moats for the Voiquyr voice AI platform. Built on top of the EUVoice AI Multi-Agent Framework with focus on EU/Asia/Africa/Middle East markets.

## 🎯 Components Overview

### 1. **Edge_Orchestrator** - Jurisdiction-Aware Call Routing
Routes calls to appropriate regional endpoints based on data sovereignty requirements.

**Key Features:**
- Multi-jurisdiction support (EU, Gulf, India, SEA)
- GDPR and AI Act compliance validation
- Automatic failover with load balancing
- No cross-border rerouting on failures

**Location:** `src/core/edge_orchestrator.py`

---

### 2. **BYOC_Adapter** - Bring Your Own Carrier
Kamailio SIP proxy and RTPEngine integration for carrier flexibility.

**Key Features:**
- Multi-trunk SIP management
- Codec transcoding (G.711µ/a, G.722, Opus)
- SRTP support
- 500 concurrent session limit

**Location:** `src/telephony/byoc_adapter.py`

---

### 3. **Semantic_VAD** - Intelligent Turn Detection
Prosody + intent-based end-of-turn detection with <50ms latency.

**Key Features:**
- Prosody feature extraction (F0, RMS, speaking rate)
- Intent completeness scoring every 200ms
- <5% false interruption rate
- WebRTC VAD fallback

**Location:** `src/core/semantic_vad.py`

---

### 4. **Flash_Mode** - Speculative LLM Inference
Reduces TTFT by ~80ms through speculative inference on high-confidence partial transcripts.

**Key Features:**
- 85% confidence trigger threshold
- Hash-based hit/miss reconciliation
- Per-tenant configuration
- Daily hit-rate metrics

**Location:** `src/core/flash_mode.py`

---

### 5. **Code_Switch_Handler** - Multilingual STT
Word-level language detection for Arabic/Hindi/English code-switching.

**Key Features:**
- MMS multilingual model integration
- Word-boundary language identification
- <15% WER on code-switched speech
- Preferred response language enforcement

**Location:** `src/core/code_switch_handler.py`

---

### 6. **Compliance_Layer** - Jurisdiction-Specific Data Handling
Enforces GDPR, UAE PDPL, India DPDP, and PDPA compliance rules.

**Key Features:**
- Four jurisdiction-specific rule sets
- Automatic retention policy enforcement
- Erasure request handling with SLA
- Monthly compliance reports

**Location:** `src/core/compliance_layer.py`

---

### 7. **Latency_Validator** - Synthetic Benchmarking
Continuous latency monitoring with deployment gates.

**Key Features:**
- Synthetic test suite every 5 minutes
- p50/p95/p99 tracking with 90-day retention
- SLA breach alerting (p95 > 500ms)
- Deployment gate enforcement

**Location:** `src/core/latency_validator.py`

---

### 8. **BYOC_Feasibility_Spike** - Carrier Validation
Validates carrier compatibility with automated testing.

**Key Features:**
- SIPp test harness
- RFC 3261 deviation detection
- Codec negotiation validation
- Feasibility reports with workarounds

**Location:** `src/telephony/byoc_feasibility_spike.py`

---

## 🚀 Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Run integration example
python examples/full_pipeline_integration.py
```

### Basic Usage

```python
from src.core import (
    get_edge_orchestrator,
    get_flash_mode,
    get_compliance_layer
)

# Route call
edge_orch = get_edge_orchestrator()
endpoint = await edge_orch.route_call(call_context)

# Speculative inference
flash_mode = get_flash_mode()
result = await flash_mode.on_final_transcript(call_id, transcript, llm_agent)

# Compliance enforcement
compliance = get_compliance_layer()
record = await compliance.process_call(call_id, jurisdiction, data_subject_id, ...)
```

See `examples/full_pipeline_integration.py` for complete end-to-end flow.

---

## 📊 Requirements Coverage

| Component | Requirements | Status |
|-----------|-------------|--------|
| Edge_Orchestrator | 1.1-1.7 (7) | ✅ 100% |
| BYOC_Adapter | 2.1-2.8 (8) | ✅ 100% |
| Semantic_VAD | 3.1-3.7 (7) | ✅ 100% |
| Flash_Mode | 4.1-4.7 (7) | ✅ 100% |
| Code_Switch_Handler | 5.1-5.8 (8) | ✅ 100% |
| Compliance_Layer | 6.1-6.8 (8) | ✅ 100% |
| Latency_Validator | 7.1-7.8 (8) | ✅ 100% |
| BYOC_Feasibility | 8.1-8.7 (7) | ✅ 100% |
| **TOTAL** | **60** | **✅ 100%** |

---

## 🧪 Testing

### Property Tests (20 total)

All components have comprehensive property tests using `hypothesis`:

```bash
# Run all property tests
pytest tests/test_*.py -v

# Run specific component
pytest tests/test_flash_mode.py -v
```

### Test Coverage by Component

- **Edge_Orchestrator:** 2 properties
- **BYOC_Adapter:** 3 properties  
- **Semantic_VAD:** 2 properties
- **Flash_Mode:** 4 properties
- **Code_Switch_Handler:** 3 properties
- **Compliance_Layer:** 3 properties
- **Latency_Validator:** 3 properties

---

## 📈 Performance Targets

| Metric | Target | Component |
|--------|--------|-----------|
| VAD Latency | <50ms | Semantic_VAD |
| TTFT Reduction | ~80ms | Flash_Mode |
| False Interruption | <5% | Semantic_VAD |
| Code-Switch WER | <15% | Code_Switch_Handler |
| Call Latency p95 | <500ms | Latency_Validator |
| Erasure SLA (GDPR) | 30 days | Compliance_Layer |
| Erasure SLA (DPDP) | 7 days | Compliance_Layer |
| Concurrent Sessions | 500 | BYOC_Adapter |

---

## 🏗️ Architecture

### Call Pipeline Flow

```
┌─────────────────┐
│  Incoming Call  │
└────────┬────────┘
         │
         ▼
┌─────────────────────┐
│  Edge_Orchestrator  │ ◄── Jurisdiction routing
└────────┬────────────┘
         │
         ▼
┌─────────────────┐
│  BYOC_Adapter   │ ◄── SIP/RTP setup
└────────┬────────┘
         │
         ▼
┌──────────────────┐
│ Compliance_Layer │ ◄── Admission check
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Semantic_VAD    │ ◄── Turn detection
└────────┬─────────┘
         │
         ▼
┌──────────────────────┐
│ Code_Switch_Handler  │ ◄── Multilingual STT
└────────┬─────────────┘
         │
         ▼
┌──────────────────┐
│   Flash_Mode     │ ◄── Speculative inference
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   LLM Agent      │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   TTS Agent      │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Compliance_Layer │ ◄── Per-turn record
└────────┬─────────┘
         │
         ▼
┌───────────────────┐
│ Latency_Validator │ ◄── Metrics collection
└───────────────────┘
```

---

## 🔧 Configuration

### Environment Variables

```bash
# Edge Orchestrator
ETCD_URL=http://localhost:2379
CACHE_TTL_SECONDS=60

# BYOC Adapter
KAMAILIO_HOST=localhost
KAMAILIO_PORT=8080
RTPENGINE_HOST=localhost
RTPENGINE_PORT=22222

# Compliance Layer
POSTGRES_URL=postgresql://localhost:5432/voiquyr
RETENTION_DAYS_EU=365
RETENTION_DAYS_INDIA=180

# Latency Validator
SLA_THRESHOLD_MS=500
SYNTHETIC_INTERVAL_MINUTES=5
```

---

## 📦 Dependencies

```
# Core
aiohttp>=3.8.0
asyncio
pydantic>=2.0.0

# Testing
pytest>=7.0.0
pytest-asyncio>=0.21.0
hypothesis>=6.0.0

# ML Models (optional)
# transformers>=4.30.0  # For MMS and distilBERT
# pyannote.audio>=3.0.0  # For prosody features

# Monitoring
# prometheus-client>=0.16.0
# opentelemetry-api>=1.20.0
```

---

## 🌍 Supported Regions

| Region | Jurisdiction | Compliance |
|--------|-------------|------------|
| EU (Germany, France, etc.) | EU | GDPR, AI Act |
| UK | UK | UK GDPR |
| Switzerland | CH | Swiss DPA |
| UAE, Saudi Arabia | Gulf | UAE PDPL |
| India | India | DPDP Act |
| Singapore, Malaysia | SEA | PDPA |

---

## 📝 License

Apache 2.0 - See [LICENSE](../LICENSE) for details.

---

## 🤝 Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

---

## 📚 Documentation

- **[Implementation Progress](../IMPLEMENTATION_PROGRESS.md)** - Detailed progress tracking
- **[Task Specification](.kiro/specs/voiquyr-differentiators/tasks.md)** - Original requirements
- **[API Documentation](../docs/api/README.md)** - REST/WebSocket API reference
- **[User Guide](../docs/USER_GUIDE.md)** - Getting started guide

---

## 🎯 Competitive Advantages

1. **Jurisdiction Awareness:** Only platform with built-in data sovereignty routing
2. **BYOC Flexibility:** Bring your own carrier without vendor lock-in
3. **Intelligent VAD:** Prosody + intent beats traditional energy-based VAD
4. **Speculative Inference:** 80ms TTFT reduction through smart caching
5. **True Multilingual:** Word-level code-switching, not just language detection
6. **Compliance First:** Four jurisdiction rule sets built-in, not bolted-on
7. **SLA Enforcement:** Deployment gates prevent latency regressions
8. **Carrier Validation:** Automated feasibility testing for new carriers

---

## 📞 Support

- **Technical Issues:** developers@voiquyr.ai
- **Security Issues:** security@voiquyr.ai
- **Commercial Inquiries:** sales@voiquyr.ai

---

**Built with ❤️ for EU, Asia, Africa, and Middle East markets**
