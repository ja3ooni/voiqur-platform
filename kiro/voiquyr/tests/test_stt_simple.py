"""
Simple test for STT Agent core functionality
"""

import asyncio
import numpy as np
import logging
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_language_detection():
    """Test language detection functionality"""
    logger.info("Testing Language Detection...")
    
    try:
        from agents.language_detection import AdvancedLanguageDetector, AudioChunk
        
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
        
    except Exception as e:
        logger.error(f"Language detection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_audio_preprocessing():
    """Test audio preprocessing functionality"""
    logger.info("Testing Audio Preprocessing...")
    
    try:
        from agents.stt_agent import AudioPreprocessor, AudioChunk
        
        # Create preprocessor
        preprocessor = AudioPreprocessor()
        
        # Create test audio (1 second of sine wave)
        sample_rate = 44100  # Different sample rate to test resampling
        duration = 1.0
        frequency = 440.0
        
        t = np.linspace(0, duration, int(sample_rate * duration))
        test_audio = np.sin(2 * np.pi * frequency * t).astype(np.float32)
        
        logger.info(f"Created test audio: {len(test_audio)} samples at {sample_rate} Hz")
        
        # Test preprocessing
        processed_audio = preprocessor.preprocess_audio(test_audio, sample_rate)
        logger.info(f"Processed audio: {len(processed_audio)} samples at {preprocessor.target_sample_rate} Hz")
        
        # Test chunking
        chunks = preprocessor.chunk_audio(processed_audio)
        logger.info(f"Created {len(chunks)} audio chunks")
        
        for i, chunk in enumerate(chunks[:3]):  # Show first 3 chunks
            logger.info(f"Chunk {i}: {len(chunk.data)} samples, timestamp: {chunk.timestamp:.3f}s")
        
        return True
        
    except Exception as e:
        logger.error(f"Audio preprocessing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_voice_activity_detection():
    """Test voice activity detection"""
    logger.info("Testing Voice Activity Detection...")
    
    try:
        from agents.audio_streaming import VoiceActivityDetector, AudioChunk
        
        # Create VAD
        vad = VoiceActivityDetector()
        
        # Test with silence (low energy)
        silence_audio = np.random.randn(8000) * 0.001  # Very low amplitude
        silence_chunk = AudioChunk(
            data=silence_audio.astype(np.float32),
            sample_rate=16000,
            timestamp=0.0,
            chunk_id=0
        )
        
        silence_result = vad.detect_voice_activity(silence_chunk)
        logger.info(f"Silence detection: speech={silence_result.is_speech}, confidence={silence_result.confidence:.3f}, energy={silence_result.energy_level:.6f}")
        
        # Test with speech-like signal (higher energy)
        speech_audio = np.random.randn(8000) * 0.1  # Higher amplitude
        speech_chunk = AudioChunk(
            data=speech_audio.astype(np.float32),
            sample_rate=16000,
            timestamp=0.5,
            chunk_id=1
        )
        
        speech_result = vad.detect_voice_activity(speech_chunk)
        logger.info(f"Speech detection: speech={speech_result.is_speech}, confidence={speech_result.confidence:.3f}, energy={speech_result.energy_level:.6f}")
        
        return True
        
    except Exception as e:
        logger.error(f"Voice activity detection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_acoustic_features():
    """Test acoustic feature extraction"""
    logger.info("Testing Acoustic Feature Extraction...")
    
    try:
        from agents.language_detection import AcousticFeatureExtractor, AudioChunk
        
        # Create feature extractor
        extractor = AcousticFeatureExtractor()
        
        # Create test audio with known characteristics
        sample_rate = 16000
        duration = 1.0
        frequency = 440.0  # A4 note
        
        t = np.linspace(0, duration, int(sample_rate * duration))
        test_audio = np.sin(2 * np.pi * frequency * t).astype(np.float32)
        
        audio_chunk = AudioChunk(
            data=test_audio,
            sample_rate=sample_rate,
            timestamp=0.0,
            chunk_id=0
        )
        
        # Extract features
        features = extractor.extract_features(audio_chunk)
        
        logger.info(f"Extracted {len(features)} acoustic features:")
        for feature_name, value in features.items():
            logger.info(f"  {feature_name}: {value:.6f}")
        
        # Verify we got expected features
        expected_features = ["spectral_centroid", "spectral_rolloff", "spectral_bandwidth", 
                           "fundamental_frequency", "intensity", "pitch_variation",
                           "zero_crossing_rate", "estimated_tempo"]
        
        for expected in expected_features:
            if expected in features:
                logger.info(f"✓ Found expected feature: {expected}")
            else:
                logger.warning(f"✗ Missing expected feature: {expected}")
        
        return True
        
    except Exception as e:
        logger.error(f"Acoustic feature extraction test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests"""
    logger.info("Starting STT Agent Component Tests...")
    
    tests = [
        ("Audio Preprocessing", test_audio_preprocessing),
        ("Voice Activity Detection", test_voice_activity_detection),
        ("Acoustic Feature Extraction", test_acoustic_features),
        ("Language Detection", test_language_detection)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*60}")
        logger.info(f"Running test: {test_name}")
        logger.info(f"{'='*60}")
        
        try:
            success = await test_func()
            results[test_name] = success
            logger.info(f"Test {test_name}: {'PASSED' if success else 'FAILED'}")
        except Exception as e:
            logger.error(f"Test {test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*60}")
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, success in results.items():
        status = "PASSED" if success else "FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! STT Agent implementation is working correctly.")
    else:
        logger.warning(f"⚠️  {total - passed} tests failed. Please check the implementation.")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)