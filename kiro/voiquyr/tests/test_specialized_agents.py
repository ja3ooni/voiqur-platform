#!/usr/bin/env python3
"""
Test script for specialized feature agents
Tests the Emotion, Accent, Lip Sync, and Arabic specialist agents
"""

import asyncio
import numpy as np
import logging
from src.agents.emotion_agent import EmotionAgent
from src.agents.accent_agent import AccentAgent
from src.agents.lip_sync_agent import LipSyncAgent
from src.agents.arabic_agent import ArabicAgent
from src.core.messaging import MessageBus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_emotion_agent():
    """Test the Emotion Agent"""
    logger.info("Testing Emotion Agent...")
    
    try:
        message_bus = MessageBus()
        agent = EmotionAgent("emotion_test", message_bus)
        
        # Initialize agent
        success = await agent.initialize()
        assert success, "Emotion agent initialization failed"
        
        # Test audio emotion detection
        test_audio = np.random.normal(0, 0.1, 16000)  # 1 second of test audio
        result = await agent.detect_emotion_from_audio(test_audio, 16000)
        
        assert result.primary_emotion is not None, "No emotion detected"
        assert 0.0 <= result.emotion_confidence <= 1.0, "Invalid confidence score"
        assert -1.0 <= result.sentiment_score <= 1.0, "Invalid sentiment score"
        
        logger.info(f"Detected emotion: {result.primary_emotion.value} (confidence: {result.emotion_confidence:.2f})")
        
        # Test text emotion detection
        test_text = "I am so happy and excited about this project!"
        text_result = await agent.detect_emotion_from_text(test_text)
        
        assert text_result.primary_emotion is not None, "No emotion detected from text"
        logger.info(f"Text emotion: {text_result.primary_emotion.value} (confidence: {text_result.emotion_confidence:.2f})")
        
        # Test emotion context creation
        context = await agent.create_emotion_context_for_tts(test_text, "text")
        assert context.emotion is not None, "No emotion context created"
        
        logger.info("✓ Emotion Agent test passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Emotion Agent test failed: {e}")
        return False


async def test_accent_agent():
    """Test the Accent Agent"""
    logger.info("Testing Accent Agent...")
    
    try:
        message_bus = MessageBus()
        agent = AccentAgent("accent_test", message_bus)
        
        # Initialize agent
        success = await agent.initialize()
        assert success, "Accent agent initialization failed"
        
        # Test accent detection
        test_audio = np.random.normal(0, 0.1, 16000)  # 1 second of test audio
        result = await agent.detect_accent_from_audio(test_audio, 16000)
        
        assert result.primary_accent is not None, "No accent detected"
        assert 0.0 <= result.accent_confidence <= 1.0, "Invalid confidence score"
        assert result.language is not None, "No language detected"
        
        logger.info(f"Detected accent: {result.primary_accent.value} (confidence: {result.accent_confidence:.2f})")
        logger.info(f"Language: {result.language}, Cultural context: {result.cultural_context.value}")
        
        # Test acoustic model recommendation
        recommendation = agent.get_acoustic_model_recommendation(
            result.primary_accent.value, result.language
        )
        assert "model_path" in recommendation, "No model recommendation provided"
        
        # Test processing adaptation
        adaptation = agent.adapt_processing_for_accent(result)
        assert "processing_params" in adaptation, "No processing adaptation provided"
        
        logger.info("✓ Accent Agent test passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Accent Agent test failed: {e}")
        return False


