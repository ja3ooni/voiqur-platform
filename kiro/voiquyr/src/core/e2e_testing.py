"""
End-to-End Testing Framework

Comprehensive testing framework for the complete voice processing pipeline
with performance benchmarking, regression testing, and multi-language scenarios.
"""

import asyncio
import logging
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import statistics

logger = logging.getLogger(__name__)


class TestType(str, Enum):
    """Types of end-to-end tests."""
    FUNCTIONAL = "functional"
    PERFORMANCE = "performance"
    LOAD = "load"
    STRESS = "stress"
    REGRESSION = "regression"
    MULTI_LANGUAGE = "multi_language"
    CONVERSATION = "conversation"
    ERROR_HANDLING = "error_handling"


class TestStatus(str, Enum):
    """Test execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


@dataclass
class TestScenario:
    """Defines a test scenario."""
    scenario_id: str
    name: str
    description: str
    test_type: TestType
    input_data: Dict[str, Any]
    expected_output: Dict[str, Any]
    performance_thresholds: Dict[str, float]
    timeout_seconds: int = 30
    retry_count: int = 0
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class TestResult:
    """Test execution result."""
    scenario_id: str
    status: TestStatus
    execution_time_ms: float
    start_time: datetime
    end_time: datetime
    actual_output: Dict[str, Any]
    performance_metrics: Dict[str, float]
    error_message: Optional[str] = None
    validation_results: Dict[str, bool] = None
    
    def __post_init__(self):
        if self.validation_results is None:
            self.validation_results = {}


@dataclass
class TestSuite:
    """Collection of test scenarios."""
    suite_id: str
    name: str
    description: str
    scenarios: List[TestScenario]
    setup_hooks: List[Callable] = None
    teardown_hooks: List[Callable] = None
    
    def __post_init__(self):
        if self.setup_hooks is None:
            self.setup_hooks = []
        if self.teardown_hooks is None:
            self.teardown_hooks = []


class TestDataGenerator:
    """Generates test data for various scenarios."""
    
    def __init__(self):
        """Initialize test data generator."""
        self.languages = ["en", "es", "fr", "de", "ar", "zh", "ja"]
        self.accents = ["american", "british", "australian", "neutral"]
        self.emotions = ["happy", "sad", "angry", "neutral", "excited"]
        
    def generate_audio_test_data(self, language: str = "en", duration_ms: int = 3000) -> bytes:
        """Generate mock audio test data."""
        # Create mock audio data based on parameters
        base_data = f"MOCK_AUDIO_{language}_{duration_ms}ms".encode()
        padding_size = max(0, duration_ms - len(base_data))
        return base_data + b"0" * padding_size
    
    def generate_text_samples(self, language: str = "en", count: int = 10) -> List[str]:
        """Generate text samples for testing."""
        samples = {
            "en": [
                "Hello, how are you today?",
                "What's the weather like?",
                "Can you help me with this problem?",
                "I need assistance with my account.",
                "Thank you for your help.",
                "Good morning, I have a question.",
                "Could you please explain this to me?",
                "I'm looking for information about your services.",
                "How do I reset my password?",
                "What are your business hours?"
            ],
            "es": [
                "Hola, ¿cómo estás hoy?",
                "¿Cómo está el clima?",
                "¿Puedes ayudarme con este problema?",
                "Necesito ayuda con mi cuenta.",
                "Gracias por tu ayuda."
            ],
            "fr": [
                "Bonjour, comment allez-vous aujourd'hui?",
                "Quel temps fait-il?",
                "Pouvez-vous m'aider avec ce problème?",
                "J'ai besoin d'aide avec mon compte.",
                "Merci pour votre aide."
            ],
            "ar": [
                "مرحبا، كيف حالك اليوم؟",
                "كيف الطقس؟",
                "هل يمكنك مساعدتي في هذه المشكلة؟",
                "أحتاج مساعدة في حسابي.",
                "شكرا لمساعدتك."
            ]
        }
        
        language_samples = samples.get(language, samples["en"])
        return language_samples[:count] if count <= len(language_samples) else language_samples * ((count // len(language_samples)) + 1)
    
    def generate_conversation_scenarios(self) -> List[Dict[str, Any]]:
        """Generate multi-turn conversation scenarios."""
        return [
            {
                "scenario": "customer_support",
                "turns": [
                    {"user": "Hello, I need help with my order", "expected_topics": ["support", "order"]},
                    {"user": "My order number is 12345", "expected_topics": ["order_lookup"]},
                    {"user": "When will it be delivered?", "expected_topics": ["delivery", "timeline"]},
                    {"user": "Thank you for the information", "expected_topics": ["gratitude", "closing"]}
                ]
            },
            {
                "scenario": "information_request",
                "turns": [
                    {"user": "What are your business hours?", "expected_topics": ["hours", "information"]},
                    {"user": "Are you open on weekends?", "expected_topics": ["weekend", "schedule"]},
                    {"user": "How can I contact you?", "expected_topics": ["contact", "communication"]}
                ]
            },
            {
                "scenario": "technical_support",
                "turns": [
                    {"user": "I'm having trouble logging in", "expected_topics": ["login", "technical"]},
                    {"user": "I forgot my password", "expected_topics": ["password", "reset"]},
                    {"user": "Can you send me a reset link?", "expected_topics": ["reset_link", "email"]}
                ]
            }
        ]


class PerformanceBenchmark:
    """Performance benchmarking system."""
    
    def __init__(self):
        """Initialize performance benchmark."""
        self.baseline_metrics: Dict[str, Dict[str, float]] = {}
        self.benchmark_history: List[Dict[str, Any]] = []
        
    def set_baseline(self, test_type: str, metrics: Dict[str, float]) -> None:
        """Set baseline performance metrics."""
        self.baseline_metrics[test_type] = metrics.copy()
        logger.info(f"Baseline set for {test_type}: {metrics}")
    
    def compare_to_baseline(self, test_type: str, current_metrics: Dict[str, float]) -> Dict[str, Any]:
        """Compare current metrics to baseline."""
        if test_type not in self.baseline_metrics:
            return {"status": "no_baseline", "message": "No baseline available for comparison"}
        
        baseline = self.baseline_metrics[test_type]
        comparison = {}
        
        for metric, current_value in current_metrics.items():
            if metric in baseline:
                baseline_value = baseline[metric]
                percentage_change = ((current_value - baseline_value) / baseline_value) * 100
                
                comparison[metric] = {
                    "current": current_value,
                    "baseline": baseline_value,
                    "change_percent": percentage_change,
                    "status": "improved" if percentage_change < -5 else "degraded" if percentage_change > 5 else "stable"
                }
        
        return {
            "status": "compared",
            "comparison": comparison,
            "overall_status": self._calculate_overall_status(comparison)
        }
    
    def _calculate_overall_status(self, comparison: Dict[str, Dict[str, Any]]) -> str:
        """Calculate overall performance status."""
        statuses = [metric_data["status"] for metric_data in comparison.values()]
        
        if "degraded" in statuses:
            return "degraded"
        elif "improved" in statuses:
            return "improved"
        else:
            return "stable"


class E2ETestingFramework:
    """Comprehensive end-to-end testing framework."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize E2E testing framework."""
        self.config = config or {}
        
        # Components
        self.test_data_generator = TestDataGenerator()
        self.performance_benchmark = PerformanceBenchmark()
        
        # Test execution state
        self.test_suites: Dict[str, TestSuite] = {}
        self.test_results: Dict[str, List[TestResult]] = {}
        
        # Performance tracking
        self.execution_metrics: Dict[str, List[float]] = {}
        
        logger.info("E2E Testing Framework initialized")
    
    def register_test_suite(self, test_suite: TestSuite) -> None:
        """Register a test suite."""
        self.test_suites[test_suite.suite_id] = test_suite
        logger.info(f"Test suite registered: {test_suite.name}")
    
    async def run_test_suite(
        self,
        suite_id: str,
        parallel_execution: bool = False,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Run a complete test suite."""
        if suite_id not in self.test_suites:
            raise ValueError(f"Test suite not found: {suite_id}")
        
        test_suite = self.test_suites[suite_id]
        logger.info(f"Starting test suite: {test_suite.name}")
        
        start_time = datetime.utcnow()
        suite_results = []
        
        try:
            # Run setup hooks
            for setup_hook in test_suite.setup_hooks:
                await setup_hook()
            
            # Execute test scenarios
            if parallel_execution:
                # Run scenarios in parallel
                tasks = [
                    self._execute_scenario(scenario, progress_callback)
                    for scenario in test_suite.scenarios
                ]
                suite_results = await asyncio.gather(*tasks, return_exceptions=True)
            else:
                # Run scenarios sequentially
                for i, scenario in enumerate(test_suite.scenarios):
                    result = await self._execute_scenario(scenario, progress_callback)
                    suite_results.append(result)
                    
                    if progress_callback:
                        progress = (i + 1) / len(test_suite.scenarios)
                        await progress_callback(f"Completed {i+1}/{len(test_suite.scenarios)} scenarios", progress)
            
            # Run teardown hooks
            for teardown_hook in test_suite.teardown_hooks:
                await teardown_hook()
            
        except Exception as e:
            logger.error(f"Test suite execution failed: {e}")
            raise
        
        end_time = datetime.utcnow()
        execution_time = (end_time - start_time).total_seconds()
        
        # Process results
        valid_results = [r for r in suite_results if isinstance(r, TestResult)]
        
        # Store results
        self.test_results[suite_id] = valid_results
        
        # Generate suite summary
        summary = self._generate_suite_summary(test_suite, valid_results, execution_time)
        
        logger.info(f"Test suite completed: {test_suite.name} - {summary['status']}")
        return summary
    
    async def _execute_scenario(
        self,
        scenario: TestScenario,
        progress_callback: Optional[Callable] = None
    ) -> TestResult:
        """Execute a single test scenario."""
        logger.debug(f"Executing scenario: {scenario.name}")
        
        start_time = datetime.utcnow()
        
        try:
            # Import here to avoid circular imports
            from .processing_pipeline import process_voice
            
            # Prepare input data
            input_data = scenario.input_data.copy()
            
            # Execute the voice processing pipeline
            processing_start = time.time()
            
            if "audio_data" in input_data:
                result = await process_voice(
                    audio_data=input_data["audio_data"],
                    session_id=input_data.get("session_id", f"test_{scenario.scenario_id}"),
                    language=input_data.get("language", "en"),
                    accent=input_data.get("accent"),
                    emotion_context=input_data.get("emotion_context"),
                    user_preferences=input_data.get("user_preferences", {})
                )
            else:
                result = await process_voice(
                    text_input=input_data.get("text_input", "Hello"),
                    session_id=input_data.get("session_id", f"test_{scenario.scenario_id}"),
                    language=input_data.get("language", "en"),
                    accent=input_data.get("accent"),
                    emotion_context=input_data.get("emotion_context"),
                    user_preferences=input_data.get("user_preferences", {})
                )
            
            processing_time = (time.time() - processing_start) * 1000
            
            # Validate results
            validation_results = self._validate_scenario_output(scenario, result)
            
            # Check performance thresholds
            performance_metrics = {
                "total_processing_time_ms": processing_time,
                "stt_time_ms": result.stage_timings.get("stt", 0),
                "llm_time_ms": result.stage_timings.get("llm", 0),
                "tts_time_ms": result.stage_timings.get("tts", 0),
                "stt_confidence": result.confidence_scores.get("stt", 0),
                "llm_confidence": result.confidence_scores.get("llm", 0),
                "tts_confidence": result.confidence_scores.get("tts", 0)
            }
            
            # Determine test status
            status = TestStatus.PASSED
            error_message = None
            
            # Check if processing failed
            if result.status.value != "completed":
                status = TestStatus.FAILED
                error_message = result.error_message or "Processing failed"
            
            # Check validation results
            elif not all(validation_results.values()):
                status = TestStatus.FAILED
                failed_validations = [k for k, v in validation_results.items() if not v]
                error_message = f"Validation failed: {', '.join(failed_validations)}"
            
            # Check performance thresholds
            elif not self._check_performance_thresholds(scenario, performance_metrics):
                status = TestStatus.FAILED
                error_message = "Performance thresholds not met"
            
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            test_result = TestResult(
                scenario_id=scenario.scenario_id,
                status=status,
                execution_time_ms=execution_time,
                start_time=start_time,
                end_time=end_time,
                actual_output=result.to_dict(),
                performance_metrics=performance_metrics,
                error_message=error_message,
                validation_results=validation_results
            )
            
            return test_result
            
        except asyncio.TimeoutError:
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            return TestResult(
                scenario_id=scenario.scenario_id,
                status=TestStatus.TIMEOUT,
                execution_time_ms=execution_time,
                start_time=start_time,
                end_time=end_time,
                actual_output={},
                performance_metrics={},
                error_message=f"Test timed out after {scenario.timeout_seconds} seconds"
            )
            
        except Exception as e:
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            return TestResult(
                scenario_id=scenario.scenario_id,
                status=TestStatus.FAILED,
                execution_time_ms=execution_time,
                start_time=start_time,
                end_time=end_time,
                actual_output={},
                performance_metrics={},
                error_message=str(e)
            )
    
    def _validate_scenario_output(self, scenario: TestScenario, result: Any) -> Dict[str, bool]:
        """Validate scenario output against expected results."""
        validation_results = {}
        expected = scenario.expected_output
        
        # Validate basic completion
        validation_results["completed"] = result.status.value == "completed"
        
        # Validate output presence
        if "transcribed_text" in expected:
            validation_results["has_transcription"] = bool(result.transcribed_text)
            
            # Check if transcription contains expected keywords
            if expected["transcribed_text"] and result.transcribed_text:
                expected_keywords = expected["transcribed_text"].lower().split()
                actual_text = result.transcribed_text.lower()
                validation_results["transcription_keywords"] = any(
                    keyword in actual_text for keyword in expected_keywords
                )
        
        if "generated_response" in expected:
            validation_results["has_response"] = bool(result.generated_response)
        
        if "synthesized_audio" in expected:
            validation_results["has_audio"] = result.synthesized_audio is not None
        
        # Validate confidence scores
        if "min_confidence" in expected:
            min_confidence = expected["min_confidence"]
            avg_confidence = statistics.mean([
                score for score in result.confidence_scores.values() if score > 0
            ]) if result.confidence_scores else 0
            validation_results["confidence_threshold"] = avg_confidence >= min_confidence
        
        return validation_results
    
    def _check_performance_thresholds(
        self,
        scenario: TestScenario,
        metrics: Dict[str, float]
    ) -> bool:
        """Check if performance metrics meet thresholds."""
        thresholds = scenario.performance_thresholds
        
        for metric, threshold in thresholds.items():
            if metric in metrics:
                if metrics[metric] > threshold:
                    return False
        
        return True
    
    def _generate_suite_summary(
        self,
        test_suite: TestSuite,
        results: List[TestResult],
        execution_time: float
    ) -> Dict[str, Any]:
        """Generate test suite summary."""
        if not results:
            return {
                "suite_id": test_suite.suite_id,
                "suite_name": test_suite.name,
                "status": "no_results",
                "execution_time_seconds": execution_time
            }
        
        # Count results by status
        status_counts = {}
        for status in TestStatus:
            status_counts[status.value] = len([r for r in results if r.status == status])
        
        # Calculate performance statistics
        execution_times = [r.execution_time_ms for r in results if r.execution_time_ms > 0]
        performance_stats = {}
        
        if execution_times:
            performance_stats = {
                "avg_execution_time_ms": statistics.mean(execution_times),
                "min_execution_time_ms": min(execution_times),
                "max_execution_time_ms": max(execution_times),
                "median_execution_time_ms": statistics.median(execution_times)
            }
        
        # Determine overall status
        if status_counts.get("failed", 0) > 0 or status_counts.get("timeout", 0) > 0:
            overall_status = "failed"
        elif status_counts.get("passed", 0) == len(results):
            overall_status = "passed"
        else:
            overall_status = "partial"
        
        return {
            "suite_id": test_suite.suite_id,
            "suite_name": test_suite.name,
            "status": overall_status,
            "execution_time_seconds": execution_time,
            "total_scenarios": len(test_suite.scenarios),
            "results_count": len(results),
            "status_breakdown": status_counts,
            "performance_stats": performance_stats,
            "success_rate": (status_counts.get("passed", 0) / len(results) * 100) if results else 0
        }
    
    def create_default_test_suites(self) -> None:
        """Create default test suites for common scenarios."""
        # Functional test suite
        functional_scenarios = []
        
        # Basic voice processing
        for i, text in enumerate(self.test_data_generator.generate_text_samples("en", 5)):
            audio_data = self.test_data_generator.generate_audio_test_data("en", 3000)
            
            scenario = TestScenario(
                scenario_id=f"functional_basic_{i+1}",
                name=f"Basic Voice Processing {i+1}",
                description=f"Test basic voice processing with: {text}",
                test_type=TestType.FUNCTIONAL,
                input_data={"audio_data": audio_data},
                expected_output={
                    "transcribed_text": text.split()[:3],  # First 3 words
                    "generated_response": True,
                    "synthesized_audio": True,
                    "min_confidence": 0.7
                },
                performance_thresholds={
                    "total_processing_time_ms": 2000,
                    "stt_time_ms": 500,
                    "llm_time_ms": 1000,
                    "tts_time_ms": 500
                }
            )
            functional_scenarios.append(scenario)
        
        functional_suite = TestSuite(
            suite_id="functional_basic",
            name="Basic Functional Tests",
            description="Basic voice processing functionality tests",
            scenarios=functional_scenarios
        )
        
        # Multi-language test suite
        multilang_scenarios = []
        
        for lang in ["en", "es", "fr", "ar"]:
            texts = self.test_data_generator.generate_text_samples(lang, 2)
            
            for i, text in enumerate(texts):
                audio_data = self.test_data_generator.generate_audio_test_data(lang, 2500)
                
                scenario = TestScenario(
                    scenario_id=f"multilang_{lang}_{i+1}",
                    name=f"Multi-language Test - {lang.upper()} {i+1}",
                    description=f"Test {lang} language processing",
                    test_type=TestType.MULTI_LANGUAGE,
                    input_data={
                        "audio_data": audio_data,
                        "language": lang
                    },
                    expected_output={
                        "transcribed_text": True,
                        "generated_response": True,
                        "synthesized_audio": True,
                        "min_confidence": 0.6  # Lower threshold for non-English
                    },
                    performance_thresholds={
                        "total_processing_time_ms": 3000
                    },
                    tags=[lang, "multilingual"]
                )
                multilang_scenarios.append(scenario)
        
        multilang_suite = TestSuite(
            suite_id="multilingual",
            name="Multi-language Tests",
            description="Multi-language voice processing tests",
            scenarios=multilang_scenarios
        )
        
        # Performance test suite
        performance_scenarios = []
        
        # Load testing scenarios
        for i in range(10):
            audio_data = self.test_data_generator.generate_audio_test_data("en", 5000)
            
            scenario = TestScenario(
                scenario_id=f"performance_load_{i+1}",
                name=f"Load Test {i+1}",
                description="Performance under load testing",
                test_type=TestType.LOAD,
                input_data={"audio_data": audio_data},
                expected_output={
                    "transcribed_text": True,
                    "generated_response": True,
                    "synthesized_audio": True
                },
                performance_thresholds={
                    "total_processing_time_ms": 1500,  # Stricter for performance tests
                    "stt_time_ms": 300,
                    "llm_time_ms": 800,
                    "tts_time_ms": 400
                },
                tags=["performance", "load"]
            )
            performance_scenarios.append(scenario)
        
        performance_suite = TestSuite(
            suite_id="performance_load",
            name="Performance Load Tests",
            description="Performance and load testing scenarios",
            scenarios=performance_scenarios
        )
        
        # Register all suites
        self.register_test_suite(functional_suite)
        self.register_test_suite(multilang_suite)
        self.register_test_suite(performance_suite)
        
        logger.info("Default test suites created and registered")
    
    def get_test_results(self, suite_id: Optional[str] = None) -> Dict[str, Any]:
        """Get test results for a suite or all suites."""
        if suite_id:
            return {
                "suite_id": suite_id,
                "results": [asdict(result) for result in self.test_results.get(suite_id, [])]
            }
        else:
            return {
                suite_id: [asdict(result) for result in results]
                for suite_id, results in self.test_results.items()
            }


# Global testing framework instance
_e2e_framework: Optional[E2ETestingFramework] = None


def get_e2e_framework() -> E2ETestingFramework:
    """Get the global E2E testing framework instance."""
    global _e2e_framework
    if _e2e_framework is None:
        _e2e_framework = E2ETestingFramework()
    return _e2e_framework


def set_e2e_framework(framework: E2ETestingFramework) -> None:
    """Set the global E2E testing framework instance."""
    global _e2e_framework
    _e2e_framework = framework