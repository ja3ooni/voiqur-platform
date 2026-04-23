# Design Document - Voiquyr Missing Implementations

## Overview

This document provides the technical architecture for implementing the missing Voiquyr platform components as specified in the requirements document. The design addresses all 25 requirements needed to replace stub/mock implementations with production-ready components.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Voiquyr Platform                                │
├─────────────────────────────────────────────────────────────────────┤
│  Telephony Layer                                                    │
│  ┌─────────┐  ┌───────────┐  ┌─────────────┐  ┌─────────────────────┐   │
│  │ Twilio │  │ Asterisk │  │ WebRTC Demo │  │ Public Demo Number  │   │
│  │HTTP/Web│  │AudioSocket│  │   Browser  │  │    VoIP/PSTN       │   │
│  └────┬────┘  └────┬────┘  └──────┬────┘  └──────────┬────────┘   │
│       │            │             │               │                 │           │
│  ┌─────┴────────────┴─────────────┴───────────────┴─────────────┴────┐  │
│  │                    Call Controller                         │        │
│  │         (Audio Bridge & Session Management)            │        │
│  └────────────────────────────┬──────────────────────────────┘        │
│                               │                                     │
│  ┌───────────────────────────┴───────────────────────────────┐     │
│  │                   Voice Pipeline                         │        │
│  │  ┌─────────┐   ┌─────────┐   ┌─────────┐           │        │
│  │  │  STT   │──▶│   LLM   │──▶│   TTS   │           │        │
│  │  │ Agent  │   │  Agent  │   │  Agent  │           │        │
│  │  └────────┘   └────────┘   └────────┘           │        │
│  └───────────────────────────────────────────────┘            │
│                               │                             │
│  ┌───────────────────────────┴───────────────────────────────┐     │
│  │                   Billing Engine                     │        │
│  │  ┌──────────┐  ┌───────────┐  ┌──────────────┐    │        │
│  │  │ UCPM    │  │  Stripe  │  │ Exchange   │    │        │
│  │  │Calc    │  │ Service  │  │ Rate API   │    │        │
│  │  └────────┘  └─────────┘  └────────────┘    │        │
│  └───────────────────────────────────────────────┘            │
└──────────────────────────────────────────────────────────────┘

                        │
          ┌────────────┴────────────┐
          │     External APIs       │
┌─────────┴──────┐  ┌────────────┴────┐
│  Python SDK    │  │ TypeScript SDK   │
│  (PyPI)      │  │ (npm)          │
└──────────────┘  └────────────────┘

          ┌────────────┴────────────┐
          │    Frontend UI         │
┌─────────┴──────┐  ┌────────────┴────┐
│ Command Center │  │  WebRTC Landing  │
│ (React/MUI)  │  │  Page Demo     │
└──────────────┘  └────────────────┘
```

---

## 1. Voice Pipeline Architecture

### 1.1 STT Agent Design

**Component**: `src/agents/stt_agent.py`

#### Provider Selection Logic
```
DEEPGRAM_API_KEY present?
    ├── YES → Use Deepgram Nova-3 Streaming API
    └── NO → MISTRAL_API_KEY present?
              ├── YES → Use Mistral Voxtral API
              └── NO → Raise ConfigurationError
```

#### Deepgram Integration
```python
class DeepgramProvider:
    async def connect() -> AsyncIterator[Transcript]:
        """Use Deepgram SDK with ondrely mode"""
        async with DeepgramClient(api_key) as dg:
            async with dg.listen.ontrelay(model="nova-3", punctuate=True) as stream:
                async for transcript in stream:
                    yield transcript
```

#### Voxtral Integration (Fallback)
```python
class VoxtralProvider:
    async def transcribe(audio_chunk: bytes) -> Transcript:
        """Use Mistral Voxtral via API"""
        client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
        result = await client.audio.transcribe(
            model="voxtral-24b",
            audio=audio_chunk
        )
        return Transcript(text=result.text, confidence=result.confidence)
```

#### Error Handling
- Timeout: 5 seconds
- Log: provider name, request_id, error details
- Return: `STTError` with structured error response

### 1.2 LLM Agent Design

**Component**: `src/agents/llm_agent.py`

#### Provider Selection Logic
```
MISTRAL_API_KEY present?
    ├── YES → Use Mistral Small API via MistralClient.chat()
    └── NO → OLLAMA_ENDPOINT configured?
              ├── YES → Use local Ollama
              └── NO → Raise ConfigurationError
```

#### Streaming Implementation
```python
async def generate_stream(prompt: str) -> AsyncIterator[str]:
    """Stream tokens as they are generated"""
    client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
    
    stream = await client.chat.stream(
        model="mistral-small-3.1-2506",
        messages=[{"role": "user", "content": prompt}]
    )
    
    async for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
