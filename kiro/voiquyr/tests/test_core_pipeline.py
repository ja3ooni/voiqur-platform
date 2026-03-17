#!/usr/bin/env python3
"""
Test for the core processing pipeline to verify integration functionality.
"""

import asyncio
import sys
import logging
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core import (
    ProcessingPipeline, ProcessingRequest, ProcessingContext,
    ProcessingStage, ProcessingStatus, process_voice
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_audio_processing():
    """Test audio-to-audio processing pipeline."""
    logger.info("Testing audio processing pipeline...")
    
    pipeline = ProcessingPipeline()
    
    # Create test context
    context = ProcessingContext(
        session_id="test_session_001",
        user_id="test_user",
        conversation_id="test_conv_001",
        language="en",
        accent="american",
        emotion_context={"primary_emotion": "neutral", "confidence": 0.8},
        conversation_history=[],
        user_preferences={"voice_speed": "normal", "voice_type": "female"},
        processing_metadata={"test_mode": True},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    # Create test request with mock audio data
    test_audio = b"MOCK_AUDIO_DATA_HELLO_WORLD" + b"0" * 2000  # Simulate 2KB audio
    
    request = ProcessingRequest(
        request_id="test_req_001",
        audio_data=test_audio,
        text_input=None,
        context=context,
        processing_options={"enable_emotion_detection": True},
        priority=7,
        timeout_seconds=30
    )
    
    # Process the request
    result = await pipeline.process_voice_request(request)
    
    print("\\n" + "="*60)
    print("AUDIO PROCESSING TEST")
    print("="*60)
    print(f"Request ID: {result.request_id}")
    print(f"Status: {result.status.value}")
    print(f"Stage: {result.stage.value}")
    print(f"Processing Time: {result.processing_time_ms:.1f}ms")
    print(f"Transcribed Text: {result.transcribed_text}")
    print(f"Generated Response: {result.generated_response}")
    print(f"Audio Generated: {result.synthesized_audio is not None}")
    
    print("\\nStage Timings:")
    for stage, timing in result.stage_timings.items():
        print(f"  {stage}: {timing:.1f}ms")
    
    print("\\nConfidence Scores:")
    for stage, confidence in result.confidence_scores.items():
        print(f"  {stage}: {confidence:.2f}")
    
    return result


async def test_text_processing():
    """Test text-to-audio processing pipeline."""
    logger.info("Testing text processing pipeline...")
    
    # Use convenience function
    result = await process_voice(
        text_input="Hello, how are you doing today?",
        session_id="test_session_002",
        user_id="test_user",
        language="en",
        accent="british",
        emotion_context={"primary_emotion": "happy", "confidence": 0.9},
        user_preferences={"voice_speed": "fast", "voice_type": "male"}
    )
    
    print("\\n" + "="*60)
    print("TEXT PROCESSING TEST")
    print("="*60)
    print(f"Request ID: {result.request_id}")
    print(f"Status: {result.status.value}")
    print(f"Processing Time: {result.processing_time_ms:.1f}ms")
    print(f"Input Text: {result.transcribed_text}")
    print(f"Generated Response: {result.generated_response}")
    print(f"Audio Generated: {result.synthesized_audio is not None}")
    
    return result


async def test_conversation_flow():
    """Test multi-turn conversation flow."""
    logger.info("Testing conversation flow...")
    
    session_id = "test_session_003"
    conversation_results = []
    
    # First turn
    result1 = await process_voice(
        text_input="Hello there!",
        session_id=session_id,
        user_id="test_user",
        language="en"
    )
    conversation_results.append(result1)
    
    # Second turn (should have conversation history)
    result2 = await process_voice(
        text_input="Can you help me with something?",
        session_id=session_id,
        user_id="test_user",
        language="en",
        conversation_history=result1.context.conversation_history
    )
    conversation_results.append(result2)
    
    # Third turn
    result3 = await process_voice(
        text_input="Thank you for your help!",
        session_id=session_id,
        user_id="test_user", 
        language="en",
        conversation_history=result2.context.conversation_history
    )
    conversation_results.append(result3)
    
    print("\\n" + "="*60)
    print("CONVERSATION FLOW TEST")
    print("="*60)
    
    for i, result in enumerate(conversation_results, 1):
        print(f"\\nTurn {i}:")
        print(f"  User: {result.transcribed_text}")
        print(f"  Assistant: {result.generated_response}")
        print(f"  Processing Time: {result.processing_time_ms:.1f}ms")
        print(f"  History Length: {len(result.context.conversation_history)}")
    
    return conversation_results


async def test_error_handling():
    """Test error handling and graceful degradation."""
    logger.info("Testing error handling...")
    
    pipeline = ProcessingPipeline({"graceful_degradation": True})
    
    # Test with empty audio data (should trigger error handling)
    result = await process_voice(
        audio_data=b"",  # Empty audio
        session_id="test_session_004",
        user_id="test_user",
        language="en"
    )
    
    print("\\n" + "="*60)
    print("ERROR HANDLING TEST")
    print("="*60)
    print(f"Status: {result.status.value}")
    print(f"Stage: {result.stage.value}")
    print(f"Error Message: {result.error_message}")
    print(f"Graceful Degradation: {result.generated_response is not None}")
    
    return result


async def test_performance_monitoring():
    """Test performance monitoring and metrics."""
    logger.info("Testing performance monitoring...")
    
    pipeline = ProcessingPipeline()
    
    # Process multiple requests to generate performance data
    for i in range(5):
        await process_voice(
            text_input=f"Test message number {i+1}",
            session_id=f"perf_test_{i}",
            user_id="perf_user",
            language="en"
        )
    
    # Get performance metrics
    metrics = pipeline.get_performance_metrics()
    
    print("\\n" + "="*60)
    print("PERFORMANCE MONITORING TEST")
    print("="*60)
    print(f"Active Requests: {metrics['active_requests']}")
    print(f"Completed Requests: {metrics['completed_requests']}")
    print(f"Context Cache Size: {metrics['context_cache_size']}")
    
    print("\\nStage Performance:")
    for stage, perf in metrics['stage_performance'].items():
        if perf['count'] > 0:
            print(f"  {stage}:")
            print(f"    Count: {perf['count']}")
            print(f"    Avg: {perf['avg_ms']:.1f}ms")
            print(f"    Min: {perf['min_ms']:.1f}ms")
            print(f"    Max: {perf['max_ms']:.1f}ms")
    
    return metrics


async def test_context_management():
    """Test context sharing and state management."""
    logger.info("Testing context management...")
    
    pipeline = ProcessingPipeline()
    session_id = "context_test_session"
    
    # First request to establish context
    result1 = await process_voice(
        text_input="My name is Alice",
        session_id=session_id,
        user_id="alice",
        language="en",
        user_preferences={"voice_type": "female", "speaking_rate": "slow"}
    )
    
    # Get context from pipeline
    context = pipeline.get_context(session_id)
    
    print("\\n" + "="*60)
    print("CONTEXT MANAGEMENT TEST")
    print("="*60)
    
    if context:
        print(f"Session ID: {context.session_id}")
        print(f"User ID: {context.user_id}")
        print(f"Language: {context.language}")
        print(f"User Preferences: {context.user_preferences}")
        print(f"Conversation History: {len(context.conversation_history)} exchanges")
        
        if context.conversation_history:
            print("\\nLatest Exchange:")
            latest = context.conversation_history[-1]
            print(f"  User: {latest['user_input']}")
            print(f"  Assistant: {latest['assistant_response']}")
            print(f"  Turn: {latest['turn_number']}")
    else:
        print("Context not found - using result context instead")
        context = result1.context
        print(f"Session ID: {context.session_id}")
        print(f"User ID: {context.user_id}")
        print(f"Language: {context.language}")
        print(f"Conversation History: {len(context.conversation_history)} exchanges")
    
    return context


async def main():
    """Main test function."""
    try:
        print("🔄 Starting Core Processing Pipeline Tests...")
        
        # Run individual tests
        audio_result = await test_audio_processing()
        text_result = await test_text_processing()
        conversation_results = await test_conversation_flow()
        error_result = await test_error_handling()
        performance_metrics = await test_performance_monitoring()
        context = await test_context_management()
        
        # Test summary
        print("\\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        tests_passed = 0
        total_tests = 6
        
        # Check audio processing
        if audio_result.status == ProcessingStatus.COMPLETED:
            print("✅ Audio Processing: PASSED")
            tests_passed += 1
        else:
            print("❌ Audio Processing: FAILED")
        
        # Check text processing
        if text_result.status == ProcessingStatus.COMPLETED:
            print("✅ Text Processing: PASSED")
            tests_passed += 1
        else:
            print("❌ Text Processing: FAILED")
        
        # Check conversation flow
        if all(r.status == ProcessingStatus.COMPLETED for r in conversation_results):
            print("✅ Conversation Flow: PASSED")
            tests_passed += 1
        else:
            print("❌ Conversation Flow: FAILED")
        
        # Check error handling
        if error_result.status == ProcessingStatus.FAILED and error_result.error_message:
            print("✅ Error Handling: PASSED")
            tests_passed += 1
        else:
            print("❌ Error Handling: FAILED")
        
        # Check performance monitoring
        if performance_metrics['completed_requests'] >= 5:
            print("✅ Performance Monitoring: PASSED")
            tests_passed += 1
        else:
            print("❌ Performance Monitoring: FAILED")
        
        # Check context management
        if context and len(context.conversation_history) > 0:
            print("✅ Context Management: PASSED")
            tests_passed += 1
        else:
            print("❌ Context Management: FAILED")
        
        print(f"\\nOverall: {tests_passed}/{total_tests} tests passed ({tests_passed/total_tests*100:.1f}%)")
        
        if tests_passed == total_tests:
            print("\\n🎉 All core pipeline tests passed!")
            return 0
        else:
            print(f"\\n⚠️  {total_tests - tests_passed} test(s) failed")
            return 1
        
    except Exception as e:
        print(f"\\n💥 Core pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)