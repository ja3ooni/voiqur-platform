"""
Shared knowledge base system for multi-agent coordination.
Implements distributed knowledge storage with Redis/PostgreSQL backend,
knowledge sharing protocols, and conflict resolution mechanisms.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set, Any, Union, Tuple
from datetime import datetime, timedelta
from enum import Enum
import json
import hashlib
from collections import defaultdict
import asyncpg
import aioredis
from pydantic import BaseModel, Field

from .models import AgentMessage, MessageType, Priority
from .messaging import MessageRouter, MessageBus


logger = logging.getLogger(__name__)


class KnowledgeType(str, Enum):
    """Types of knowledge that can be stored."""
    FACT = "fact"
    RULE = "rule"
    PROCEDURE = "procedure"
    EXPERIENCE = "experience"
    CONFIGURATION = "configuration"
    TEMPORARY = "temporary"


class AccessLevel(str, Enum):
    """Access levels for knowledge items."""
    PUBLIC = "public"
    RESTRICTED = "restricted"
    PRIVATE = "private"
    SYSTEM = "system"


class ConflictResolutionStrategy(str, Enum):
    """Strategies for resolving knowledge conflicts."""
    TIMESTAMP_WINS = "timestamp_wins"
    AUTHORITY_WINS = "authority_wins"
    MERGE = "merge"
    VOTE = "vote"
    MANUAL = "manual"


class KnowledgeItem(BaseModel):
    """Represents a piece of knowledge in the system."""
    
    knowledge_id: str = Field(..., description="Unique identifier for the knowledge item")
    knowledge_type: KnowledgeType = Field(..., description="Type of knowledge")
    key: str = Field(..., description="Knowledge key/topic")
    value: Any = Field(..., description="Knowledge value/content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    # Ownership and access
    owner_agent_id: str = Field(..., description="Agent that created this knowledge")
    access_level: AccessLevel = Field(default=AccessLevel.PUBLIC, description="Access level")
    authorized_agents: Set[str] = Field(default_factory=set, description="Agents with access")
    
    # Versioning and history
    version: int = Field(default=1, description="Version number")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(None, description="Expiration time")
    
    # Validation and trust
    confidence_score: float = Field(default=1.0, description="Confidence in this knowledge (0-1)")
    validation_count: int = Field(default=0, description="Number of validations")
    validators: Set[str] = Field(default_factory=set, description="Agents that validated this")
    
    # Conflict resolution
    conflict_resolution_strategy: ConflictResolutionStrategy = Field(
        default=ConflictResolutionStrategy.TIMESTAMP_WINS
    )
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            set: lambda v: list(v)
        }
    
    def is_expired(self) -> bool:
        """Check if the knowledge item has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def can_access(self, agent_id: str) -> bool:
        """Check if an agent can access this knowledge."""
        if self.access_level == AccessLevel.PUBLIC:
            return True
        elif self.access_level == AccessLevel.PRIVATE:
            return agent_id == self.owner_agent_id
        elif self.access_level == AccessLevel.RESTRICTED:
            return agent_id in self.authorized_agents or agent_id == self.owner_agent_id
        elif self.access_level == AccessLevel.SYSTEM:
            return False  # Only system can access
        return False
    
    def update_value(self, new_value: Any, updater_agent_id: str) -> None:
        """Update the knowledge value."""
        self.value = new_value
        self.updated_at = datetime.utcnow()
        self.version += 1
        if updater_agent_id != self.owner_agent_id:
            self.metadata["last_updater"] = updater_agent_id
    
    def add_validation(self, validator_agent_id: str) -> None:
        """Add a validation from an agent."""
        if validator_agent_id not in self.validators:
            self.validators.add(validator_agent_id)
            self.validation_count += 1
            # Increase confidence based on validations
            self.confidence_score = min(1.0, self.confidence_score + 0.1)


class KnowledgeConflict(BaseModel):
    """Represents a conflict between knowledge items."""
    
    conflict_id: str = Field(..., description="Unique conflict identifier")
    conflicting_items: List[KnowledgeItem] = Field(..., description="Conflicting knowledge items")
    conflict_type: str = Field(..., description="Type of conflict")
    resolution_strategy: ConflictResolutionStrategy = Field(..., description="Resolution strategy")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = Field(None)
    resolution: Optional[KnowledgeItem] = Field(None, description="Resolved knowledge item")
    votes: Dict[str, str] = Field(default_factory=dict, description="Agent votes (agent_id -> item_id)")


