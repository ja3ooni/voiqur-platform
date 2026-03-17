# Shared Knowledge Base System

The Shared Knowledge Base is a core component of the EUVoice AI multi-agent framework that enables distributed knowledge storage, sharing, and conflict resolution between agents.

## Overview

The knowledge base system provides:

- **Distributed Storage**: Uses Redis for caching and PostgreSQL for persistent storage
- **Knowledge Sharing**: Agents can store, retrieve, and search for knowledge items
- **Conflict Resolution**: Automatic resolution of conflicting knowledge using configurable strategies
- **Access Control**: Fine-grained access control with public, private, restricted, and system levels
- **Subscriptions**: Real-time notifications when knowledge is created, updated, or deleted
- **Expiration**: Automatic cleanup of expired knowledge items
- **Validation**: Knowledge validation by multiple agents to increase confidence scores

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Agent A       │    │   Agent B       │    │   Agent C       │
│                 │    │                 │    │                 │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │  Shared Knowledge Base    │
                    │                           │
                    │  ┌─────────────────────┐  │
                    │  │  Message Router     │  │
                    │  └─────────────────────┘  │
                    │                           │
                    │  ┌─────────────────────┐  │
                    │  │  Conflict Resolver  │  │
                    │  └─────────────────────┘  │
                    │                           │
                    │  ┌─────────────────────┐  │
                    │  │  Subscription Mgr   │  │
                    │  └─────────────────────┘  │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │     Storage Layer         │
                    │                           │
                    │  ┌─────────┐ ┌─────────┐  │
                    │  │  Redis  │ │PostgreSQL│ │
                    │  │ (Cache) │ │(Persist)│  │
                    │  └─────────┘ └─────────┘  │
                    └───────────────────────────┘
```

## Knowledge Item Structure

Each knowledge item contains:

```python
class KnowledgeItem:
    knowledge_id: str              # Unique identifier
    knowledge_type: KnowledgeType  # FACT, RULE, PROCEDURE, EXPERIENCE, etc.
    key: str                       # Knowledge key/topic
    value: Any                     # Knowledge content
    metadata: Dict[str, Any]       # Additional metadata
    
    # Ownership and access
    owner_agent_id: str
    access_level: AccessLevel      # PUBLIC, PRIVATE, RESTRICTED, SYSTEM
    authorized_agents: Set[str]
    
    # Versioning
    version: int
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime]
    
    # Validation and trust
    confidence_score: float        # 0.0 to 1.0
    validation_count: int
    validators: Set[str]
    
    # Conflict resolution
    conflict_resolution_strategy: ConflictResolutionStrategy
```

## Knowledge Types

- **FACT**: Factual information (e.g., agent capabilities, performance metrics)
- **RULE**: Business rules or constraints
- **PROCEDURE**: Step-by-step procedures or workflows
- **EXPERIENCE**: Learning from past experiences
- **CONFIGURATION**: System configuration data
- **TEMPORARY**: Short-lived session data

## Access Levels

- **PUBLIC**: Accessible by all agents
- **RESTRICTED**: Accessible by owner and authorized agents only
- **PRIVATE**: Accessible by owner only
- **SYSTEM**: System-level access only

## Conflict Resolution Strategies

When multiple agents store different values for the same knowledge key:

- **TIMESTAMP_WINS**: Most recently updated knowledge wins
- **AUTHORITY_WINS**: Knowledge with highest validation count/confidence wins
- **MERGE**: Attempt to merge conflicting values (implementation-specific)
- **VOTE**: Initiate voting process among eligible agents
- **MANUAL**: Require manual resolution

## Usage Examples

### Basic Knowledge Storage and Retrieval

```python
from src.core import SharedKnowledgeBase, KnowledgeItem, KnowledgeType, AccessLevel

# Initialize knowledge base
knowledge_base = SharedKnowledgeBase(message_router)
await knowledge_base.start()

# Store knowledge
knowledge = KnowledgeItem(
    knowledge_id="agent_capability_stt",
    knowledge_type=KnowledgeType.FACT,
    key="stt_performance",
    value={"accuracy": 0.95, "latency_ms": 120},
    owner_agent_id="stt_agent_1",
    access_level=AccessLevel.PUBLIC
)

await knowledge_base.store_knowledge(knowledge)

# Retrieve knowledge
retrieved = await knowledge_base.get_knowledge("agent_capability_stt", "requesting_agent")
```

### Knowledge Search

```python
# Search for knowledge by content
results = await knowledge_base.search_knowledge(
    query="accuracy",
    knowledge_types=[KnowledgeType.FACT],
    requester_agent_id="search_agent"
)

for item in results:
    print(f"Found: {item.key} = {item.value}")
```

### Knowledge Subscriptions

```python
from src.core import KnowledgeSubscription