```

#### Context Management
- 32k token window
- Conversation history persistence
- Tool calling support via OpenAI function format

### 1.3 TTS Agent Design

**Component**: `src/agents/tts_agent.py`

#### Provider Selection Logic
```
ELEVENLABS_API_KEY present?
    ├── YES → Use ElevenLabs Flash
    │         First chunk within 200ms
    └── NO → Use Piper TTS (local)
              First chunk within 300ms
```

#### ElevenLabs Integration
```python
class ElevenLabsProvider:
    async def synthesize(text: str) -> AsyncIterator[bytes]:
        """Stream audio chunks from ElevenLabs"""
        async with ElevenLabs(api_key=api_key) as el:
            async for chunk in el.text_to_speech.stream(
                model_id="eleven_flash_v2",
                text=text,
                optimize_latency=3
            ):
                yield chunk
```

#### Piper TTS Fallback
```python
class PiperProvider:
    async def synthesize(text: str) -> bytes:
        """Use local Piper TTS engine"""
        result = subprocess.run(
            ["piper", "--model", model_path, "--text", text],
            capture_output=True
        )
        return result.audio
```

---

## 2. Telephony Integration

### 2.1 Twilio Bridge

**Component**: `src/telephony/twilio_bridge.py`

#### Inbound Call Flow
```
Twilio Webhook → Validate Signature → Establish Media Stream 
            → Route to Call Controller → Stream Audio ↔ Twilio
```

#### Key Implementation
```python
class TwilioBridge:
    async def handle_inbound_call(self, request: Request):
        # 1. Validate Twilio signature
        if not await self.validate_signature(request):
            raise HTTPException(403, "Invalid signature")
        
        # 2. Accept call and create media stream URL
        media_url = await self.create_media_stream()
        
        # 3. Route to Call Controller
        await self.call_controller.accept_call(
            call_sid=request.form["CallSid"],
            media_stream=media_url
        )
        
        # 4. Return TwiML with media stream instructions
        return TwiMLResponse(
            connect(method="stream",
            attrs={"url": media_url}
        )
```

#### Outbound Call
```python
async def initiate_outbound(to_number: str, agent_id: str):
    """Make outbound call via Twilio REST API"""
    call = await self.twilio.calls.create(
        to=f"client:{to_number}",
        from_=self.config.phone_number,
        url=f"{self.base_url}/twilio/voice"
    )
    return call.sid
```

### 2.2 Asterisk AudioSocket

**Component**: `src/telephony/asterisk_bridge.py`

#### Connection Handling
```python
class AsteriskBridge:
    async def handle_connection(self, reader: asyncio.StreamReader):
        """Handle incoming AudioSocket connection"""
        while True:
            frame = await reader.readframe()
            if frame is None:
                break
            # Forward to Call Controller
            await self.process_audio_frame(frame)
```

---

## 3. Billing Engine

### 3.1 UCPM Calculator

**Component**: `src/billing/ucpm_calculator.py`

```python
@dataclass
class UCPMRate:
    stt_per_minute: Decimal    # Deepgram tiered pricing
    llm_per_token: Decimal    # Input + Output tokens
    tts_per_character: Decimal
    
    def calculate(self, usage: UsageMetrics) -> Decimal:
        total = (
            usage.stt_minutes * self.stt_per_minute +
            usage.input_tokens * self.llm_per_token +
            usage.output_tokens * self.llm_per_token +
            usage.tts_characters * self.tts_per_character
        )
        return total
```

### 3.2 Stripe Service

**Component**: `src/billing/stripe_service.py`

```python
class StripeService:
    async def create_usage_record(self, customer_id: str, usage: UsageMetrics):
        # 1. Calculate UCPM charge
        amount = self.ucpm_calculator.calculate(usage)
        
        # 2. Create Stripe Usage Record
        record = await self.stripe.usage_records.create(
            subscription_item=self.get_subscription_item(customer_id),
            quantity=int(amount * 100)  # cents
        )
        
        return record
    
    async def process_webhook(self, payload: bytes, signature: str):
        # Verify webhook signature
        event = self.stripe.webhook.construct_event(
            payload, 
            signature,
            os.getenv("STRIPE_WEBHOOK_SECRET")
        )
        
        # Handle event idempotently
        if event.id in self.processed_events:
            return  # Already processed
        self.processed_events.add(event.id)
        
        return await self.handle_event(event)
```

### 3.3 Exchange Rate Service

**Component**: `src/billing/currency_manager.py`

```python
class CurrencyManager:
    CACHE_TTL = timedelta(hours=1)
    
    async def get_rate(self, from_currency: str, to_currency: str) -> Decimal:
        # Check cache
        cached = await self.cache.get(f"rate:{from_currency}:{to_currency}")
        if cached:
            return cached.rate
        
        # Fetch live rate
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.exchangerate-api.com/v4/latest/EUR"
            )
            data = response.json()
        
        rate = Decimal(str(data["rates"][to_currency]))
        
        # Cache with TTL
        await self.cache.setex(
            f"rate:{from_currency}:{to_currency}",
            self.CACHE_TTL,
            rate
        )
        
        return rate
