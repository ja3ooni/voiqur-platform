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

from .edge_orchestrator import (
    EdgeOrchestrator,
    Jurisdiction,
    RegionalEndpoint,
    RoutingRule,
    CallContext,
    get_edge_orchestrator,
    set_edge_orchestrator
)

from .semantic_vad import (
    SemanticVAD,
    AudioFrame,
    VADResult,
    VADMode,
    get_semantic_vad,
    set_semantic_vad
)

from .flash_mode import (
    FlashMode,
    SpeculativeInferenceState,
    FlashModeResult,
    SpeculativeStatus,
    get_flash_mode,
    set_flash_mode
)

from .code_switch_handler import (
    CodeSwitchHandler,
    Language,
    LanguageSegment,
    CodeSwitchTranscript,
    ResponseLanguageConfig,
    get_code_switch_handler,
    set_code_switch_handler
)

from .compliance_layer import (
    ComplianceLayer,
    ComplianceJurisdiction,
    ComplianceRecord,
    ErasureRequest,
    ComplianceSummaryReport,
    ComplianceAlert,
    AlertSeverity,
    GDPRRuleSet,
    UAEPDPLRuleSet,
    INDIADPDPRuleSet,
    PDPARuleSet,
    get_compliance_layer,
    set_compliance_layer
)

from .latency_validator import (
    LatencyValidator,
    Region,
    Component,
    LatencyMeasurement,
    RegionLatencyReport,
    DeploymentGateResult,
    get_latency_validator,
    set_latency_validator
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
    "set_e2e_framework",
    
    # Edge Orchestrator
    "EdgeOrchestrator",
    "Jurisdiction",
    "RegionalEndpoint",
    "RoutingRule",
    "CallContext",
    "get_edge_orchestrator",
    "set_edge_orchestrator",
    # Semantic VAD
    "SemanticVAD",
    "AudioFrame",
    "VADResult",
    "VADMode",
    "get_semantic_vad",
    "set_semantic_vad",
    # Flash Mode
    "FlashMode",
    "SpeculativeInferenceState",
    "FlashModeResult",
    "SpeculativeStatus",
    "get_flash_mode",
    "set_flash_mode",
    # Code Switch Handler
    "CodeSwitchHandler",
    "Language",
    "LanguageSegment",
    "CodeSwitchTranscript",
    "ResponseLanguageConfig",
    "get_code_switch_handler",
    "set_code_switch_handler",
    # Compliance Layer
    "ComplianceLayer",
    "ComplianceJurisdiction",
    "ComplianceRecord",
    "ErasureRequest",
    "ComplianceSummaryReport",
    "ComplianceAlert",
    "AlertSeverity",
    "GDPRRuleSet",
    "UAEPDPLRuleSet",
    "INDIADPDPRuleSet",
    "PDPARuleSet",
    "get_compliance_layer",
    "set_compliance_layer",
    # Latency Validator
    "LatencyValidator",
    "Region",
    "Component",
    "LatencyMeasurement",
    "RegionLatencyReport",
    "DeploymentGateResult",
    "get_latency_validator",
    "set_latency_validator",
]