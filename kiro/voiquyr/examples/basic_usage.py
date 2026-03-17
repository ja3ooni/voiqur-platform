"""
Basic usage example of the EUVoice AI Multi-Agent Framework.
Demonstrates agent registration, task submission, and knowledge sharing.
"""

import asyncio
import logging
from datetime import datetime, timedelta
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from multi_agent_framework import MultiAgentFramework
from core import (
    AgentRegistration, AgentCapability, Task, KnowledgeItem,
    KnowledgeType, AccessLevel, Priority, TaskStatus
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Main example function."""
    
    # Create and start the framework
    framework = MultiAgentFramework()
    
    try:
        await framework.start()
        logger.info("Framework started successfully")
        
        # Example 1: Register agents
        await register_example_agents(framework)
        
        # Example 2: Submit tasks
        await submit_example_tasks(framework)
        
        # Example 3: Share knowledge
        await knowledge_sharing_example(framework)
        
        # Example 4: Monitor system health
        await monitoring_example(framework)
        
        # Wait a bit to see the system in action
        await asyncio.sleep(10)
        
        # Show final statistics
        stats = framework.get_framework_stats()
        logger.info(f"Final framework statistics: {stats}")
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
    
    finally:
        await framework.stop()
        logger.info("Framework stopped")


async def register_example_agents(framework: MultiAgentFramework):
    """Register example agents with different capabilities."""
    
    # STT Agent
    stt_capabilities = [
        AgentCapability(
            name="speech_to_text",
            description="Convert speech to text using Mistral Voxtral",
            input_schema={"audio_data": "bytes", "language": "string"},
            output_schema={"text": "string", "confidence": "float"}
        ),
        AgentCapability(
            name="language_detection",
            description="Detect language from audio",
            input_schema={"audio_data": "bytes"},
            output_schema={"language": "string", "confidence": "float"}
        )
    ]
    
    stt_registration = AgentRegistration(
        agent_id="stt_agent_001",
        agent_type="STT",
        capabilities=stt_capabilities,
        endpoint="http://localhost:8001/stt",
        metadata={"model": "mistral_voxtral_small", "languages": ["en", "fr", "de", "es"]}
    )
    
    await framework.register_agent(stt_registration)
    logger.info("STT Agent registered")
    
    # LLM Agent
    llm_capabilities = [
        AgentCapability(
            name="dialog_management",
            description="Manage conversation flow and context",
            input_schema={"text": "string", "context": "object"},
            output_schema={"response": "string", "context": "object"}
        ),
        AgentCapability(
            name="intent_recognition",
            description="Recognize user intents from text",
            input_schema={"text": "string"},
            output_schema={"intent": "string", "entities": "object"}
        )
    ]
    
    llm_registration = AgentRegistration(
        agent_id="llm_agent_001",
        agent_type="LLM",
        capabilities=llm_capabilities,
        endpoint="http://localhost:8002/llm",
        metadata={"model": "mistral_small_3.1", "context_length": 32000}
    )
    
    await framework.register_agent(llm_registration)
    logger.info("LLM Agent registered")
    
    # TTS Agent
    tts_capabilities = [
        AgentCapability(
            name="text_to_speech",
            description="Convert text to speech with EU accents",
            input_schema={"text": "string", "voice": "string", "language": "string"},
            output_schema={"audio_data": "bytes", "duration": "float"}
        ),
        AgentCapability(
            name="voice_cloning",
            description="Clone voice from sample",
            input_schema={"text": "string", "voice_sample": "bytes"},
            output_schema={"audio_data": "bytes"}
        )
    ]
    
    tts_registration = AgentRegistration(
        agent_id="tts_agent_001",
        agent_type="TTS",
        capabilities=tts_capabilities,
        endpoint="http://localhost:8003/tts",
        metadata={"model": "xtts_v2", "supported_accents": ["british", "french", "german"]}
    )
    
    await framework.register_agent(tts_registration)
    logger.info("TTS Agent registered")


async def submit_example_tasks(framework: MultiAgentFramework):
    """Submit example tasks to the framework."""
    
    # Task 1: Speech-to-Text processing
    stt_task = Task(
        description="Transcribe audio file to text",
        requirements=["REQ-2.1"],  # From requirements document
        context={
            "required_capabilities": ["speech_to_text"],
            "input_data": {
                "audio_file": "example_audio.wav",
                "language": "en"
            },
            "timeout_seconds": 30
        },
        priority=Priority.HIGH
    )
    
    await framework.submit_task(stt_task)
    logger.info(f"STT task submitted: {stt_task.task_id}")
    
    # Task 2: Dialog management
    llm_task = Task(
        description="Process user query and generate response",
        requirements=["REQ-2.2", "REQ-2.3"],
        dependencies=[stt_task.task_id],  # Depends on STT task
        context={
            "required_capabilities": ["dialog_management", "intent_recognition"],
            "input_data": {
                "user_text": "Hello, I need help with my account",
                "conversation_context": {}
            },
            "timeout_seconds": 15
        },
        priority=Priority.NORMAL
    )
    
    await framework.submit_task(llm_task)
    logger.info(f"LLM task submitted: {llm_task.task_id}")
    
    # Task 3: Text-to-Speech synthesis
    tts_task = Task(
        description="Convert response text to speech",
        requirements=["REQ-2.5"],
        dependencies=[llm_task.task_id],  # Depends on LLM task
        context={
            "required_capabilities": ["text_to_speech"],
            "input_data": {
                "text": "Hello! I'd be happy to help you with your account.",
                "voice": "british_female",
                "language": "en"
            },
            "timeout_seconds": 20
        },
        priority=Priority.NORMAL
    )
    
    await framework.submit_task(tts_task)
    logger.info(f"TTS task submitted: {tts_task.task_id}")


async def knowledge_sharing_example(framework: MultiAgentFramework):
    """Demonstrate knowledge sharing between agents."""
    
    # Store configuration knowledge
    config_knowledge = KnowledgeItem(
        knowledge_id="config_stt_models",
        knowledge_type=KnowledgeType.CONFIGURATION,
        key="stt_model_config",
        value={
            "default_model": "mistral_voxtral_small",
            "fallback_model": "nvidia_canary_1b",
            "supported_languages": ["en", "fr", "de", "es", "it", "pt"],
            "quality_threshold": 0.85
        },
        owner_agent_id="system",
        access_level=AccessLevel.PUBLIC,
        metadata={"version": "1.0", "last_updated": "2024-01-15"}
    )
    
    await framework.store_knowledge(config_knowledge)
    logger.info("STT configuration knowledge stored")
    
    # Store experience knowledge
    experience_knowledge = KnowledgeItem(
        knowledge_id="exp_accent_handling",
        knowledge_type=KnowledgeType.EXPERIENCE,
        key="accent_recognition_tips",
        value={
            "british_accent": {
                "preprocessing": "normalize_vowels",
                "model_adjustment": "increase_confidence_threshold",
                "common_issues": ["dropped_r", "vowel_shifts"]
            },
            "french_accent": {
                "preprocessing": "handle_liaison",
                "model_adjustment": "french_phoneme_mapping",
                "common_issues": ["silent_letters", "nasal_vowels"]
            }
        },
        owner_agent_id="stt_agent_001",
        access_level=AccessLevel.PUBLIC,
        confidence_score=0.9,
        expires_at=datetime.utcnow() + timedelta(days=30)
    )
    
    await framework.store_knowledge(experience_knowledge)
    logger.info("Accent handling experience knowledge stored")
    
    # Retrieve knowledge
    retrieved_config = await framework.get_knowledge("config_stt_models", "llm_agent_001")
    if retrieved_config:
        logger.info(f"Retrieved configuration: {retrieved_config.value}")
    
    retrieved_experience = await framework.get_knowledge("exp_accent_handling", "tts_agent_001")
    if retrieved_experience:
        logger.info(f"Retrieved experience: {retrieved_experience.key}")


async def monitoring_example(framework: MultiAgentFramework):
    """Demonstrate system monitoring capabilities."""
    
    # Get system health
    system_health = framework.get_system_health()
    logger.info(f"System health: {system_health['health_percentage']:.2%}")
    
    # Get individual agent health
    for agent_id in ["stt_agent_001", "llm_agent_001", "tts_agent_001"]:
        agent_health = framework.get_agent_health(agent_id)
        if agent_health:
            logger.info(f"Agent {agent_id} health: {agent_health['health_status']}")
    
    # Get framework statistics
    stats = framework.get_framework_stats()
    logger.info(f"Total agents registered: {stats['stats']['total_agents_registered']}")
    logger.info(f"Total tasks processed: {stats['stats']['total_tasks_processed']}")


if __name__ == "__main__":
    asyncio.run(main())