#!/usr/bin/env python3
"""
Test script for emotion-aware TTS synthesis integration
Tests the integration between Emotion Agent and TTS Agent
"""

import asyncio
import logging
import numpy as np
import base64
from src.agents.emotion_agent import EmotionAgent, EmotionType
from src.agents.tts_agent import TTSAgent
from src.core.messaging import MessageRouter, MessageBus
from src.core.models import AgentRegistration, AgentCapability

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_emotion_agent():
    """Test basic emotion agent functionality"""
    print("\n=== Testing Emotion Agent ===")
    
    # Create message bus
    router = MessageRouter()
    message_bus = MessageBus(router)
    
    # Create emotion agent
    emotion_agent = EmotionAgent("emotion_agent", message_bus)
    
    # Register agent
    registration = AgentRegistration(
        agent_id="emotion_agent",
        agent_type="emotion",
        capabilities=emotion_agent.state.capabilities,
        endpoint="local"
    )
    await router.register_agent(registration)
    
    # Initialize agent
    success = await emotion_agent.initialize()
    print(f"Emotion Agent initialized: {success}")
    
    # Test text emotion detection
    test_texts = [
        "I'm so happy and excited about this!",
        "This is really sad and disappointing.",
        "I'm furious and angry about this situation!",
        "What a calm and peaceful day.",
        "This is a neutral statement."
    ]
    
    for text in test_texts:
        result = await emotion_agent.detect_emotion_from_text(text)
        print(f"Text: '{text}'")
        print(f"  Emotion: {result.primary_emotion.value} (confidence: {result.emotion_confidence:.2f})")
        print(f"  Sentiment: {result.sentiment_score:.2f}")
        print(f"  Arousal: {result.arousal:.2f}, Valence: {result.valence:.2f}")
        print(f"  Intensity: {result.intensity:.2f}")
        print()
    
    # Test audio emotion detection
    print("Testing audio emotion detection...")
    
    # Generate test audio signals with different characteristics
    sample_rate = 16000
    duration = 2.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Happy audio (higher pitch, more variation)
    happy_audio = 0.3 * np.sin(2 * np.pi * 300 * t) + 0.1 * np.sin(2 * np.pi * 600 * t)
    happy_audio += 0.05 * np.random.normal(0, 1, len(happy_audio))
    
    result = await emotion_agent.detect_emotion_from_audio(happy_audio, sample_rate)
    print(f"Happy audio - Emotion: {result.primary_emotion.value} (confidence: {result.emotion_confidence:.2f})")
    
    # Sad audio (lower pitch, less variation)
    sad_audio = 0.2 * np.sin(2 * np.pi * 150 * t) + 0.05 * np.sin(2 * np.pi * 300 * t)
    sad_audio += 0.02 * np.random.normal(0, 1, len(sad_audio))
    
    result = await emotion_agent.detect_emotion_from_audio(sad_audio, sample_rate)
    print(f"Sad audio - Emotion: {result.primary_emotion.value} (confidence: {result.emotion_confidence:.2f})")
    
    return emotion_agent


async def test_tts_emotion_integration():
    """Test TTS agent integration with emotion agent"""
    print("\n=== Testing TTS-Emotion Integration ===")
    
    # Create message bus
    router = MessageRouter()
    message_bus = MessageBus(router)
    
    # Create and register emotion agent
    emotion_agent = EmotionAgent("emotion_agent", message_bus)
    emotion_registration = AgentRegistration(
        agent_id="emotion_agent",
        agent_type="emotion",
        capabilities=emotion_agent.state.capabilities,
        endpoint="local"
    )
    await router.register_agent(emotion_registration)
    await emotion_agent.initialize()
    
    # Create and register TTS agent
    tts_agent = TTSAgent("tts_agent", message_bus)
    tts_registration = AgentRegistration(
        agent_id="tts_agent",
        agent_type="tts",
        capabilities=tts_agent.state.capabilities,
        endpoint="local"
    )
    await router.register_agent(tts_registration)
    await tts_agent.initialize()
    
    # Test emotion context creation
    test_text = "I'm absolutely thrilled and excited about this amazing opportunity!"
    
    emotion_context = await emotion_agent.create_emotion_context_for_tts(test_text, "text")
    print(f"Emotion context for '{test_text}':")
    print(f"  Emotion: {emotion_context.emotion}")
    print(f"  Intensity: {emotion_context.intensity:.2f}")
    print(f"  Sentiment: {emotion_context.sentiment_score:.2f}")
    print(f"  Arousal: {emotion_context.arousal:.2f}")
    print(f"  Valence: {emotion_context.valence:.2f}")
    print()
    
    # Test emotion-aware synthesis
    emotion_context_dict = {
        "emotion": emotion_context.emotion,
        "intensity": emotion_context.intensity,
        "sentiment_score": emotion_context.sentiment_score,
        "arousal": emotion_context.arousal,
        "valence": emotion_context.valence,
        "confidence": emotion_context.confidence
    }
    
    result = await tts_agent.synthesize_with_emotion(
        text=test_text,
        emotion_context=emotion_context_dict
    )
    
    print(f"Emotion-aware synthesis result:")
    print(f"  Duration: {result.duration:.2f}s")
    print(f"  Quality score: {result.quality_score:.2f}")
    print(f"  Applied emotion: {result.metadata.get('applied_emotion', 'unknown')}")
    print(f"  Applied intensity: {result.metadata.get('applied_intensity', 0):.2f}")
    print()
    
    # Test automatic emotion detection and synthesis
    print("Testing automatic emotion detection and synthesis...")
    
    test_texts_emotions = [
        "I'm so happy and excited!",
        "This is really sad and disappointing.",
        "I'm absolutely furious about this!",
        "What a calm and peaceful moment.",
        "This is just a normal statement."
    ]
    
    for text in test_texts_emotions:
        result = await tts_agent.synthesize_with_emotion_detection(text)
        
        print(f"Text: '{text}'")
        print(f"  Duration: {result.duration:.2f}s")
        print(f"  Applied emotion: {result.metadata.get('applied_emotion', 'unknown')}")
        print(f"  Applied intensity: {result.metadata.get('applied_intensity', 0):.2f}")
        print(f"  Emotion source: {result.metadata.get('emotion_source', 'unknown')}")
        print()
    
    return tts_agent, emotion_agent