async def test_lip_sync_agent():
    """Test the Lip Sync Agent"""
    logger.info("Testing Lip Sync Agent...")
    
    try:
        message_bus = MessageBus()
        agent = LipSyncAgent("lip_sync_test", message_bus)
        
        # Initialize agent
        success = await agent.initialize()
        assert success, "Lip Sync agent initialization failed"
        
        # Test lip sync animation generation
        test_phonemes = [
            {"phoneme": "h", "start_time": 0.0, "end_time": 0.1, "confidence": 0.9},
            {"phoneme": "ɛ", "start_time": 0.1, "end_time": 0.3, "confidence": 0.95},
            {"phoneme": "l", "start_time": 0.3, "end_time": 0.4, "confidence": 0.9},
            {"phoneme": "oʊ", "start_time": 0.4, "end_time": 0.7, "confidence": 0.95}
        ]
        
        animation = await agent.generate_lip_sync_animation(
            test_phonemes, "en", "realistic_3d", "unity", 30
        )
        
        assert animation.animation_id is not None, "No animation ID generated"
        assert len(animation.viseme_frames) > 0, "No viseme frames generated"
        assert animation.total_duration > 0, "Invalid animation duration"
        
        logger.info(f"Generated animation: {len(animation.viseme_frames)} frames, {animation.total_duration:.2f}s")
        
        # Test real-time viseme retrieval
        viseme_frame = agent.get_realtime_viseme(animation.animation_id, 0.2)
        assert viseme_frame is not None, "No viseme frame retrieved"
        
        # Test engine format conversion
        converted = agent.convert_to_engine_format(animation, "unity")
        assert "animationClip" in converted, "Unity format conversion failed"
        
        logger.info("✓ Lip Sync Agent test passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Lip Sync Agent test failed: {e}")
        return False


async def test_arabic_agent():
    """Test the Arabic Agent"""
    logger.info("Testing Arabic Agent...")
    
    try:
        message_bus = MessageBus()
        agent = ArabicAgent("arabic_test", message_bus)
        
        # Initialize agent
        success = await agent.initialize()
        assert success, "Arabic agent initialization failed"
        
        # Test Arabic text analysis
        test_texts = [
            "مرحبا، كيف حالك؟ هذا نص تجريبي باللغة العربية.",  # MSA
            "إيه أخبارك؟ كله تمام؟",  # Egyptian
            "شو أخبارك؟ كيفك؟",  # Levantine
            "شلونك؟ زين؟"  # Gulf
        ]
        
        for i, text in enumerate(test_texts):
            analysis = await agent.analyze_arabic_text(text)
            
            assert analysis.dialect is not None, f"No dialect detected for text {i+1}"
            assert analysis.diacritized_text is not None, f"No diacritization for text {i+1}"
            assert analysis.cultural_context is not None, f"No cultural context for text {i+1}"
            
            logger.info(f"Text {i+1}: {analysis.dialect.value} (confidence: {analysis.dialect_confidence:.2f})")
            logger.info(f"  Cultural context: {analysis.cultural_context.value}")
            logger.info(f"  Formality: {analysis.formality_level.value}")
            
            # Test synthesis adaptation
            adaptations = await agent.adapt_for_arabic_synthesis(
                text, analysis.dialect.value, analysis.formality_level.value
            )
            assert "phonetic_adjustments" in adaptations, f"No phonetic adaptations for text {i+1}"
        
        # Test code-switching
        mixed_text = "مرحبا hello كيف حالك how are you؟"
        code_switch_analysis = await agent.handle_code_switching(mixed_text)
        
        assert len(code_switch_analysis.languages_detected) > 1, "Code-switching not detected"
        assert code_switch_analysis.switching_frequency > 0, "No switching frequency calculated"
        
        logger.info(f"Code-switching detected: {code_switch_analysis.languages_detected}")
        logger.info(f"Switching frequency: {code_switch_analysis.switching_frequency:.1f}%")
        
        logger.info("✓ Arabic Agent test passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Arabic Agent test failed: {e}")
        return False


async def main():
    """Run all specialized agent tests"""
    logger.info("Starting Specialized Feature Agents Tests")
    logger.info("=" * 50)
    
    tests = [
        test_emotion_agent,
        test_accent_agent,
        test_lip_sync_agent,
        test_arabic_agent
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            logger.error(f"Test failed with exception: {e}")
            results.append(False)
        
        logger.info("-" * 30)
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    logger.info("=" * 50)
    logger.info(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All specialized agent tests passed!")
        return True
    else:
        logger.error(f"❌ {total - passed} tests failed")
        return False


if __name__ == "__main__":
    asyncio.run(main())