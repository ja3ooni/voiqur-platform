#!/usr/bin/env python3
"""
Test script for voice cloning capabilities in TTS Agent
Tests the enhanced voice cloning with 6-second samples, cross-lingual synthesis, and MOS scoring
"""

import pytest
pytest.importorskip("torch")

import asyncio
import numpy as np
import logging
from typing import Dict, Any
import base64

from src.agents.tts_agent import (
    TTSAgent, VoiceCloneRequest, VoiceCloneResult, 
    SynthesisRequest, EmotionType, VoiceQuality
)
from src.core.messaging import MessageBus
from src.core.models import AgentMessage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_test_audio(duration: float = 6.0, sample_rate: int = 22050, 
                       voice_type: str = "female") -> np.ndarray:
    """Generate test audio sample for voice cloning"""
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Generate more realistic speech-like audio
    if voice_type == "female":
        base_freq = 220  # Female voice frequency
    else:
        base_freq = 150  # Male voice frequency
    
    # Create speech-like signal with multiple harmonics and modulation
    audio = (
        0.4 * np.sin(2 * np.pi * base_freq * t) +
        0.2 * np.sin(2 * np.pi * base_freq * 2 * t) +
        0.1 * np.sin(2 * np.pi * base_freq * 3 * t) +
        0.05 * np.sin(2 * np.pi * base_freq * 4 * t)
    )
    
    # Add formant-like resonances
    formant1 = 0.1 * np.sin(2 * np.pi * 800 * t)
    formant2 = 0.05 * np.sin(2 * np.pi * 1200 * t)
    audio += formant1 + formant2
    
    # Add speech-like amplitude modulation
    modulation = 1.0 + 0.3 * np.sin(2 * np.pi * 5 * t)  # 5 Hz modulation
    audio *= modulation
    
    # Add some noise for realism
    noise = 0.02 * np.random.normal(0, 1, len(audio))
    audio += noise
    
    # Normalize
    audio = audio / np.max(np.abs(audio)) * 0.8
    
    return audio


async def test_voice_cloning_basic():
    """Test basic voice cloning functionality"""
    logger.info("=== Testing Basic Voice Cloning ===")
    
    # Create TTS agent
    message_bus = MessageBus()
    tts_agent = TTSAgent("tts_test", message_bus)
    
    # Initialize agent
    success = await tts_agent.initialize()
    assert success, "TTS Agent initialization failed"
    
    # Generate test audio sample (6 seconds)
    sample_audio = generate_test_audio(duration=6.5, voice_type="female")
    sample_rate = 22050
    
    # Test voice cloning
    result = await tts_agent.clone_voice_from_sample(
        sample_audio=sample_audio,
        sample_rate=sample_rate,
        voice_name="TestVoice_Female",
        language="en"
    )
    
    # Verify results
    assert result.success, f"Voice cloning failed: {result.error_message}"
    assert result.voice_id, "Voice ID not generated"
    assert result.quality_score >= 2.0, f"Quality score too low: {result.quality_score}"
    assert result.voice_model is not None, "Voice model not created"
    assert result.voice_model.cloned_from_sample, "Voice model not marked as cloned"
    
    logger.info(f"✅ Voice cloned successfully: {result.voice_id}")
    logger.info(f"   Quality Score (MOS): {result.quality_score:.2f}")
    logger.info(f"   Supported emotions: {[e.value for e in result.voice_model.supported_emotions]}")
    logger.info(f"   Cross-lingual targets: {result.voice_model.metadata.get('supported_target_languages', [])}")
    
    return result.voice_id


async def test_voice_cloning_quality_validation():
    """Test voice cloning with quality validation"""
    logger.info("=== Testing Voice Cloning Quality Validation ===")
    
    message_bus = MessageBus()
    tts_agent = TTSAgent("tts_test", message_bus)
    await tts_agent.initialize()
    
    # Test with high-quality sample (longer duration)
    high_quality_audio = generate_test_audio(duration=10.0, voice_type="male")
    
    result_hq = await tts_agent.clone_voice_from_sample(
        sample_audio=high_quality_audio,
        sample_rate=22050,
        voice_name="HighQuality_Male",
        language="en",
        target_text="This is a test sentence for quality validation."
    )
    
    assert result_hq.success, "High-quality voice cloning failed"
    logger.info(f"✅ High-quality voice: MOS {result_hq.quality_score:.2f}")
    
    # Test with low-quality sample (minimum duration)
    low_quality_audio = generate_test_audio(duration=6.0, voice_type="female")
    # Add more noise to simulate low quality
    low_quality_audio += 0.1 * np.random.normal(0, 1, len(low_quality_audio))
    
    result_lq = await tts_agent.clone_voice_from_sample(
        sample_audio=low_quality_audio,
        sample_rate=22050,
        voice_name="LowQuality_Female",
        language="en"
    )
    
    assert result_lq.success, "Low-quality voice cloning failed"
    logger.info(f"✅ Low-quality voice: MOS {result_lq.quality_score:.2f}")
    
    # Verify quality difference
    assert result_hq.quality_score > result_lq.quality_score, "Quality scoring not working correctly"
    
    # Test with too-short sample
    short_audio = generate_test_audio(duration=4.0, voice_type="male")
    
    result_short = await tts_agent.clone_voice_from_sample(
        sample_audio=short_audio,
        sample_rate=22050,
        voice_name="TooShort_Male",
        language="en"
    )
    
    assert not result_short.success, "Short sample should fail"
    assert "6 seconds" in result_short.error_message, "Error message should mention 6 seconds"
    logger.info(f"✅ Short sample correctly rejected: {result_short.error_message}")
    
    return result_hq.voice_id