# Subscribe to knowledge updates
subscription = KnowledgeSubscription(
    subscription_id="agent_performance_updates",
    agent_id="monitoring_agent",
    knowledge_pattern="performance",
    knowledge_types={KnowledgeType.FACT}
)

await knowledge_base.subscribe_to_knowledge(subscription)
```

### Knowledge Validation

```python
# Validate knowledge to increase confidence
await knowledge_base.validate_knowledge("agent_capability_stt", "validator_agent")

# Check updated confidence score
validated = await knowledge_base.get_knowledge("agent_capability_stt", "any_agent")
print(f"Confidence: {validated.confidence_score}")
```

## Configuration

### Database Configuration

```python
# Redis configuration
redis_url = "redis://localhost:6379"

# PostgreSQL configuration  
postgres_url = "postgresql://username:password@localhost:5432/euvoice"

# Initialize with custom configuration
knowledge_base = SharedKnowledgeBase(
    message_router=message_router,
    redis_url=redis_url,
    postgres_url=postgres_url
)
```

### Performance Tuning

```python
# Adjust cache TTL
knowledge_base.cache_ttl = 600  # 10 minutes

# Adjust sync interval
knowledge_base.knowledge_sync_interval = 60.0  # 60 seconds

# Adjust conflict resolution timeout
knowledge_base.conflict_resolution_timeout = timedelta(minutes=15)
```

## Database Schema

### PostgreSQL Tables

#### knowledge_items
```sql
CREATE TABLE knowledge_items (
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
);
```

#### knowledge_conflicts
```sql
CREATE TABLE knowledge_conflicts (
    conflict_id VARCHAR(255) PRIMARY KEY,
    conflicting_items JSONB NOT NULL,
    conflict_type VARCHAR(100) NOT NULL,
    resolution_strategy VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP NULL,
    resolution JSONB NULL,
    votes JSONB DEFAULT '{}'
);
```

### Redis Keys

- `knowledge:{knowledge_id}`: Cached knowledge items
- `knowledge_stats`: System statistics
- `agent_subscriptions:{agent_id}`: Agent subscription data

## Monitoring and Statistics

```python
# Get knowledge base statistics
stats = knowledge_base.get_knowledge_stats()
print(f"Total knowledge items: {stats['total_knowledge_items']}")
print(f"Cache hits: {stats['cache_hits']}")
print(f"Cache misses: {stats['cache_misses']}")
print(f"Active conflicts: {stats['active_conflicts']}")
print(f"Active subscriptions: {stats['active_subscriptions']}")
```

## Error Handling

The knowledge base handles various error scenarios:

- **Database Connection Failures**: Graceful degradation with local caching
- **Conflict Resolution Timeouts**: Automatic fallback to timestamp-based resolution
- **Invalid Access Attempts**: Proper access control enforcement
- **Expired Knowledge**: Automatic cleanup and cache invalidation

## Best Practices

1. **Use Appropriate Knowledge Types**: Choose the right type for your data
2. **Set Proper Access Levels**: Use least-privilege principle
3. **Include Expiration for Temporary Data**: Prevent storage bloat
4. **Validate Important Knowledge**: Increase confidence through validation
5. **Use Descriptive Keys**: Make knowledge discoverable through search
6. **Handle Conflicts Proactively**: Choose appropriate resolution strategies
7. **Monitor Performance**: Track cache hit rates and query performance

## Integration with Multi-Agent Framework

The knowledge base integrates seamlessly with other framework components:

- **Message Router**: For inter-agent communication about knowledge updates
- **Service Registry**: For discovering agents capable of validating knowledge
- **Quality Monitor**: For tracking knowledge base performance metrics
- **Coordination Controller**: For coordinating knowledge-dependent workflows

## Security Considerations

- **Access Control**: Enforced at the knowledge item level
- **Data Encryption**: Sensitive data should be encrypted before storage
- **Audit Logging**: All knowledge operations are logged for compliance
- **Input Validation**: All knowledge items are validated before storage
- **Rate Limiting**: Prevents abuse of knowledge base operations

## Troubleshooting

### Common Issues

1. **Connection Errors**: Check Redis and PostgreSQL connectivity
2. **Permission Denied**: Verify agent access levels and authorization
3. **Conflict Resolution Stuck**: Check voting timeouts and eligible voters
4. **High Memory Usage**: Monitor cache size and implement cleanup policies
5. **Slow Queries**: Add appropriate database indexes and optimize search patterns

### Debug Mode

Enable debug logging for detailed operation traces:

```python
import logging
logging.getLogger('src.core.knowledge_base').setLevel(logging.DEBUG)
```

## Future Enhancements

- **Distributed Consensus**: Implement Raft or similar for multi-node deployments
- **Advanced Search**: Full-text search with Elasticsearch integration
- **Knowledge Graphs**: Support for relationship-based knowledge representation
- **Machine Learning Integration**: Automatic knowledge extraction and validation
- **Blockchain Integration**: Immutable knowledge audit trails