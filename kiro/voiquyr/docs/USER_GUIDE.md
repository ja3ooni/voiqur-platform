# EUVoice AI Platform User Guide

## Introduction

Welcome to the EUVoice AI Platform! This guide will help you get started with building and deploying voice assistants for European, Asian, African, and Middle Eastern languages.

## Table of Contents

- [Quick Start](#quick-start)
- [Voice Processing](#voice-processing)
- [Configuration](#configuration)
- [Advanced Features](#advanced-features)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Installation

```bash
# Install the Python SDK
pip install euvoice-python

# Or install from source
git clone https://github.com/euvoice/euvoice-ai-platform.git
cd euvoice-ai-platform
pip install -e .
```

### Basic Usage

```python
from euvoice import EUVoiceClient

# Initialize client
client = EUVoiceClient(api_key="your_api_key")

# Transcribe audio
result = client.stt.transcribe("audio.wav")
print(f"Transcription: {result.text}")
print(f"Language: {result.language}")
print(f"Confidence: {result.confidence}")

# Process with LLM
response = client.llm.process(
    text=result.text,
    context={"session_id": "user_123"}
)
print(f"Response: {response.text}")

# Synthesize speech
audio = client.tts.synthesize(
    text=response.text,
    voice="default",
    language=result.language
)
audio.save("response.wav")
```

## Voice Processing

### Speech-to-Text (STT)

Convert audio to text with automatic language detection:

```python
# Basic transcription
result = client.stt.transcribe("audio.wav")

# With language specification
result = client.stt.transcribe(
    "audio.wav",
    language="fr",  # French
    accent_detection=True,
    emotion_analysis=True
)

# Real-time streaming
stream = client.stt.create_stream()
stream.on('transcription', lambda text: print(text))
stream.send_audio(audio_chunk)
```

### Language Support

Supported languages include:
- English (en)
- French (fr)
- German (de)
- Spanish (es)
- Italian (it)
- Portuguese (pt)
- Dutch (nl)
- Polish (pl)
- Czech (cs)
- Romanian (ro)
- Hungarian (hu)
- Swedish (sv)
- Danish (da)
- Finnish (fi)
- Greek (el)
- Bulgarian (bg)
- Croatian (hr)
- Slovak (sk)
- Slovenian (sl)
- Estonian (et)
- Latvian (lv)
- Lithuanian (lt)
- Maltese (mt)
- Irish (ga)
- Arabic (ar)

### Dialog Management (LLM)

Process text through intelligent dialog management:

```python
# Simple processing
response = client.llm.process("Hello, how are you?")

# With context
response = client.llm.process(
    text="What's the weather like?",
    context={
        "session_id": "user_123",
        "user_preferences": {"location": "Paris"},
        "conversation_history": []
    }
)

# With tool calling
response = client.llm.process(
    text="Send an email to John",
    tools=["email", "calendar", "contacts"]
)
```

### Text-to-Speech (TTS)

Convert text to natural-sounding speech:

```python
# Basic synthesis
audio = client.tts.synthesize("Hello world")

# With voice cloning
audio = client.tts.synthesize(
    text="Hello world",
    voice="cloned_voice_id",
    emotion="friendly"
)

# Multiple languages
audio = client.tts.synthesize(
    text="Bonjour le monde",
    language="fr",
    voice="french_female"
)
```

## Configuration

### API Authentication

```python
# Using API key
client = EUVoiceClient(api_key="your_api_key")

# Using OAuth2
client = EUVoiceClient(
    oauth_token="your_oauth_token",
    oauth_refresh_token="your_refresh_token"
)
```

### Voice Configuration

```python
# Configure voice preferences
client.configure_voice(
    language="en-US",
    accent="american",
    speed=1.0,
    pitch=0.0,
    emotion="neutral"
)
```

### Session Management

```python
# Create session
session = client.create_session(
    user_id="user_123",
    preferences={
        "language": "en",
        "voice": "professional_female"
    }
)

# Use session
response = client.llm.process(
    text="Hello",
    session_id=session.id
)
```

## Advanced Features

### Emotion Detection

```python
# Enable emotion detection
result = client.stt.transcribe(
    "audio.wav",
    emotion_analysis=True
)

print(f"Emotion: {result.emotion.primary}")
print(f"Sentiment: {result.emotion.sentiment}")
```

### Accent Recognition

```python
# Enable accent detection
result = client.stt.transcribe(
    "audio.wav",
    accent_detection=True
)

print(f"Accent: {result.accent}")
```

### Voice Cloning

```python
# Clone voice from sample
voice_id = client.tts.clone_voice(
    audio_sample="voice_sample.wav",
    name="My Custom Voice"
)

# Use cloned voice
audio = client.tts.synthesize(
    text="Hello",
    voice=voice_id
)
```

### Lip Sync Generation

```python
# Generate lip sync data
result = client.tts.synthesize(
    text="Hello world",
    include_lip_sync=True
)

print(result.lip_sync_data.phonemes)
print(result.lip_sync_data.timestamps)
```

### Arabic Language Support

```python
# Process Arabic with dialect detection
result = client.stt.transcribe(
    "arabic_audio.wav",
    language="ar",
    dialect_detection=True
)

print(f"Dialect: {result.dialect}")  # e.g., "egyptian", "levantine"

# Synthesize Arabic with diacritization
audio = client.tts.synthesize(
    text="مرحبا بك",
    language="ar",
    dialect="msa",  # Modern Standard Arabic
    diacritization=True
)
```

## Troubleshooting

### Common Issues

#### Audio Format Not Supported

```python
# Convert audio to supported format
from pydub import AudioSegment

audio = AudioSegment.from_file("input.mp3")
audio = audio.set_frame_rate(16000)
audio = audio.set_channels(1)
audio.export("output.wav", format="wav")

# Then transcribe
result = client.stt.transcribe("output.wav")
```

#### Low Transcription Accuracy

```python
# Specify language explicitly
result = client.stt.transcribe(
    "audio.wav",
    language="fr",  # Don't use "auto" if you know the language
    accent_detection=True
)

# Use higher quality audio
# - Sample rate: 16kHz or higher
# - Format: WAV, FLAC (lossless)
# - Minimize background noise
```

#### Rate Limit Exceeded

```python
# Implement retry logic
import time
from euvoice.exceptions import RateLimitError

def transcribe_with_retry(audio_file, max_retries=3):
    for attempt in range(max_retries):
        try:
            return client.stt.transcribe(audio_file)
        except RateLimitError as e:
            if attempt < max_retries - 1:
                time.sleep(e.retry_after)
            else:
                raise
```

### Getting Help

- **Documentation**: https://docs.euvoice.ai
- **Community Forum**: https://community.euvoice.ai
- **Support Email**: support@euvoice.ai
- **GitHub Issues**: https://github.com/euvoice/euvoice-ai-platform/issues

## Best Practices

1. **Use Appropriate Audio Quality**: 16kHz sample rate, mono channel
2. **Specify Language When Known**: Better accuracy than auto-detection
3. **Handle Errors Gracefully**: Implement retry logic and error handling
4. **Cache Results**: Cache transcriptions and responses when possible
5. **Monitor Usage**: Track API usage to avoid rate limits
6. **Secure API Keys**: Never commit API keys to version control
7. **Use Sessions**: Maintain context across multiple interactions
8. **Test Thoroughly**: Test with various accents and audio conditions

## Examples

See the `examples/` directory for complete working examples:
- `basic_usage.py`: Simple transcription and synthesis
- `real_time_streaming.py`: Real-time audio processing
- `voice_cloning.py`: Custom voice creation
- `multilingual.py`: Multi-language support
- `emotion_detection.py`: Emotion and sentiment analysis

## Next Steps

- Explore the [API Documentation](api/README.md)
- Learn about [Agent Development](agents/README.md)
- Read the [Deployment Guide](deployment/README.md)
- Join the [Community Forum](https://community.euvoice.ai)
