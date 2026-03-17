#!/usr/bin/env python3
"""
Example usage of the SharedKnowledgeBase system.
Demonstrates how agents can share knowledge, handle conflicts, and subscribe to updates.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from src.core import (
    MessageRouter, SharedKnowledgeBase, KnowledgeItem, 
    KnowledgeType, AccessLevel, ConflictResolutionStrategy,
    KnowledgeSubscription
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ExampleAgent:
    """Example agent that uses the knowledge base."""
    
    def __init__(self, agent_id: str, knowledge_base: SharedKnowledgeBase):
        self.agent_id = agent_id
        self.knowledge_base = knowledge_base
        self.local_knowledge = {}
    
    async def store_capability_info(self, capability_name: str, performance_data: dict):
        """Store information about agent capabilities."""
        knowledge = KnowledgeItem(
            knowledge_id=f"{self.agent_id}_{capability_name}",
            knowledge_type=KnowledgeType.FACT,
            key=f"agent_capability_{capability_name}",
            value={
                "agent_id": self.agent_id,
                "capability": capability_name,
                "performance": performance_data,
                "last_updated": datetime.utcnow().isoformat()
            },
            owner_agent_id=self.agent_id,
            access_level=AccessLevel.PUBLIC
        )
        
        success = await self.knowledge_base.store_knowledge(knowledge)
        logger.info(f"Agent {self.agent_id} stored capability info: {success}")
        return success
    
    async def learn_from_experience(self, task_type: str, outcome: dict):
        """Store learning from task execution."""
        knowledge = KnowledgeItem(
            knowledge_id=f"{self.agent_id}_experience_{task_type}_{datetime.utcnow().timestamp()}",
            knowledge_type=KnowledgeType.EXPERIENCE,
            key=f"task_experience_{task_type}",
            value={
                "agent_id": self.agent_id,
                "task_type": task_type,
                "outcome": outcome,
                "learned_at": datetime.utcnow().isoformat()
            },
            owner_agent_id=self.agent_id,
            access_level=AccessLevel.PUBLIC,
            expires_at=datetime.utcnow() + timedelta(days=30)  # Experience expires after 30 days
        )
        
        success = await self.knowledge_base.store_knowledge(knowledge)
        logger.info(f"Agent {self.agent_id} stored experience: {success}")
        return success
    
    async def find_best_agent_for_task(self, capability_name: str):
        """Find the best agent for a specific capability."""
        # Search for agents with this capability
        agents_with_capability = await self.knowledge_base.search_knowledge(
            f"agent_capability_{capability_name}",
            knowledge_types=[KnowledgeType.FACT],
            requester_agent_id=self.agent_id
        )
        
        if not agents_with_capability:
            logger.info(f"No agents found with capability: {capability_name}")
            return None
        
        # Find the best performing agent
        best_agent = None
        best_score = 0
        
        for knowledge in agents_with_capability:
            performance = knowledge.value.get("performance", {})
            score = performance.get("accuracy", 0) * performance.get("speed", 1)
            
            if score > best_score:
                best_score = score
                best_agent = knowledge.value.get("agent_id")
        
        logger.info(f"Best agent for {capability_name}: {best_agent} (score: {best_score})")
        return best_agent
    
    async def subscribe_to_capability_updates(self, capability_name: str):
        """Subscribe to updates about a specific capability."""
        subscription = KnowledgeSubscription(
            subscription_id=f"{self.agent_id}_sub_{capability_name}",
            agent_id=self.agent_id,
            knowledge_pattern=f"agent_capability_{capability_name}",
            knowledge_types={KnowledgeType.FACT}
        )
        
        success = await self.knowledge_base.subscribe_to_knowledge(subscription)
        logger.info(f"Agent {self.agent_id} subscribed to {capability_name} updates: {success}")
        return success


async def demonstrate_knowledge_sharing():
    """Demonstrate knowledge sharing between agents."""
    logger.info("=== Demonstrating Knowledge Sharing ===")
    
    # Initialize the knowledge base
    message_router = MessageRouter()
    knowledge_base = SharedKnowledgeBase(message_router)
    
    try:
        await knowledge_base.start()
        
        # Create example agents
        stt_agent = ExampleAgent("stt_agent_1", knowledge_base)
        llm_agent = ExampleAgent("llm_agent_1", knowledge_base)
        tts_agent = ExampleAgent("tts_agent_1", knowledge_base)
        
        # Agents store their capability information
        await stt_agent.store_capability_info("speech_to_text", {
            "accuracy": 0.95,
            "speed": 1.2,  # seconds per minute of audio
            "languages": ["en", "fr", "de", "es"]
        })
        
        await llm_agent.store_capability_info("dialog_management", {
            "accuracy": 0.88,
            "speed": 0.5,  # seconds per response
            "context_length": 32000
        })
        
        await tts_agent.store_capability_info("text_to_speech", {
            "accuracy": 0.92,  # MOS score / 5
            "speed": 0.8,  # seconds per sentence
            "voices": ["natural", "expressive", "formal"]
        })
        
        # Agents learn from experiences
        await stt_agent.learn_from_experience("transcribe_noisy_audio", {
            "success": True,
            "accuracy_achieved": 0.87,
            "preprocessing_helped": True,
            "noise_type": "background_music"
        })
        
        await llm_agent.learn_from_experience("handle_interruption", {
            "success": True,
            "context_preserved": True,
            "response_time": 0.3,
            "user_satisfaction": 0.9
        })
        
        # Agent looks for the best STT agent
        best_stt = await llm_agent.find_best_agent_for_task("speech_to_text")
        
        # Agent subscribes to capability updates
        await llm_agent.subscribe_to_capability_updates("speech_to_text")
        
        # Show knowledge base statistics
        stats = knowledge_base.get_knowledge_stats()
        logger.info(f"Knowledge base statistics: {stats}")
        
    except Exception as e:
        logger.error(f"Demonstration failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await knowledge_base.stop()


async def demonstrate_conflict_resolution():
    """Demonstrate conflict resolution between agents."""
    logger.info("\n=== Demonstrating Conflict Resolution ===")
    
    message_router = MessageRouter()
    knowledge_base = SharedKnowledgeBase(message_router)
    
    try:
        await knowledge_base.start()
        
        # Two agents report different performance metrics for the same capability
        agent1 = ExampleAgent("performance_agent_1", knowledge_base)
        agent2 = ExampleAgent("performance_agent_2", knowledge_base)
        
        # Agent 1 reports performance
        knowledge1 = KnowledgeItem(
            knowledge_id="system_performance_1",
            knowledge_type=KnowledgeType.FACT,
            key="system_latency",
            value={"average_latency_ms": 85, "measured_by": "performance_agent_1"},
            owner_agent_id="performance_agent_1",
            access_level=AccessLevel.PUBLIC,
            conflict_resolution_strategy=ConflictResolutionStrategy.AUTHORITY_WINS
        )
        
        # Agent 2 reports different performance (conflict)
        knowledge2 = KnowledgeItem(
            knowledge_id="system_performance_2",
            knowledge_type=KnowledgeType.FACT,
            key="system_latency",
            value={"average_latency_ms": 92, "measured_by": "performance_agent_2"},
            owner_agent_id="performance_agent_2",
            access_level=AccessLevel.PUBLIC,
            conflict_resolution_strategy=ConflictResolutionStrategy.AUTHORITY_WINS,
            validation_count=2  # This agent has more validations
        )
        
        # Store both (second one should trigger conflict resolution)
        await knowledge_base.store_knowledge(knowledge1)
        await knowledge_base.store_knowledge(knowledge2)
        
        # Check the resolved value
        resolved_knowledge = await knowledge_base.get_knowledge_by_key("system_latency")
        if resolved_knowledge:
            logger.info(f"Conflict resolved. Final latency value: {resolved_knowledge[0].value}")
        
    except Exception as e:
        logger.error(f"Conflict resolution demonstration failed: {e}")
    
    finally:
        await knowledge_base.stop()


async def demonstrate_knowledge_expiration():
    """Demonstrate knowledge expiration and cleanup."""
    logger.info("\n=== Demonstrating Knowledge Expiration ===")
    
    message_router = MessageRouter()
    knowledge_base = SharedKnowledgeBase(message_router)
    
    try:
        await knowledge_base.start()
        
        # Store temporary knowledge that expires quickly
        temp_knowledge = KnowledgeItem(
            knowledge_id="temp_session_data",
            knowledge_type=KnowledgeType.TEMPORARY,
            key="user_session_123",
            value={"user_id": "user123", "preferences": {"language": "en"}},
            owner_agent_id="session_agent",
            access_level=AccessLevel.RESTRICTED,
            authorized_agents={"session_agent", "personalization_agent"},
            expires_at=datetime.utcnow() + timedelta(seconds=5)  # Expires in 5 seconds
        )
        
        await knowledge_base.store_knowledge(temp_knowledge)
        logger.info("Stored temporary knowledge (expires in 5 seconds)")
        
        # Retrieve immediately (should work)
        retrieved = await knowledge_base.get_knowledge("temp_session_data", "session_agent")
        logger.info(f"Immediate retrieval: {'Success' if retrieved else 'Failed'}")
        
        # Wait for expiration
        logger.info("Waiting for knowledge to expire...")
        await asyncio.sleep(6)
        
        # Try to retrieve after expiration (should fail)
        expired_retrieval = await knowledge_base.get_knowledge("temp_session_data", "session_agent")
        logger.info(f"Retrieval after expiration: {'Success' if expired_retrieval else 'Failed (as expected)'}")
        
    except Exception as e:
        logger.error(f"Expiration demonstration failed: {e}")
    
    finally:
        await knowledge_base.stop()


if __name__ == "__main__":
    print("EUVoice AI Knowledge Base Usage Examples")
    print("=" * 50)
    print("Note: This example requires Redis and PostgreSQL to be running.")
    print("For development, you can use Docker:")
    print("  docker run -d -p 6379:6379 redis:alpine")
    print("  docker run -d -p 5432:5432 -e POSTGRES_DB=euvoice -e POSTGRES_PASSWORD=test postgres:alpine")
    print()
    
    async def run_all_demonstrations():
        """Run all demonstrations."""
        try:
            await demonstrate_knowledge_sharing()
            await demonstrate_conflict_resolution()
            await demonstrate_knowledge_expiration()
            logger.info("\n=== All Demonstrations Completed ===")
        except Exception as e:
            logger.error(f"Demonstrations failed: {e}")
    
    try:
        asyncio.run(run_all_demonstrations())
    except KeyboardInterrupt:
        print("\nDemonstrations interrupted by user")
    except Exception as e:
        print(f"\nDemonstrations failed: {e}")