async def test_cross_lingual_synthesis():
    """Test cross-lingual voice synthesis"""
    logger.info("=== Testing Cross-Lingual Voice Synthesis ===")
    
    message_bus = MessageBus()
    tts_agent = TTSAgent("tts_test", message_bus)
    await tts_agent.initialize()
    
    # First clone an English voice
    english_audio = generate_test_audio(duration=8.0, voice_type="female")
    
    clone_result = await tts_agent.clone_voice_from_sample(
        sample_audio=english_audio,
        sample_rate=22050,
        voice_name="English_Speaker",
        language="en"
    )
    
    assert clone_result.success, "English voice cloning failed"
    voice_id = clone_result.voice_id
    
    logger.info(f"✅ English voice cloned: {voice_id}")
    
    # Test cross-lingual synthesis to French (English-accented French)
    french_text = "Bonjour, comment allez-vous? Je suis un assistant vocal."
    
    cross_lingual_result = await tts_agent.synthesize_cross_lingual(
        text=french_text,
        source_voice_id=voice_id,
        target_language="fr",
        preserve_accent=True
    )
    
    assert cross_lingual_result.audio_data is not None, "Cross-lingual synthesis failed"
    assert cross_lingual_result.metadata["cross_lingual"], "Cross-lingual flag not set"
    assert cross_lingual_result.metadata["source_language"] == "en", "Source language incorrect"
    assert cross_lingual_result.metadata["target_language"] == "fr", "Target language incorrect"
    assert cross_lingual_result.metadata["accent_preserved"], "Accent preservation flag not set"
    
    logger.info(f"✅ Cross-lingual synthesis successful: EN → FR")
    logger.info(f"   Audio duration: {cross_lingual_result.duration:.2f}s")
    logger.info(f"   Quality score: {cross_lingual_result.quality_score:.2f}")
    
    # Test synthesis to German
    german_text = "Guten Tag, wie geht es Ihnen? Ich bin ein Sprachassistent."
    
    german_result = await tts_agent.synthesize_cross_lingual(
        text=german_text,
        source_voice_id=voice_id,
        target_language="de",
        preserve_accent=True
    )
    
    assert german_result.audio_data is not None, "German synthesis failed"
    logger.info(f"✅ Cross-lingual synthesis successful: EN → DE")
    
    return voice_id


async def test_voice_quality_validation():
    """Test voice quality validation functionality"""
    logger.info("=== Testing Voice Quality Validation ===")
    
    message_bus = MessageBus()
    tts_agent = TTSAgent("tts_test", message_bus)
    await tts_agent.initialize()
    
    # Clone a voice for testing
    test_audio = generate_test_audio(duration=7.0, voice_type="male")
    
    clone_result = await tts_agent.clone_voice_from_sample(
        sample_audio=test_audio,
        sample_rate=22050,
        voice_name="ValidationTest_Male",
        language="en"
    )
    
    assert clone_result.success, "Voice cloning for validation test failed"
    voice_id = clone_result.voice_id
    
    # Test quality validation
    validation_result = await tts_agent.validate_voice_quality(
        voice_id=voice_id,
        test_text="This is a comprehensive test of voice quality validation."
    )
    
    assert "mos_score" in validation_result, "MOS score not in validation result"
    assert "quality_metrics" in validation_result, "Quality metrics not in validation result"
    assert validation_result["mos_score"] >= 1.0, "MOS score below minimum"
    assert validation_result["mos_score"] <= 5.0, "MOS score above maximum"
    
    logger.info(f"✅ Voice quality validation successful")
    logger.info(f"   MOS Score: {validation_result['mos_score']:.2f}")
    logger.info(f"   SNR: {validation_result['quality_metrics']['snr']:.2f} dB")
    logger.info(f"   Clarity: {validation_result['quality_metrics']['clarity_score']:.2f}")
    logger.info(f"   Prosody: {validation_result['quality_metrics']['prosody_score']:.2f}")
    
    return validation_result


