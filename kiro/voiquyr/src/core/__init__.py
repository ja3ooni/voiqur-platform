"""
Core Module

Core processing pipeline and system integration components for the EUVoice AI Platform.
"""

from .processing_pipeline import (
    ProcessingPipeline,
    ProcessingRequest,
    ProcessingResult,
    ProcessingContext,
    ProcessingStage,
    ProcessingStatus,
    get_processing_pipeline,
    set_processing_pipeline,
    process_voice
)

from .feature_agents import (
    SpecializedFeatureManager,
    FeatureType,
    FeatureResult,
    FeatureToggleManager,
    EmotionAgent,
    AccentAgent,
    LipSyncAgent,
    ArabicAgent,
    get_feature_manager,
    set_feature_manager
)

from .orchestration import (
    SystemOrchestrator,
    AgentInstance,
    AgentStatus,
    LoadBalancingStrategy,
    HealthChecker,
    LoadBalancer,
    get_system_orchestrator,
    set_system_orchestrator
)

from .e2e_testing import (
    E2ETestingFramework,
    TestScenario,
    TestResult,
    TestSuite,
    TestType,
    TestStatus,
    TestDataGenerator,
    PerformanceBenchmark,
    get_e2e_framework,
    set_e2e_framework
)

__all__ = [
    # Processing Pipeline
    "ProcessingPipeline",
    "ProcessingRequest",
    "ProcessingResult", 
    "ProcessingContext",
    "ProcessingStage",
    "ProcessingStatus",
    "get_processing_pipeline",
    "set_processing_pipeline",
    "process_voice",
    
    # Feature Agents
    "SpecializedFeatureManager",
    "FeatureType",
    "FeatureResult",
    "FeatureToggleManager",
    "EmotionAgent",
    "AccentAgent", 
    "LipSyncAgent",
    "ArabicAgent",
    "get_feature_manager",
    "set_feature_manager",
    
    # Orchestration
    "SystemOrchestrator",
    "AgentInstance",
    "AgentStatus",
    "LoadBalancingStrategy", 
    "HealthChecker",
    "LoadBalancer",
    "get_system_orchestrator",
    "set_system_orchestrator",
    
    # E2E Testing
    "E2ETestingFramework",
    "TestScenario",
    "TestResult",
    "TestSuite",
    "TestType",
    "TestStatus",
    "TestDataGenerator",
    "PerformanceBenchmark",
    "get_e2e_framework",
    "set_e2e_framework"
]