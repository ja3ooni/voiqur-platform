# EUVoice AI Platform API Documentation

## Overview

The EUVoice AI Platform provides comprehensive REST and WebSocket APIs for building, deploying, and managing voice assistants. All APIs are designed with EU compliance, GDPR requirements, and low-latency performance in mind.

## Base URL

```
Production: https://api.euvoice.ai/v1
Staging: https://staging-api.euvoice.ai/v1
Development: http://localhost:8000/v1
```

## Authentication

All API endpoints require authentication using JWT tokens or API keys.

### JWT Authentication
```http
Authorization: Bearer <jwt_token>
```

### API Key Authentication
```http
X-API-Key: <api_key>
```

## Rate Limiting

- **Free Tier**: 100 requests/minute
- **Pro Tier**: 1,000 requests/minute  
- **Enterprise**: Custom limits

Rate limit headers are included in all responses:
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

## Core Endpoints

### Voice Processing Pipeline

#### Speech-to-Text (STT)
Convert audio to text with language detection and accent recognition.

```http
POST /stt/transcribe
Content-Type: multipart/form-data

{
  "audio": <audio_file>,
  "language": "auto|en|fr|de|es|...",
  "accent_detection": true,
  "emotion_analysis": true
}
```

**Response:**
```json
{
  "text": "Hello, how can I help you today?",
  "confidence": 0.95,
  "language": "en-US",
  "accent": "american",
  "emotion": {
    "primary": "neutral",
    "confidence": 0.87,
    "sentiment": 0.1
  },
  "timestamps": [
    {"start": 0.0, "end": 0.5, "word": "Hello"},
    {"start": 0.6, "end": 0.9, "word": "how"}
  ]
}
```

#### Large Language Model (LLM)
Process text through dialog management and reasoning.

```http
POST /llm/process
Content-Type: application/json

{
  "text": "Hello, how can I help you today?",
  "context": {
    "session_id": "sess_123",
    "user_id": "user_456",
    "conversation_history": []
  },
  "tools": ["web_search", "calendar", "email"]
}
```

**Response:**
```json
{
  "response": "Hello! I'm here to help. What would you like assistance with?",
  "intent": "greeting",
  "entities": [],
  "tool_calls": [],
  "context_updated": true,
  "confidence": 0.92
}
```

#### Text-to-Speech (TTS)
Convert text to natural speech with voice cloning and emotion.

```http
POST /tts/synthesize
Content-Type: application/json

{
  "text": "Hello! I'm here to help.",
  "voice": "default|cloned_voice_id",
  "language": "en-US",
  "emotion": "friendly",
  "speed": 1.0,
  "pitch": 0.0
}
```

**Response:**
```json
{
  "audio_url": "https://cdn.euvoice.ai/audio/abc123.wav",
  "duration": 2.5,
  "format": "wav",
  "sample_rate": 22050,
  "lip_sync_data": {
    "phonemes": [...],
    "timestamps": [...]
  }
}
```

### Real-time Streaming

#### WebSocket Audio Streaming
Real-time bidirectional audio processing.

```javascript
const ws = new WebSocket('wss://api.euvoice.ai/v1/stream');

// Send audio chunks
ws.send(JSON.stringify({
  type: 'audio_chunk',
  data: base64AudioData,
  format: 'wav',
  sample_rate: 16000
}));

// Receive real-time transcription
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'transcription') {
    console.log('Partial:', data.text);
  }
};
```

### Agent Management

#### List Available Agents
```http
GET /agents
```

**Response:**
```json
{
  "agents": [
    {
      "id": "stt_agent_001",
      "type": "STT",
      "status": "active",
      "capabilities": ["speech_to_text", "language_detection"],
      "performance": {
        "latency_ms": 45,
        "accuracy": 0.95,
        "load": 0.3
      }
    }
  ]
}
```

#### Register New Agent
```http
POST /agents/register
Content-Type: application/json

{
  "agent_id": "custom_agent_001",
  "agent_type": "CUSTOM",
  "capabilities": [
    {
      "name": "custom_processing",
      "description": "Custom audio processing",
      "input_schema": {"audio": "bytes"},
      "output_schema": {"result": "object"}
    }
  ],
  "endpoint": "https://my-agent.example.com/process"
}
```

