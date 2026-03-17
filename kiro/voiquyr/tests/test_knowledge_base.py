#!/usr/bin/env python3
"""
Test script for the SharedKnowledgeBase implementation.
This script tests the core functionality of the knowledge base system.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from src.core import (
    MessageRouter, SharedKnowledgeBase, KnowledgeItem, 
    KnowledgeType, AccessLevel, ConflictResolutionStrategy
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_knowledge_base():
    """Test the SharedKnowledgeBase functionality."""
    
    # Initialize components
    message_router = MessageRouter()
    
    # Use in-memory databases for testing (would normally use real Redis/PostgreSQL)
    knowledge_base = SharedKnowledgeBase(
        message_router=message_router,
        redis_url="redis://localhost:6379",
        postgres_url="postgresql://localhost:5432/euvoice_test"
    )
    
    try:
        # Start the knowledge base (this will try to connect to databases)
        logger.info("Starting knowledge base...")
        await knowledge_base.start()
        logger.info("Knowledge base started successfully")
        
        # Test 1: Store and retrieve knowledge
        logger.info("\n=== Test 1: Store and Retrieve Knowledge ===")
        
        knowledge1 = KnowledgeItem(
            knowledge_id="test_knowledge_1",
            knowledge_type=KnowledgeType.FACT,
            key="agent_capabilities",
            value={"stt_accuracy": 0.95, "supported_languages": ["en", "fr", "de"]},
            owner_agent_id="stt_agent_1",
            access_level=AccessLevel.PUBLIC
        )
        
        # Store knowledge
        success = await knowledge_base.store_knowledge(knowledge1)
        logger.info(f"Store knowledge result: {success}")
        
        # Retrieve knowledge
        retrieved = await knowledge_base.get_knowledge("test_knowledge_1", "any_agent")
        if retrieved:
            logger.info(f"Retrieved knowledge: {retrieved.key} = {retrieved.value}")
        else:
            logger.error("Failed to retrieve knowledge")
        
        # Test 2: Knowledge search
        logger.info("\n=== Test 2: Knowledge Search ===")
        
        # Store more knowledge for search testing
        knowledge2 = KnowledgeItem(
            knowledge_id="test_knowledge_2",
            knowledge_type=KnowledgeType.CONFIGURATION,
            key="model_config",
            value={"model_name": "mistral-small", "temperature": 0.7},
            owner_agent_id="llm_agent_1",
            access_level=AccessLevel.PUBLIC
        )
        
        await knowledge_base.store_knowledge(knowledge2)
        
        # Search for knowledge
        search_results = await knowledge_base.search_knowledge("capabilities", requester_agent_id="test_agent")
        logger.info(f"Search results: {len(search_results)} items found")
        for item in search_results:
            logger.info(f"  - {item.key}: {item.value}")
        
        # Test 3: Knowledge validation
        logger.info("\n=== Test 3: Knowledge Validation ===")
        
        # Validate knowledge
        validation_success = await knowledge_base.validate_knowledge("test_knowledge_1", "validator_agent")
        logger.info(f"Validation result: {validation_success}")
        
        # Check updated validation count
        validated_knowledge = await knowledge_base.get_knowledge("test_knowledge_1", "any_agent")
        if validated_knowledge:
            logger.info(f"Validation count: {validated_knowledge.validation_count}")
            logger.info(f"Confidence score: {validated_knowledge.confidence_score}")
        
        # Test 4: Knowledge update
        logger.info("\n=== Test 4: Knowledge Update ===")
        
        # Update knowledge value
        new_value = {"stt_accuracy": 0.97, "supported_languages": ["en", "fr", "de", "es"]}
        update_success = await knowledge_base.update_knowledge("test_knowledge_1", new_value, "stt_agent_1")
        logger.info(f"Update result: {update_success}")
        
        # Verify update
        updated_knowledge = await knowledge_base.get_knowledge("test_knowledge_1", "any_agent")
        if updated_knowledge:
            logger.info(f"Updated value: {updated_knowledge.value}")
            logger.info(f"Version: {updated_knowledge.version}")
        
        # Test 5: Access control
        logger.info("\n=== Test 5: Access Control ===")
        
        # Create private knowledge
        private_knowledge = KnowledgeItem(
            knowledge_id="private_knowledge",
            knowledge_type=KnowledgeType.CONFIGURATION,
            key="secret_config",
            value={"api_key": "secret123"},
            owner_agent_id="secure_agent",
            access_level=AccessLevel.PRIVATE
        )
        
        await knowledge_base.store_knowledge(private_knowledge)
        
        # Try to access as owner (should succeed)
        owner_access = await knowledge_base.get_knowledge("private_knowledge", "secure_agent")
        logger.info(f"Owner access: {'Success' if owner_access else 'Failed'}")
        
        # Try to access as different agent (should fail)
        unauthorized_access = await knowledge_base.get_knowledge("private_knowledge", "other_agent")
        logger.info(f"Unauthorized access: {'Success' if unauthorized_access else 'Failed (as expected)'}")
        
        # Test 6: Get statistics
        logger.info("\n=== Test 6: Knowledge Base Statistics ===")
        
        stats = knowledge_base.get_knowledge_stats()
        logger.info(f"Knowledge base stats: {stats}")
        
        logger.info("\n=== All Tests Completed Successfully ===")
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        await knowledge_base.stop()
        logger.info("Knowledge base stopped")


async def test_conflict_resolution():
    """Test conflict resolution mechanisms."""
    logger.info("\n=== Testing Conflict Resolution ===")
    
    message_router = MessageRouter()
    knowledge_base = SharedKnowledgeBase(message_router)
    
    try:
        await knowledge_base.start()
        
        # Create conflicting knowledge items
        knowledge1 = KnowledgeItem(
            knowledge_id="conflict_test_1",
            knowledge_type=KnowledgeType.FACT,
            key="model_accuracy",
            value=0.95,
            owner_agent_id="agent_1",
            conflict_resolution_strategy=ConflictResolutionStrategy.TIMESTAMP_WINS
        )
        
        knowledge2 = KnowledgeItem(
            knowledge_id="conflict_test_2", 
            knowledge_type=KnowledgeType.FACT,
            key="model_accuracy",
            value=0.97,  # Different value - will cause conflict
            owner_agent_id="agent_2",
            conflict_resolution_strategy=ConflictResolutionStrategy.TIMESTAMP_WINS
        )
        
        # Store first knowledge
        await knowledge_base.store_knowledge(knowledge1)
        
        # Store second knowledge (should trigger conflict resolution)
        await knowledge_base.store_knowledge(knowledge2)
        
        # Check which knowledge won
        final_knowledge = await knowledge_base.get_knowledge_by_key("model_accuracy")
        if final_knowledge:
            logger.info(f"Conflict resolved. Final value: {final_knowledge[0].value}")
            logger.info(f"Winner agent: {final_knowledge[0].owner_agent_id}")
        
    except Exception as e:
        logger.error(f"Conflict resolution test failed: {e}")
    
    finally:
        await knowledge_base.stop()


if __name__ == "__main__":
    print("Testing SharedKnowledgeBase Implementation")
    print("=" * 50)
    
    # Note: This test requires Redis and PostgreSQL to be running
    # For development, you can use Docker:
    # docker run -d -p 6379:6379 redis:alpine
    # docker run -d -p 5432:5432 -e POSTGRES_DB=euvoice_test -e POSTGRES_PASSWORD=test postgres:alpine
    
    try:
        asyncio.run(test_knowledge_base())
        asyncio.run(test_conflict_resolution())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nTest failed: {e}")