async def test_message_based_voice_cloning():
    """Test voice cloning through message interface"""
    logger.info("=== Testing Message-Based Voice Cloning ===")
    
    message_bus = MessageBus()
    tts_agent = TTSAgent("tts_test", message_bus)
    await tts_agent.initialize()
    
    # Generate test audio and encode as base64
    sample_audio = generate_test_audio(duration=6.5, voice_type="female")
    sample_audio_int16 = (sample_audio * 32767).astype(np.int16)
    sample_audio_b64 = base64.b64encode(sample_audio_int16.tobytes()).decode('utf-8')
    
    # Create voice clone request message
    clone_message = AgentMessage(
        sender_id="test_client",
        receiver_id="tts_test",
        message_type="voice_clone_request",
        payload={
            "sample_audio": sample_audio_b64,
            "voice_name": "MessageTest_Female",
            "language": "en",
            "sample_rate": 22050
        }
    )
    
    # Handle message
    response = await tts_agent.handle_message(clone_message)
    
    assert response is not None, "No response received"
    assert response.message_type == "voice_clone_response", "Wrong response type"
    assert response.payload["success"], f"Voice cloning failed: {response.payload.get('error_message')}"
    
    voice_id = response.payload["voice_id"]
    quality_score = response.payload["quality_score"]
    
    logger.info(f"✅ Message-based voice cloning successful")
    logger.info(f"   Voice ID: {voice_id}")
    logger.info(f"   Quality Score: {quality_score:.2f}")
    
    # Test cross-lingual synthesis through messages
    cross_lingual_message = AgentMessage(
        sender_id="test_client",
        receiver_id="tts_test",
        message_type="cross_lingual_synthesis_request",
        payload={
            "text": "Hola, ¿cómo estás? Soy un asistente de voz.",
            "source_voice_id": voice_id,
            "target_language": "es",
            "preserve_accent": True
        }
    )
    
    cross_response = await tts_agent.handle_message(cross_lingual_message)
    
    assert cross_response is not None, "No cross-lingual response received"
    assert cross_response.message_type == "cross_lingual_synthesis_response", "Wrong cross-lingual response type"
    assert "audio_data" in cross_response.payload, "No audio data in cross-lingual response"
    
    logger.info(f"✅ Message-based cross-lingual synthesis successful")
    logger.info(f"   Target language: {cross_response.payload['target_language']}")
    logger.info(f"   Duration: {cross_response.payload['duration']:.2f}s")
    
    return voice_id


async def test_performance_metrics():
    """Test performance metrics tracking"""
    logger.info("=== Testing Performance Metrics ===")
    
    message_bus = MessageBus()
    tts_agent = TTSAgent("tts_test", message_bus)
    await tts_agent.initialize()
    
    # Perform multiple operations to generate metrics
    for i in range(3):
        sample_audio = generate_test_audio(duration=6.0 + i, voice_type="female" if i % 2 == 0 else "male")
        
        result = await tts_agent.clone_voice_from_sample(
            sample_audio=sample_audio,
            sample_rate=22050,
            voice_name=f"MetricsTest_{i}",
            language="en"
        )
        
        assert result.success, f"Voice cloning {i} failed"
    
    # Get performance metrics
    metrics = tts_agent.get_performance_metrics()
    
    assert metrics["total_voice_clones"] == 3, "Voice clone count incorrect"
    assert metrics["successful_voice_clones"] == 3, "Successful clone count incorrect"
    assert metrics["voice_clone_success_rate"] == 1.0, "Success rate incorrect"
    assert metrics["average_quality_score"] > 0, "Average quality score not calculated"
    
    logger.info(f"✅ Performance metrics tracking working")
    logger.info(f"   Total clones: {metrics['total_voice_clones']}")
    logger.info(f"   Success rate: {metrics['voice_clone_success_rate']:.2%}")
    logger.info(f"   Average quality: {metrics['average_quality_score']:.2f}")
    
    return metrics


async def main():
    """Run all voice cloning tests"""
    logger.info("Starting Voice Cloning Tests")
    logger.info("=" * 50)
    
    try:
        # Test basic voice cloning
        voice_id_1 = await test_voice_cloning_basic()
        
        # Test quality validation
        voice_id_2 = await test_voice_cloning_quality_validation()
        
        # Test cross-lingual synthesis
        voice_id_3 = await test_cross_lingual_synthesis()
        
        # Test voice quality validation
        await test_voice_quality_validation()
        
        # Test message-based interface
        voice_id_4 = await test_message_based_voice_cloning()
        
        # Test performance metrics
        await test_performance_metrics()
        
        logger.info("=" * 50)
        logger.info("🎉 All Voice Cloning Tests Passed!")
        logger.info(f"Created voice models: {[voice_id_1, voice_id_2, voice_id_3, voice_id_4]}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)