### Knowledge Base

#### Store Knowledge
```http
POST /knowledge
Content-Type: application/json

{
  "key": "user_preferences_123",
  "value": {
    "language": "en-US",
    "voice": "female_professional",
    "speed": 1.1
  },
  "access_level": "private",
  "ttl": 3600
}
```

#### Retrieve Knowledge
```http
GET /knowledge/{key}
```

### Monitoring and Analytics

#### System Health
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "health_percentage": 0.98,
  "components": {
    "stt_service": "healthy",
    "llm_service": "healthy", 
    "tts_service": "degraded",
    "database": "healthy"
  },
  "metrics": {
    "total_requests": 1000000,
    "avg_latency_ms": 85,
    "error_rate": 0.001
  }
}
```

#### Performance Metrics
```http
GET /metrics?timerange=1h&agent_type=STT
```

## Error Handling

All errors follow RFC 7807 Problem Details format:

```json
{
  "type": "https://euvoice.ai/errors/rate-limit-exceeded",
  "title": "Rate limit exceeded",
  "status": 429,
  "detail": "You have exceeded the rate limit of 1000 requests per minute",
  "instance": "/stt/transcribe",
  "retry_after": 60
}
```

### Common Error Codes

- `400` - Bad Request: Invalid input parameters
- `401` - Unauthorized: Missing or invalid authentication
- `403` - Forbidden: Insufficient permissions
- `404` - Not Found: Resource not found
- `429` - Too Many Requests: Rate limit exceeded
- `500` - Internal Server Error: Server-side error
- `503` - Service Unavailable: Service temporarily unavailable

## SDKs and Libraries

### Python SDK
```bash
pip install euvoice-python
```

```python
from euvoice import EUVoiceClient

client = EUVoiceClient(api_key="your_api_key")

# Transcribe audio
result = client.stt.transcribe("audio.wav")
print(result.text)

# Process with LLM
response = client.llm.process("Hello there")
print(response.text)

# Synthesize speech
audio = client.tts.synthesize("Hello world")
audio.save("output.wav")
```

### JavaScript SDK
```bash
npm install @euvoice/sdk
```

```javascript
import { EUVoiceClient } from '@euvoice/sdk';

const client = new EUVoiceClient({ apiKey: 'your_api_key' });

// Real-time streaming
const stream = client.createStream();
stream.on('transcription', (text) => console.log(text));
stream.sendAudio(audioBuffer);
```

## Compliance and Security

### GDPR Compliance
- All personal data is processed within EU boundaries
- Data anonymization available via `anonymize=true` parameter
- Right to deletion via `DELETE /users/{id}/data`
- Data export via `GET /users/{id}/export`

### Data Retention
- Audio data: Deleted after 30 days (configurable)
- Transcriptions: Retained for analytics (anonymized)
- User preferences: Retained until account deletion

### Security Features
- TLS 1.3 encryption for all communications
- API key rotation and expiration
- Request signing for sensitive operations
- Audit logging for compliance

## Webhooks

Register webhooks to receive real-time notifications:

```http
POST /webhooks
Content-Type: application/json

{
  "url": "https://your-app.com/webhook",
  "events": ["transcription.completed", "synthesis.completed"],
  "secret": "webhook_secret_key"
}
```

Webhook payload example:
```json
{
  "event": "transcription.completed",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "session_id": "sess_123",
    "text": "Hello world",
    "confidence": 0.95
  },
  "signature": "sha256=..."
}
```

## OpenAPI Specification

The complete OpenAPI 3.0 specification is available at:
- Interactive docs: `https://api.euvoice.ai/docs`
- JSON spec: `https://api.euvoice.ai/openapi.json`
- YAML spec: `https://api.euvoice.ai/openapi.yaml`

## Support

- Documentation: https://docs.euvoice.ai
- Community: https://community.euvoice.ai
- Support: support@euvoice.ai
- Status Page: https://status.euvoice.ai