class KnowledgeSubscription(BaseModel):
    """Represents a subscription to knowledge updates."""
    
    subscription_id: str = Field(..., description="Unique subscription identifier")
    agent_id: str = Field(..., description="Subscribing agent")
    knowledge_pattern: str = Field(..., description="Knowledge key pattern to match")
    knowledge_types: Set[KnowledgeType] = Field(default_factory=set, description="Types to subscribe to")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    active: bool = Field(default=True, description="Whether subscription is active")


class SharedKnowledgeBase:
    """
    Distributed knowledge storage system with Redis/PostgreSQL backend.
    Handles knowledge sharing, conflict resolution, and concurrent updates.
    """
    
    def __init__(self, message_router: MessageRouter, 
                 redis_url: str = "redis://localhost:6379",
                 postgres_url: str = "postgresql://localhost:5432/euvoice"):
        self.message_router = message_router
        self.message_bus = MessageBus(message_router)
        
        # Database connections
        self.redis_url = redis_url
        self.postgres_url = postgres_url
        self.redis_client: Optional[aioredis.Redis] = None
        self.postgres_pool: Optional[asyncpg.Pool] = None
        
        # In-memory caches
        self.knowledge_cache: Dict[str, KnowledgeItem] = {}
        self.subscriptions: Dict[str, KnowledgeSubscription] = {}
        self.active_conflicts: Dict[str, KnowledgeConflict] = {}
        
        # Configuration
        self.cache_ttl = 300  # 5 minutes
        self.conflict_resolution_timeout = timedelta(minutes=10)
        self.knowledge_sync_interval = 30.0  # seconds
        
        # Runtime state
        self.sync_task: Optional[asyncio.Task] = None
        self.is_running = False
        
        # Statistics
        self.stats = {
            "total_knowledge_items": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "conflicts_resolved": 0,
            "subscriptions_active": 0
        }
    
    async def start(self) -> None:
        """Start the knowledge base system."""
        if self.is_running:
            return
        
        logger.info("Starting Shared Knowledge Base")
        
        # Initialize database connections
        await self._initialize_connections()
        await self._initialize_schema()
        
        self.is_running = True
        self.sync_task = asyncio.create_task(self._sync_loop())
    
    async def stop(self) -> None:
        """Stop the knowledge base system."""
        if not self.is_running:
            return
        
        logger.info("Stopping Shared Knowledge Base")
        self.is_running = False
        
        if self.sync_task:
            self.sync_task.cancel()
            try:
                await self.sync_task
            except asyncio.CancelledError:
                pass
        
        # Close database connections
        if self.redis_client:
            await self.redis_client.close()
        
        if self.postgres_pool:
            await self.postgres_pool.close()
    
    async def _initialize_connections(self) -> None:
        """Initialize database connections."""
        try:
            # Initialize Redis connection
            self.redis_client = aioredis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("Redis connection established")
            
            # Initialize PostgreSQL connection pool
            self.postgres_pool = await asyncpg.create_pool(self.postgres_url)
            logger.info("PostgreSQL connection pool established")
            
        except Exception as e:
            logger.error(f"Failed to initialize database connections: {e}")
            raise
    
    async def _initialize_schema(self) -> None:
        """Initialize database schema."""
        if not self.postgres_pool:
            return
        
        async with self.postgres_pool.acquire() as conn:
            # Create knowledge_items table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_items (
                    knowledge_id VARCHAR(255) PRIMARY KEY,
                    knowledge_type VARCHAR(50) NOT NULL,
                    key VARCHAR(255) NOT NULL,
                    value JSONB NOT NULL,
                    metadata JSONB DEFAULT '{}',
                    owner_agent_id VARCHAR(255) NOT NULL,
                    access_level VARCHAR(50) DEFAULT 'public',
                    authorized_agents JSONB DEFAULT '[]',
                    version INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    expires_at TIMESTAMP NULL,
                    confidence_score FLOAT DEFAULT 1.0,
                    validation_count INTEGER DEFAULT 0,
                    validators JSONB DEFAULT '[]',
                    conflict_resolution_strategy VARCHAR(50) DEFAULT 'timestamp_wins'
                )
            """)
            
            # Create indexes
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_key ON knowledge_items(key)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_type ON knowledge_items(knowledge_type)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_owner ON knowledge_items(owner_agent_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_expires ON knowledge_items(expires_at)")
            
            # Create conflicts table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_conflicts (
                    conflict_id VARCHAR(255) PRIMARY KEY,
                    conflicting_items JSONB NOT NULL,
                    conflict_type VARCHAR(100) NOT NULL,
                    resolution_strategy VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    resolved_at TIMESTAMP NULL,
                    resolution JSONB NULL,
                    votes JSONB DEFAULT '{}'
                )
            """)
            
            logger.info("Database schema initialized")
    
    async def store_knowledge(self, knowledge: KnowledgeItem) -> bool:
        """Store a knowledge item."""
        try:
            # Check for conflicts
            existing_items = await self.get_knowledge_by_key(knowledge.key)
            conflicts = [item for item in existing_items 
                        if item.knowledge_id != knowledge.knowledge_id and 
                        item.value != knowledge.value]
            
            if conflicts:
                await self._handle_knowledge_conflict(knowledge, conflicts)
                return True  # Conflict handling will resolve this
            
            # Store in PostgreSQL
            await self._store_in_postgres(knowledge)
            
            # Cache in Redis
            await self._cache_in_redis(knowledge)
            
            # Update local cache
            self.knowledge_cache[knowledge.knowledge_id] = knowledge
            
            # Notify subscribers
            await self._notify_subscribers(knowledge, "created")
            
            self.stats["total_knowledge_items"] += 1
            logger.info(f"Knowledge stored: {knowledge.knowledge_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store knowledge {knowledge.knowledge_id}: {e}")
            return False
    
    async def get_knowledge(self, knowledge_id: str, requester_agent_id: str) -> Optional[KnowledgeItem]:
        """Get a knowledge item by ID."""
        try:
            # Check local cache first
            if knowledge_id in self.knowledge_cache:
                knowledge = self.knowledge_cache[knowledge_id]
                if knowledge.can_access(requester_agent_id) and not knowledge.is_expired():
                    self.stats["cache_hits"] += 1
                    return knowledge
            
            # Check Redis cache
            cached_data = await self.redis_client.get(f"knowledge:{knowledge_id}")
            if cached_data:
                knowledge_dict = json.loads(cached_data)
                knowledge = KnowledgeItem(**knowledge_dict)
                if knowledge.can_access(requester_agent_id) and not knowledge.is_expired():
                    self.knowledge_cache[knowledge_id] = knowledge
                    self.stats["cache_hits"] += 1
                    return knowledge
            
            # Query PostgreSQL
            knowledge = await self._get_from_postgres(knowledge_id)
            if knowledge and knowledge.can_access(requester_agent_id) and not knowledge.is_expired():
                # Update caches
                self.knowledge_cache[knowledge_id] = knowledge
                await self._cache_in_redis(knowledge)
                self.stats["cache_misses"] += 1
                return knowledge
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get knowledge {knowledge_id}: {e}")
            return None
    
    async def get_knowledge_by_key(self, key: str, requester_agent_id: Optional[str] = None) -> List[KnowledgeItem]:
        """Get all knowledge items with a specific key."""
        try:
            if not self.postgres_pool:
                return []
            
            async with self.postgres_pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT * FROM knowledge_items WHERE key = $1 AND (expires_at IS NULL OR expires_at > NOW())",
                    key
                )
                
                knowledge_items = []
                for row in rows:
                    knowledge = self._row_to_knowledge_item(row)
                    if requester_agent_id is None or knowledge.can_access(requester_agent_id):
                        knowledge_items.append(knowledge)
                
                return knowledge_items
                
        except Exception as e:
            logger.error(f"Failed to get knowledge by key {key}: {e}")
            return []
    
    async def update_knowledge(self, knowledge_id: str, new_value: Any, 
                             updater_agent_id: str) -> bool:
        """Update a knowledge item."""
        try:
            knowledge = await self.get_knowledge(knowledge_id, updater_agent_id)
            if not knowledge:
                logger.error(f"Knowledge {knowledge_id} not found or access denied")
                return False
            
            # Check if agent can update
            if not (knowledge.owner_agent_id == updater_agent_id or 
                   knowledge.access_level == AccessLevel.PUBLIC):
                logger.error(f"Agent {updater_agent_id} cannot update knowledge {knowledge_id}")
                return False
            
            # Update the knowledge
            old_value = knowledge.value
            knowledge.update_value(new_value, updater_agent_id)
            
            # Store updated knowledge
            await self._store_in_postgres(knowledge)
            await self._cache_in_redis(knowledge)
            self.knowledge_cache[knowledge_id] = knowledge
            
            # Notify subscribers
            await self._notify_subscribers(knowledge, "updated", {"old_value": old_value})
            
            logger.info(f"Knowledge updated: {knowledge_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update knowledge {knowledge_id}: {e}")
            return False
    
    async def delete_knowledge(self, knowledge_id: str, requester_agent_id: str) -> bool:
        """Delete a knowledge item."""
        try:
            knowledge = await self.get_knowledge(knowledge_id, requester_agent_id)
            if not knowledge:
                return False
            
            # Check if agent can delete
            if knowledge.owner_agent_id != requester_agent_id:
                logger.error(f"Agent {requester_agent_id} cannot delete knowledge {knowledge_id}")
                return False
            
            # Delete from PostgreSQL
            if self.postgres_pool:
                async with self.postgres_pool.acquire() as conn:
                    await conn.execute("DELETE FROM knowledge_items WHERE knowledge_id = $1", knowledge_id)
            
            # Remove from Redis
            if self.redis_client:
                await self.redis_client.delete(f"knowledge:{knowledge_id}")
            
            # Remove from local cache
            if knowledge_id in self.knowledge_cache:
                del self.knowledge_cache[knowledge_id]
            
            # Notify subscribers
            await self._notify_subscribers(knowledge, "deleted")
            
            logger.info(f"Knowledge deleted: {knowledge_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete knowledge {knowledge_id}: {e}")
            return False
    
    async def subscribe_to_knowledge(self, subscription: KnowledgeSubscription) -> bool:
        """Subscribe to knowledge updates."""
        try:
            self.subscriptions[subscription.subscription_id] = subscription
            self.stats["subscriptions_active"] = len([s for s in self.subscriptions.values() if s.active])
            
            logger.info(f"Knowledge subscription created: {subscription.subscription_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create subscription {subscription.subscription_id}: {e}")
            return False
    
    async def unsubscribe_from_knowledge(self, subscription_id: str) -> bool:
        """Unsubscribe from knowledge updates."""
        if subscription_id in self.subscriptions:
            del self.subscriptions[subscription_id]
            self.stats["subscriptions_active"] = len([s for s in self.subscriptions.values() if s.active])
            logger.info(f"Knowledge subscription removed: {subscription_id}")
            return True
        return False
    
    async def validate_knowledge(self, knowledge_id: str, validator_agent_id: str) -> bool:
        """Validate a knowledge item."""
        try:
            knowledge = await self.get_knowledge(knowledge_id, validator_agent_id)
            if not knowledge:
                return False
            
            knowledge.add_validation(validator_agent_id)
            
            # Update in storage
            await self._store_in_postgres(knowledge)
            await self._cache_in_redis(knowledge)
            self.knowledge_cache[knowledge_id] = knowledge
            
            logger.info(f"Knowledge validated: {knowledge_id} by {validator_agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate knowledge {knowledge_id}: {e}")
            return False
    
    async def search_knowledge(self, query: str, knowledge_types: Optional[List[KnowledgeType]] = None,
                             requester_agent_id: Optional[str] = None) -> List[KnowledgeItem]:
        """Search for knowledge items."""
        try:
            if not self.postgres_pool:
                return []
            
            # Build query
            where_conditions = ["(expires_at IS NULL OR expires_at > NOW())"]
            params = []
            param_count = 0
            
            # Add text search
            param_count += 1
            where_conditions.append(f"(key ILIKE ${param_count} OR value::text ILIKE ${param_count})")
            params.append(f"%{query}%")
            
            # Add knowledge type filter
            if knowledge_types:
                param_count += 1
                where_conditions.append(f"knowledge_type = ANY(${param_count})")
                params.append([kt.value for kt in knowledge_types])
            
            query_sql = f"""
                SELECT * FROM knowledge_items 
                WHERE {' AND '.join(where_conditions)}
                ORDER BY confidence_score DESC, updated_at DESC
                LIMIT 100
            """
            
            async with self.postgres_pool.acquire() as conn:
                rows = await conn.fetch(query_sql, *params)
                
                knowledge_items = []
                for row in rows:
                    knowledge = self._row_to_knowledge_item(row)
                    if requester_agent_id is None or knowledge.can_access(requester_agent_id):
                        knowledge_items.append(knowledge)
                
                return knowledge_items
                
        except Exception as e:
            logger.error(f"Failed to search knowledge: {e}")
            return []
    
    async def _handle_knowledge_conflict(self, new_knowledge: KnowledgeItem, 
                                       conflicting_items: List[KnowledgeItem]) -> None:
        """Handle conflicts between knowledge items."""
        conflict_id = f"conflict_{new_knowledge.key}_{datetime.utcnow().timestamp()}"
        
        all_items = [new_knowledge] + conflicting_items
        conflict = KnowledgeConflict(
            conflict_id=conflict_id,
            conflicting_items=all_items,
            conflict_type="value_mismatch",
            resolution_strategy=new_knowledge.conflict_resolution_strategy
        )
        
        self.active_conflicts[conflict_id] = conflict
        
        # Apply resolution strategy
        if conflict.resolution_strategy == ConflictResolutionStrategy.TIMESTAMP_WINS:
            winner = max(all_items, key=lambda x: x.updated_at)
            await self._resolve_conflict(conflict_id, winner)
        
        elif conflict.resolution_strategy == ConflictResolutionStrategy.AUTHORITY_WINS:
            # Simple authority: owner wins, then by validation count
            winner = max(all_items, key=lambda x: (x.validation_count, x.confidence_score))
            await self._resolve_conflict(conflict_id, winner)
        
        elif conflict.resolution_strategy == ConflictResolutionStrategy.VOTE:
            # Initiate voting process
            await self._initiate_conflict_voting(conflict)
        
        else:
            # Default to timestamp wins
            winner = max(all_items, key=lambda x: x.updated_at)
            await self._resolve_conflict(conflict_id, winner)
    
    async def _initiate_conflict_voting(self, conflict: KnowledgeConflict) -> None:
        """Initiate voting process for conflict resolution."""
        # Get all agents that have access to the conflicting knowledge
        eligible_voters = set()
        for item in conflict.conflicting_items:
            if item.access_level == AccessLevel.PUBLIC:
                # All agents can vote
                all_agents = self.message_router.get_all_agents()
                eligible_voters.update(all_agents.keys())
            else:
                eligible_voters.add(item.owner_agent_id)
                eligible_voters.update(item.authorized_agents)
        
        # Send voting requests
        await self.message_bus.send_notification(
            sender_id="knowledge_base",
            notification_data={
                "event": "conflict_voting",
                "conflict_id": conflict.conflict_id,
                "conflicting_items": [item.dict() for item in conflict.conflicting_items],
                "voting_deadline": (datetime.utcnow() + self.conflict_resolution_timeout).isoformat()
            },
            recipients=list(eligible_voters)
        )
        
        logger.info(f"Initiated voting for conflict {conflict.conflict_id}")
    
    async def vote_on_conflict(self, conflict_id: str, voter_agent_id: str, 
                             chosen_knowledge_id: str) -> bool:
        """Vote on a knowledge conflict."""
        if conflict_id not in self.active_conflicts:
            return False
        
        conflict = self.active_conflicts[conflict_id]
        
        # Validate the chosen knowledge ID
        valid_choice = any(item.knowledge_id == chosen_knowledge_id 
                          for item in conflict.conflicting_items)
        if not valid_choice:
            return False
        
        # Record vote
        conflict.votes[voter_agent_id] = chosen_knowledge_id
        
        # Check if we have enough votes to resolve
        total_eligible = len(set().union(*[
            {item.owner_agent_id} | item.authorized_agents 
            for item in conflict.conflicting_items
        ]))
        
        if len(conflict.votes) >= total_eligible // 2 + 1:  # Majority
            # Count votes and resolve
            vote_counts = defaultdict(int)
            for chosen_id in conflict.votes.values():
                vote_counts[chosen_id] += 1
            
            winner_id = max(vote_counts.keys(), key=lambda x: vote_counts[x])
            winner = next(item for item in conflict.conflicting_items 
                         if item.knowledge_id == winner_id)
            
            await self._resolve_conflict(conflict_id, winner)
        
        return True
    
    async def _resolve_conflict(self, conflict_id: str, winner: KnowledgeItem) -> None:
        """Resolve a knowledge conflict."""
        if conflict_id not in self.active_conflicts:
            return
        
        conflict = self.active_conflicts[conflict_id]
        conflict.resolution = winner
        conflict.resolved_at = datetime.utcnow()
        
        # Store the winning knowledge
        await self._store_in_postgres(winner)
        await self._cache_in_redis(winner)
        self.knowledge_cache[winner.knowledge_id] = winner
        
        # Remove losing knowledge items
        for item in conflict.conflicting_items:
            if item.knowledge_id != winner.knowledge_id:
                await self.delete_knowledge(item.knowledge_id, "system")
        
        # Store conflict resolution in database
        if self.postgres_pool:
            async with self.postgres_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO knowledge_conflicts 
                    (conflict_id, conflicting_items, conflict_type, resolution_strategy, 
                     created_at, resolved_at, resolution, votes)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, 
                conflict.conflict_id,
                json.dumps([item.dict() for item in conflict.conflicting_items]),
                conflict.conflict_type,
                conflict.resolution_strategy.value,
                conflict.created_at,
                conflict.resolved_at,
                json.dumps(conflict.resolution.dict()) if conflict.resolution else None,
                json.dumps(conflict.votes)
                )
        
        # Remove from active conflicts
        del self.active_conflicts[conflict_id]
        self.stats["conflicts_resolved"] += 1
        
        logger.info(f"Conflict resolved: {conflict_id}, winner: {winner.knowledge_id}")
    
    async def _notify_subscribers(self, knowledge: KnowledgeItem, event_type: str, 
                                extra_data: Optional[Dict[str, Any]] = None) -> None:
        """Notify subscribers about knowledge changes."""
        for subscription in self.subscriptions.values():
            if not subscription.active:
                continue
            
            # Check if subscription matches
            if subscription.knowledge_types and knowledge.knowledge_type not in subscription.knowledge_types:
                continue
            
            # Simple pattern matching (could be enhanced with regex)
            if subscription.knowledge_pattern not in knowledge.key:
                continue
            
            # Send notification
            notification_data = {
                "event": f"knowledge_{event_type}",
                "knowledge": knowledge.dict(),
                "subscription_id": subscription.subscription_id
            }
            
            if extra_data:
                notification_data.update(extra_data)
            
            await self.message_bus.send_notification(
                sender_id="knowledge_base",
                notification_data=notification_data,
                recipients=[subscription.agent_id]
            )
    
    async def _store_in_postgres(self, knowledge: KnowledgeItem) -> None:
        """Store knowledge in PostgreSQL."""
        if not self.postgres_pool:
            return
        
        async with self.postgres_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO knowledge_items 
                (knowledge_id, knowledge_type, key, value, metadata, owner_agent_id, 
                 access_level, authorized_agents, version, created_at, updated_at, 
                 expires_at, confidence_score, validation_count, validators, 
                 conflict_resolution_strategy)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                ON CONFLICT (knowledge_id) DO UPDATE SET
                    value = EXCLUDED.value,
                    metadata = EXCLUDED.metadata,
                    version = EXCLUDED.version,
                    updated_at = EXCLUDED.updated_at,
                    confidence_score = EXCLUDED.confidence_score,
                    validation_count = EXCLUDED.validation_count,
                    validators = EXCLUDED.validators
            """,
            knowledge.knowledge_id,
            knowledge.knowledge_type.value,
            knowledge.key,
            json.dumps(knowledge.value),
            json.dumps(knowledge.metadata),
            knowledge.owner_agent_id,
            knowledge.access_level.value,
            json.dumps(list(knowledge.authorized_agents)),
            knowledge.version,
            knowledge.created_at,
            knowledge.updated_at,
            knowledge.expires_at,
            knowledge.confidence_score,
            knowledge.validation_count,
            json.dumps(list(knowledge.validators)),
            knowledge.conflict_resolution_strategy.value
            )
    
    async def _cache_in_redis(self, knowledge: KnowledgeItem) -> None:
        """Cache knowledge in Redis."""
        if not self.redis_client:
            return
        
        key = f"knowledge:{knowledge.knowledge_id}"
        value = json.dumps(knowledge.dict())
        await self.redis_client.setex(key, self.cache_ttl, value)
    
    async def _get_from_postgres(self, knowledge_id: str) -> Optional[KnowledgeItem]:
        """Get knowledge from PostgreSQL."""
        if not self.postgres_pool:
            return None
        
        async with self.postgres_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM knowledge_items WHERE knowledge_id = $1",
                knowledge_id
            )
            
            if row:
                return self._row_to_knowledge_item(row)
        
        return None
    
    def _row_to_knowledge_item(self, row) -> KnowledgeItem:
        """Convert database row to KnowledgeItem."""
        return KnowledgeItem(
            knowledge_id=row['knowledge_id'],
            knowledge_type=KnowledgeType(row['knowledge_type']),
            key=row['key'],
            value=json.loads(row['value']),
            metadata=json.loads(row['metadata']),
            owner_agent_id=row['owner_agent_id'],
            access_level=AccessLevel(row['access_level']),
            authorized_agents=set(json.loads(row['authorized_agents'])),
            version=row['version'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            expires_at=row['expires_at'],
            confidence_score=row['confidence_score'],
            validation_count=row['validation_count'],
            validators=set(json.loads(row['validators'])),
            conflict_resolution_strategy=ConflictResolutionStrategy(row['conflict_resolution_strategy'])
        )
    
    async def _sync_loop(self) -> None:
        """Synchronization loop for cache management and cleanup."""
        while self.is_running:
            try:
                await self._cleanup_expired_knowledge()
                await self._resolve_pending_conflicts()
                await asyncio.sleep(self.knowledge_sync_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in knowledge sync loop: {e}")
                await asyncio.sleep(self.knowledge_sync_interval)
    
    async def _cleanup_expired_knowledge(self) -> None:
        """Clean up expired knowledge items."""
        if not self.postgres_pool:
            return
        
        async with self.postgres_pool.acquire() as conn:
            # Delete expired items
            deleted_rows = await conn.fetch("""
                DELETE FROM knowledge_items 
                WHERE expires_at IS NOT NULL AND expires_at <= NOW()
                RETURNING knowledge_id
            """)
            
            # Remove from caches
            for row in deleted_rows:
                knowledge_id = row['knowledge_id']
                
                # Remove from local cache
                if knowledge_id in self.knowledge_cache:
                    del self.knowledge_cache[knowledge_id]
                
                # Remove from Redis
                if self.redis_client:
                    await self.redis_client.delete(f"knowledge:{knowledge_id}")
            
            if deleted_rows:
                logger.info(f"Cleaned up {len(deleted_rows)} expired knowledge items")
    
    async def _resolve_pending_conflicts(self) -> None:
        """Resolve conflicts that have timed out."""
        current_time = datetime.utcnow()
        conflicts_to_resolve = []
        
        for conflict_id, conflict in self.active_conflicts.items():
            if current_time - conflict.created_at > self.conflict_resolution_timeout:
                conflicts_to_resolve.append(conflict_id)
        
        for conflict_id in conflicts_to_resolve:
            conflict = self.active_conflicts[conflict_id]
            
            if conflict.resolution_strategy == ConflictResolutionStrategy.VOTE:
                # Resolve by current vote count
                if conflict.votes:
                    vote_counts = defaultdict(int)
                    for chosen_id in conflict.votes.values():
                        vote_counts[chosen_id] += 1
                    
                    winner_id = max(vote_counts.keys(), key=lambda x: vote_counts[x])
                    winner = next(item for item in conflict.conflicting_items 
                                 if item.knowledge_id == winner_id)
                else:
                    # No votes, use timestamp
                    winner = max(conflict.conflicting_items, key=lambda x: x.updated_at)
            else:
                # Use timestamp as fallback
                winner = max(conflict.conflicting_items, key=lambda x: x.updated_at)
            
            await self._resolve_conflict(conflict_id, winner)
    
    def get_knowledge_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        return {
            **self.stats,
            "cache_size": len(self.knowledge_cache),
            "active_conflicts": len(self.active_conflicts),
            "active_subscriptions": len([s for s in self.subscriptions.values() if s.active])
        }