async def test_message_based_communication():
    """Test message-based communication between agents"""
    print("\n=== Testing Message-Based Communication ===")
    
    # Create message bus
    router = MessageRouter()
    message_bus = MessageBus(router)
    
    # Create and register agents
    emotion_agent = EmotionAgent("emotion_agent", message_bus)
    tts_agent = TTSAgent("tts_agent", message_bus)
    
    # Register agents
    await router.register_agent(AgentRegistration(
        agent_id="emotion_agent", agent_type="emotion",
        capabilities=emotion_agent.state.capabilities, endpoint="local"
    ))
    await router.register_agent(AgentRegistration(
        agent_id="tts_agent", agent_type="tts",
        capabilities=tts_agent.state.capabilities, endpoint="local"
    ))
    
    # Initialize agents
    await emotion_agent.initialize()
    await tts_agent.initialize()
    
    # Test emotion detection request
    from src.core.models import AgentMessage, Priority
    
    emotion_request = AgentMessage(
        sender_id="test_client",
        receiver_id="emotion_agent",
        message_type="emotion_detection_request",
        payload={
            "input_data": "I'm incredibly excited and happy about this wonderful news!",
            "input_type": "text"
        },
        priority=Priority.HIGH
    )
    
    # Send message
    await router.send_message(emotion_request)
    
    # Process message
    messages = await router.get_messages("emotion_agent", max_messages=1)
    if messages:
        response = await emotion_agent.handle_message(messages[0])
        if response:
            print("Emotion detection response:")
            print(f"  Emotion: {response.payload['emotion']}")
            print(f"  Confidence: {response.payload['confidence']:.2f}")
            print(f"  Sentiment: {response.payload['sentiment_score']:.2f}")
            print(f"  Arousal: {response.payload['arousal']:.2f}")
            print(f"  Valence: {response.payload['valence']:.2f}")
            print()
    
    # Test emotion synthesis request
    emotion_synthesis_request = AgentMessage(
        sender_id="test_client",
        receiver_id="tts_agent",
        message_type="auto_emotion_synthesis_request",
        payload={
            "text": "I'm absolutely thrilled about this amazing opportunity!",
            "voice_id": "en_us_female_1"
        },
        priority=Priority.HIGH
    )
    
    # Send message
    await router.send_message(emotion_synthesis_request)
    
    # Process message
    messages = await router.get_messages("tts_agent", max_messages=1)
    if messages:
        response = await tts_agent.handle_message(messages[0])
        if response:
            print("Auto emotion synthesis response:")
            print(f"  Duration: {response.payload['duration']:.2f}s")
            print(f"  Quality: {response.payload['quality_score']:.2f}")
            print(f"  Audio data length: {len(response.payload['audio_data'])} chars (base64)")
            print(f"  Metadata: {response.payload.get('metadata', {})}")
            print()


async def test_performance_metrics():
    """Test performance metrics and monitoring"""
    print("\n=== Testing Performance Metrics ===")
    
    # Create agents
    router = MessageRouter()
    message_bus = MessageBus(router)
    
    emotion_agent = EmotionAgent("emotion_agent", message_bus)
    tts_agent = TTSAgent("tts_agent", message_bus)
    
    await emotion_agent.initialize()
    await tts_agent.initialize()
    
    # Perform multiple operations to generate metrics
    test_texts = [
        "I'm so happy!",
        "This is sad.",
        "I'm angry!",
        "Very excited!",
        "Calm and peaceful."
    ]
    
    for text in test_texts:
        await emotion_agent.detect_emotion_from_text(text)
        await tts_agent.synthesize_with_emotion_detection(text)
    
    # Get performance stats
    emotion_stats = emotion_agent.get_performance_stats()
    print("Emotion Agent Performance:")
    print(f"  Total detections: {emotion_stats['performance_metrics']['total_detections']}")
    print(f"  Text detections: {emotion_stats['performance_metrics']['text_detections']}")
    print(f"  Average processing time: {emotion_stats['performance_metrics']['average_processing_time']:.4f}s")
    print(f"  Average confidence: {emotion_stats['performance_metrics']['average_confidence']:.2f}")
    print()
    
    print("TTS Agent Performance:")
    print(f"  Total syntheses: {tts_agent.performance_metrics['total_syntheses']}")
    print(f"  Average synthesis time: {tts_agent.performance_metrics['average_synthesis_time']:.4f}s")
    print(f"  Average quality score: {tts_agent.performance_metrics['average_quality_score']:.2f}")
    print()


async def main():
    """Run all tests"""
    print("Starting Emotion-Aware TTS Integration Tests")
    print("=" * 50)
    
    try:
        # Test individual components
        await test_emotion_agent()
        await test_tts_emotion_integration()
        await test_message_based_communication()
        await test_performance_metrics()
        
        print("\n" + "=" * 50)
        print("All tests completed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())