```

---

## 4. Frontend Architecture

### 4.1 Command Center

**Component**: `voiquyr-command-center/`

#### Login Flow
```
Form Submit → Validate Client-Side → POST /auth/login
         → JWT in HttpOnly Cookie → Redirect /dashboard
```

#### Real-time Dashboard
```typescript
// WebSocket for live updates
const ws = new WebSocket(wsUrl);

// Connection handlers
ws.onmessage = (event) => {
  const { active_calls, total_calls, avg_duration } = JSON.parse(event.data);
  updateDashboard({ active_calls, total_calls, avg_duration });
};
```

### 4.2 WebRTC Demo Page

**Component**: `frontend/src/pages/Demo.tsx`

```typescript
// WebRTC setup
const pc = new RTCPeerConnection(servers);

pc.ontrack = (event) => {
  audioElement.srcObject = event.streams[0];
};

async function startDemo() {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  stream.getTracks().forEach(track => pc.addTrack(track, stream));
  
  // Connect to signaling server
  const offer = await pc.createOffer();
  await pc.setLocalDescription(offer);
}
```

---

## 5. SDK Architecture

### 5.1 Python SDK

**Component**: `voiquyr/` (PyPI package)

```python
# voiquyr/__init__.py
class VoiquyrClient:
    def __init__(self, api_key: str, base_url: str = "https://api.voiquyr.com"):
        self.api_key = api_key
        self.base_url = base_url
    
    async def make_call(self, to: str, agent_id: str) -> Call:
        response = await self._post("/v1/calls", {
            "to": to,
            "agent_id": agent_id
        })
        return Call(**response.json())
    
    async def list_agents(self) -> List[Agent]:
        response = await self._get("/v1/agents")
        return [Agent(**a) for a in response.json()["agents"]]
```

### 5.2 TypeScript SDK

**Component**: `@voiquyr/sdk` (npm package)

```typescript
// index.ts
export class VoiquyrClient {
  constructor(
    public apiKey: string,
    public baseUrl = "https://api.voiquyr.com"
  ) {}
  
  async makeCall(params: { to: string; agentId: string }): Promise<Call> {
    const response = await this.fetch("/v1/calls", {
      method: "POST",
      body: JSON.stringify(params)
    });
    return response.json();
  }
}
```

---

## 6. Infrastructure

### 6.1 Database Migrations

**Component**: `alembic/` directory

```
alembic/
├── env.py
├── script.py.mako
└── versions/
    ├── 001_initial.py
    └── 002_add_agents.py
```

### 6.2 CI/CD Pipeline

**Component**: `.github/workflows/ci.yml`

```yaml
name: CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run migrations
        run: alembic upgrade head
      
      - name: Run tests
        run: pytest --cov=src
      
      - name: Build Docker
        run: docker build .
```

### 6.3 Prometheus Metrics

**Component**: `src/monitoring/metrics.py`

```python
from prometheus_client import Counter, Histogram

voiquyr_calls_total = Counter(
    'voiquyr_calls_total',
    'Total calls processed'
)

voiquyr_call_duration_seconds = Histogram(
    'voiquyr_call_duration_seconds',
    'Call duration in seconds'
)
```

---

## 7. Data Models

### 7.1 Agent
```python
class Agent(Base):
    id: UUID
    name: str
    stt_provider: STTProvider
    llm_provider: LLMProvider
    tts_provider: TTSProvider
    system_prompt: str
    created_at: datetime
    updated_at: datetime
```

### 7.2 Call
```python
class Call(Base):
    id: UUID
    tenant_id: UUID
    agent_id: UUID
    from_number: str
    to_number: str
    status: CallStatus
    duration_seconds: int
    started_at: datetime
    ended_at: datetime
    cost: Decimal
```

### 7.3 UsageRecord
```python
class UsageRecord(Base):
    id: UUID
    call_id: UUID
    stt_minutes: float
    input_tokens: int
    output_tokens: int
    tts_characters: int
    cost: Decimal
