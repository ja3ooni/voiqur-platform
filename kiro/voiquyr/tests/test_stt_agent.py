"""
Test script for STT Agent implementation
"""

import asyncio
import numpy as np
import logging
from src.core.messaging import MessageBus
from src.agents.stt_agent import STTAgent, AudioChunk
from src.agents.audio_streaming import AudioStreamingManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_stt_agent():
    """Test STT Agent functionality"""
    logger.info("Testing STT Agent implementation...")
    
    # Create message bus (mock)
    message_bus = MessageBus()
    
    # Create STT agent
    stt_agent = STTAgent("stt_agent_test", message_bus)
    
    # Initialize agent
    success = await stt_agent.initialize()
    if not success:
        logger.error("Failed to initialize STT agent")
        return False
    
    logger.info("STT Agent initialized successfully")
    
    # Create test audio data (1 second of sine wave at 440 Hz)
    sample_rate = 16000
    duration = 1.0
    frequency = 440.0
    
    t = np.linspace(0, duration, int(sample_rate * duration))
    test_audio = np.sin(2 * np.pi * frequency * t).astype(np.float32)
    
    logger.info(f"Created test audio: {len(test_audio)} samples at {sample_rate} Hz")
    
    # Test transcription
    try:
        results = await stt_agent.transcribe_audio(test_audio, sample_rate)
        logger.info(f"Transcription completed: {len(results)} chunks processed")
        
        for i, result in enumerate(results):
            logger.info(f"Chunk {i}: '{result.text}' (confidence: {result.confidence:.2f}, language: {result.language})")
        
        # Test performance metrics
        metrics = stt_agent.get_performance_metrics()
        logger.info(f"Performance metrics: {metrics}")
        
        return True
        
    except Exception as e:
        logger.error(f"Transcription test failed: {e}")
        return False

async def test_audio_streaming():
    """Test audio streaming functionality"""
    logger.info("Testing Audio Streaming Manager...")
    
    # Create message bus and STT agent
    message_bus = MessageBus()
    stt_agent = STTAgent("stt_agent_streaming", message_bus)
    
    # Initialize STT agent
    await stt_agent.initialize()
    
    # Create streaming manager
    streaming_manager = AudioStreamingManager(stt_agent)
    
    # Initialize streaming manager
    success = await streaming_manager.initialize(host="localhost", port=8766)
    if not success:
        logger.error("Failed to initialize streaming manager")
        return False
    
    logger.info("Audio Streaming Manager initialized successfully")
    
    # Get status
    status = streaming_manager.get_streaming_status()
    logger.info(f"Streaming status: {status}")
    
    return True

async def test_language_detection():
    """Test advanced language detection"""
    logger.info("Testing Advanced Language Detection...")
    
    from src.agents.language_detection import AdvancedLanguageDetector
    
    # Create language detector
    detector = AdvancedLanguageDetector()
    
    # Initialize models
    success = await detector.initialize_models()
    if not success:
        logger.error("Failed to initialize language detection models")
        return False
    
    logger.info("Language detection models initialized successfully")
    
    # Test with sample audio
    sample_rate = 16000
    duration = 0.5
    test_audio = np.random.randn(int(sample_rate * duration)).astype(np.float32)
    
    audio_chunk = AudioChunk(
        data=test_audio,
        sample_rate=sample_rate,
        timestamp=0.0,
        chunk_id=0
    )
    
    # Detect language
    result = await detector.detect_language(audio_chunk)
    
    logger.info(f"Language detection result:")
    logger.info(f"  Language: {result.language} (confidence: {result.confidence:.2f})")
    logger.info(f"  Family: {result.language_family.value}")
    logger.info(f"  Dialect: {result.dialect}")
    logger.info(f"  Accent region: {result.accent_region}")
    logger.info(f"  Processing time: {result.processing_time:.3f}s")
    logger.info(f"  Alternatives: {result.alternative_languages}")
    
    # Test performance metrics
    metrics = detector.get_performance_metrics()
    logger.info(f"Detection performance: {metrics}")
    
    # Test supported languages
    languages = detector.get_supported_languages()
    logger.info(f"Supported languages ({len(languages)}): {languages}")
    
    return True

async def main():
    """Run all tests"""
    logger.info("Starting STT Agent tests...")
    
    tests = [
        ("STT Agent Basic", test_stt_agent),
        ("Audio Streaming", test_audio_streaming),
        ("Language Detection", test_language_detection)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running test: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            success = await test_func()
            results[test_name] = success
            logger.info(f"Test {test_name}: {'PASSED' if success else 'FAILED'}")
        except Exception as e:
            logger.error(f"Test {test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    logger.info(f"\n{'='*50}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*50}")
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, success in results.items():
        status = "PASSED" if success else "FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("All tests passed! STT Agent implementation is working correctly.")
    else:
        logger.warning(f"{total - passed} tests failed. Please check the implementation.")

if __name__ == "__main__":
    asyncio.run(main())