"""
Test script for TTS Agent implementation
Tests core functionality including synthesis, voice cloning, emotion-aware synthesis, and streaming
"""

import asyncio
import numpy as np
import base64
from src.agents.tts_agent import (
    TTSAgent, SynthesisRequest, VoiceCloneRequest, EmotionType, VoiceQuality
)
from src.core.messaging import MessageBus
from src.core.models import AgentMessage, Priority


async def test_tts_agent():
    """Test TTS Agent functionality"""
    print("Testing TTS Agent Implementation...")
    
    # Create message bus and TTS agent
    message_bus = MessageBus()
    tts_agent = TTSAgent("tts_agent_test", message_bus)
    
    # Test 1: Initialize agent
    print("\n1. Testing agent initialization...")
    success = await tts_agent.initialize()
    print(f"   Initialization: {'SUCCESS' if success else 'FAILED'}")
    print(f"   Agent status: {tts_agent.state.status}")
    print(f"   Supported languages: {len(tts_agent.get_supported_languages())}")
    print(f"   Available voice models: {len(tts_agent.get_voice_models())}")
    
    # Test 2: Basic text synthesis
    print("\n2. Testing basic text synthesis...")
    try:
        result = await tts_agent.synthesize_text(
            text="Hello, this is a test of the EUVoice AI text-to-speech system.",
            voice_id="en_us_female_1",
            language="en"
        )
        print(f"   Synthesis: SUCCESS")
        print(f"   Duration: {result.duration:.2f}s")
        print(f"   Quality score: {result.quality_score:.2f}")
        print(f"   Processing time: {result.processing_time:.3f}s")
    except Exception as e:
        print(f"   Synthesis: FAILED - {e}")
    
    # Test 3: Voice cloning
    print("\n3. Testing voice cloning...")
    try:
        # Create mock 6-second audio sample
        sample_rate = 22050
        duration = 6.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        sample_audio = 0.3 * np.sin(2 * np.pi * 220 * t)  # Mock voice sample
        
        clone_result = await tts_agent.clone_voice_from_sample(
            sample_audio=sample_audio,
            sample_rate=sample_rate,
            voice_name="Test Cloned Voice",
            language="en"
        )
        
        print(f"   Voice cloning: {'SUCCESS' if clone_result.success else 'FAILED'}")
        if clone_result.success:
            print(f"   New voice ID: {clone_result.voice_id}")
            print(f"   Quality score: {clone_result.quality_score:.2f}")
        else:
            print(f"   Error: {clone_result.error_message}")
    except Exception as e:
        print(f"   Voice cloning: FAILED - {e}")
    
    # Test 4: Emotion-aware synthesis
    print("\n4. Testing emotion-aware synthesis...")
    try:
        emotion_context = {
            "emotion": "happy",
            "intensity": 1.5
        }
        
        emotion_result = await tts_agent.synthesize_with_emotion(
            text="I'm so excited to demonstrate emotion-aware speech synthesis!",
            emotion_context=emotion_context,
            voice_id="en_us_female_1",
            language="en"
        )
        
        print(f"   Emotion synthesis: SUCCESS")
        print(f"   Emotion applied: {emotion_context['emotion']}")
        print(f"   Duration: {emotion_result.duration:.2f}s")
        print(f"   Quality score: {emotion_result.quality_score:.2f}")
    except Exception as e:
        print(f"   Emotion synthesis: FAILED - {e}")
    
    # Test 5: Streaming session
    print("\n5. Testing real-time streaming...")
    try:
        stream_id = await tts_agent.create_streaming_session(
            text="This is a test of real-time audio streaming with low latency.",
            voice_id="en_us_female_1",
            language="en"
        )
        
        print(f"   Streaming session created: {stream_id}")
        
        # Get a few chunks
        chunk_count = 0
        while chunk_count < 3:
            chunk_data = await tts_agent.get_stream_chunk(stream_id)
            if chunk_data is None:
                break
            
            chunk, is_last = chunk_data
            chunk_count += 1
            print(f"   Received chunk {chunk_count}: {len(chunk)} samples, last: {is_last}")
            
            if is_last:
                break
        
        print(f"   Streaming: SUCCESS ({chunk_count} chunks)")
    except Exception as e:
        print(f"   Streaming: FAILED - {e}")
    
    # Test 6: Message handling
    print("\n6. Testing message handling...")
    try:
        # Test synthesis request message
        synthesis_message = AgentMessage(
            sender_id="test_client",
            receiver_id="tts_agent_test",
            message_type="synthesis_request",
            payload={
                "text": "Testing message-based synthesis",
                "voice_id": "en_us_female_1",
                "language": "en",
                "emotion": "neutral"
            },
            priority=Priority.NORMAL
        )
        
        response = await tts_agent.handle_message(synthesis_message)
        
        if response and response.message_type == "synthesis_response":
            print(f"   Message handling: SUCCESS")
            print(f"   Response type: {response.message_type}")
            print(f"   Audio data length: {len(response.payload.get('audio_data', ''))}")
        else:
            print(f"   Message handling: FAILED - No valid response")
    except Exception as e:
        print(f"   Message handling: FAILED - {e}")
    
    # Test 7: Performance metrics
    print("\n7. Testing performance metrics...")
    try:
        metrics = tts_agent.get_performance_metrics()
        print(f"   Total syntheses: {metrics['total_syntheses']}")
        print(f"   Average synthesis time: {metrics['average_synthesis_time']:.3f}s")
        print(f"   Average quality score: {metrics['average_quality_score']:.2f}")
        print(f"   Voice clone success rate: {metrics['state']['performance_metrics']['voice_clone_success_rate']:.2f}")
        print(f"   Performance metrics: SUCCESS")
    except Exception as e:
        print(f"   Performance metrics: FAILED - {e}")
    
    # Test 8: Multi-language support
    print("\n8. Testing multi-language support...")
    try:
        languages_to_test = ["en", "fr", "de", "es", "it"]
        test_texts = {
            "en": "Hello, how are you today?",
            "fr": "Bonjour, comment allez-vous?",
            "de": "Hallo, wie geht es Ihnen?",
            "es": "Hola, ¿cómo está usted?",
            "it": "Ciao, come stai?"
        }
        
        for lang in languages_to_test:
            if lang in tts_agent.get_supported_languages():
                # Find a voice for this language
                voices = tts_agent.get_voice_models(lang)
                if voices:
                    voice_id = voices[0].voice_id
                    text = test_texts.get(lang, "Test text")
                    
                    result = await tts_agent.synthesize_text(
                        text=text,
                        voice_id=voice_id,
                        language=lang
                    )
                    
                    print(f"   {lang.upper()}: SUCCESS (voice: {voices[0].name}, duration: {result.duration:.2f}s)")
                else:
                    print(f"   {lang.upper()}: No voices available")
            else:
                print(f"   {lang.upper()}: Not supported")
        
        print(f"   Multi-language support: SUCCESS")
    except Exception as e:
        print(f"   Multi-language support: FAILED - {e}")
    
    print(f"\nTTS Agent testing completed!")
    print(f"Final agent status: {tts_agent.state.status}")


if __name__ == "__main__":
    asyncio.run(test_tts_agent())