```

---

## 8. API Endpoints

### 8.1 Core API
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/agents` | GET | List agents |
| `/v1/agents` | POST | Create agent |
| `/v1/agents/{id}` | GET | Get agent |
| `/v1/agents/{id}` | PUT | Update agent |
| `/v1/calls` | GET | List calls |
| `/v1/calls` | POST | Initiate call |
| `/v1/calls/{id}` | GET | Get call status |
| `/health` | GET | Health check |

### 8.2 Telephony Webhooks
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/twilio/voice` | POST | Twilio voice webhook |
| `/twilio/status` | POST | Twilio status callback |
| `/asterisk/connect` | WS | Asterisk AudioSocket |

### 8.3 Billing
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/invoices` | GET | List invoices |
| `/v1/invoices/{id}` | GET | Get invoice |
| `/webhooks/stripe` | POST | Stripe webhooks |

---

## 9. Security

### 9.1 Authentication
- JWT tokens with 15-minute expiry
- Refresh tokens with 8-hour expiry
- OAuth 2.0 + PKCE for frontend

### 9.2 Twilio Signature Verification
```python
async def validate_signature(self, request: Request) -> bool:
    url = str(request.url)
    signature = request.headers["X-Twilio-Signature"]
    params = request.form
    
    expected = generate_signature(url, params, self.auth_token)
    return hmac.compare_digest(signature, expected)
```

### 9.3 Data Residency
```python
# When EU_DATA_RESIDENCY=true
config.EU_ONLY_MODES = True

# Provider routing
def get_stt_provider():
    if config.EU_ONLY_MODES:
        return DeepgramEU()  # EU-hosted endpoint
    return DeepgramUS()
```

---

## 10. Error Responses

### 10.1 Standard Error Envelope
```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Human readable error message",
    "request_id": "req_abc123"
  }
}
```

### 10.2 Error Codes
| Code | HTTP Status | Description |
|------|-----------|-------------|
| `INVALID_REQUEST` | 400 | Malformed request |
| `AUTH_REQUIRED` | 401 | Missing authentication |
| `AUTH_INVALID` | 401 | Invalid token |
| `FORBIDDEN` | 403 | Permission denied |
| `NOT_FOUND` | 404 | Resource not found |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |

---

## 11. SLO Definitions

| SLI | Target | Window |
|-----|--------|--------|
| API Availability | 99.5% | 30-day |
| Voice Turn Latency | <1,500ms | 95th percentile |
| Error Rate | <5% | 30-day |

### Backpressure
- Threshold: 80% of provisioned capacity
- Response: HTTP 429 with `Retry-After` header

---

## Appendix A: File Structure

```
voiquyr/
├── src/
│   ├── agents/
│   │   ├── stt_agent.py      # STT with Deepgram/Voxtral
│   │   ├── llm_agent.py     # LLM with Mistral/Ollama
│   │   └── tts_agent.py    # TTS with ElevenLabs/Piper
│   ├── telephony/
│   │   ├── twilio_bridge.py
│   │   └── asterisk_bridge.py
│   ├── billing/
│   │   ├── ucpm_calculator.py
│   │   ├── stripe_service.py
│   │   └── currency_manager.py
│   ├── api/
│   │   ├── main.py
│   │   ├── routers/
│   │   └── middleware.py
│   └── monitoring/
│       └── metrics.py
├── voiquyr-command-center/
│   └── frontend/
├── voiquyr-sdk/           # Python SDK
├── voiquyr-js/            # TypeScript SDK
├── alembic/
├── .github/workflows/
└── k8s/
```

---

## Appendix B: Environment Variables

| Variable | Required | Description |
|----------|-----------|-------------|
| `MISTRAL_API_KEY` | Yes* | Mistral API key for LLM |
| `DEEPGRAM_API_KEY` | Yes* | Deepgram API key for STT |
| `ELEVENLABS_API_KEY` | Yes* | ElevenLabs API key for TTS |
| `STRIPE_API_KEY` | Yes* | Stripe API key for billing |
| `STRIPE_WEBHOOK_SECRET` | Yes* | Stripe webhook secret |
| `TWILIO_ACCOUNT_SID` | Yes* | Twilio Account SID |
| `TWILIO_AUTH_TOKEN` | Yes* | Twilio Auth Token |
| `DATABASE_URL` | Yes | PostgreSQL connection |
| `REDIS_URL` | Yes | Redis connection |
| `EU_DATA_RESIDENCY` | No | Enable EU-only mode |
| `OLLAMA_ENDPOINT` | No* | Local Ollama endpoint |

*At least one of the options must be configured

---

Last Updated: April 2026