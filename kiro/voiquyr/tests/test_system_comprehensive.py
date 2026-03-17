#!/usr/bin/env python3
"""
Comprehensive System Tests

Complete system tests for voice assistant conversations, performance under load,
and failure scenarios with recovery mechanisms.
"""

import asyncio
import sys
import logging
from pathlib import Path
from datetime import datetime
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core import (
    ProcessingPipeline, process_voice, get_processing_pipeline
)
from core.feature_agents import (
    SpecializedFeatureManager, FeatureType, get_feature_manager
)
from core.orchestration import (
    SystemOrchestrator, get_system_orchestrator
)
from core.e2e_testing import (
    E2ETestingFramework, TestType, get_e2e_framework
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_complete_voice_conversations():
    """Test complete voice assistant conversations."""
    logger.info("Testing complete voice assistant conversations...")
    
    # Initialize systems
    pipeline = ProcessingPipeline()
    feature_manager = SpecializedFeatureManager()
    
    conversation_scenarios = [
        {
            "name": "Customer Support Conversation",
            "turns": [
                "Hello, I need help with my order",
                "My order number is ABC123",
                "When will it be delivered?",
                "Thank you for your help"
            ]
        },
        {
            "name": "Information Request Conversation", 
            "turns": [
                "What are your business hours?",
                "Are you open on weekends?",
                "How can I contact support?"
            ]
        },
        {
            "name": "Technical Support Conversation",
            "turns": [
                "I'm having trouble logging in",
                "I forgot my password",
                "Can you send me a reset link?",
                "Yes, my email is user@example.com"
            ]
        }
    ]
    
    results = []
    
    for scenario in conversation_scenarios:
        logger.info(f"Testing scenario: {scenario['name']}")
        
        session_id = f"conv_test_{len(results)}"
        conversation_results = []
        
        for turn_num, user_input in enumerate(scenario['turns']):
            # Process each turn
            result = await process_voice(
                text_input=user_input,
                session_id=session_id,
                user_id="test_user",
                language="en",
                conversation_history=conversation_results[-1].context.conversation_history if conversation_results else []
            )
            
            conversation_results.append(result)
            
            # Validate turn result
            turn_success = (
                result.status.value == "completed" and
                result.transcribed_text and
                result.generated_response and
                result.synthesized_audio is not None
            )
            
            logger.info(f"Turn {turn_num + 1}: {'✅' if turn_success else '❌'}")
            logger.info(f"  User: {result.transcribed_text}")
            logger.info(f"  Assistant: {result.generated_response}")
            logger.info(f"  Processing Time: {result.processing_time_ms:.1f}ms")
        
        # Evaluate conversation quality
        conversation_success = all(
            r.status.value == "completed" for r in conversation_results
        )
        
        avg_processing_time = sum(r.processing_time_ms for r in conversation_results) / len(conversation_results)
        
        scenario_result = {
            "scenario": scenario['name'],
            "success": conversation_success,
            "turns": len(conversation_results),
            "avg_processing_time_ms": avg_processing_time,
            "conversation_length": len(conversation_results[-1].context.conversation_history) if conversation_results else 0
        }
        
        results.append(scenario_result)
    
    print("\\n" + "="*60)
    print("VOICE CONVERSATION TESTS")
    print("="*60)
    
    for result in results:
        status = "✅ PASSED" if result["success"] else "❌ FAILED"
        print(f"{result['scenario']}: {status}")
        print(f"  Turns: {result['turns']}")
        print(f"  Avg Processing Time: {result['avg_processing_time_ms']:.1f}ms")
        print(f"  Conversation History: {result['conversation_length']} exchanges")
    
    return results


async def test_system_performance_under_load():
    """Test system performance under load."""
    logger.info("Testing system performance under load...")
    
    # Initialize orchestrator for load balancing
    orchestrator = SystemOrchestrator()
    await orchestrator.start_orchestration()
    
    try:
        # Test parameters
        concurrent_requests = 20
        requests_per_batch = 5
        
        performance_results = []
        
        # Run multiple batches of concurrent requests
        for batch in range(4):
            logger.info(f"Running load test batch {batch + 1}/4...")
            
            # Create concurrent requests
            tasks = []
            for i in range(requests_per_batch):
                task = process_voice(
                    text_input=f"Load test request {batch * requests_per_batch + i + 1}",
                    session_id=f"load_test_{batch}_{i}",
                    user_id=f"load_user_{i}",
                    language="en"
                )
                tasks.append(task)
            
            # Execute batch concurrently
            batch_start = asyncio.get_event_loop().time()
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            batch_duration = (asyncio.get_event_loop().time() - batch_start) * 1000
            
            # Analyze batch results
            successful_results = [r for r in batch_results if not isinstance(r, Exception)]
            failed_results = [r for r in batch_results if isinstance(r, Exception)]
            
            if successful_results:
                avg_processing_time = sum(r.processing_time_ms for r in successful_results) / len(successful_results)
                max_processing_time = max(r.processing_time_ms for r in successful_results)
                min_processing_time = min(r.processing_time_ms for r in successful_results)
            else:
                avg_processing_time = max_processing_time = min_processing_time = 0
            
            batch_result = {
                "batch": batch + 1,
                "concurrent_requests": requests_per_batch,
                "successful": len(successful_results),
                "failed": len(failed_results),
                "batch_duration_ms": batch_duration,
                "avg_processing_time_ms": avg_processing_time,
                "min_processing_time_ms": min_processing_time,
                "max_processing_time_ms": max_processing_time,
                "throughput_rps": len(successful_results) / (batch_duration / 1000) if batch_duration > 0 else 0
            }
            
            performance_results.append(batch_result)
            
            # Brief pause between batches
            await asyncio.sleep(0.5)
        
        # Get orchestration status
        orchestration_status = orchestrator.get_orchestration_status()
        
        print("\\n" + "="*60)
        print("PERFORMANCE UNDER LOAD TESTS")
        print("="*60)
        
        total_requests = sum(r["successful"] + r["failed"] for r in performance_results)
        total_successful = sum(r["successful"] for r in performance_results)
        success_rate = (total_successful / total_requests * 100) if total_requests > 0 else 0
        
        print(f"Total Requests: {total_requests}")
        print(f"Successful: {total_successful}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        if performance_results:
            avg_throughput = sum(r["throughput_rps"] for r in performance_results) / len(performance_results)
            avg_processing_time = sum(r["avg_processing_time_ms"] for r in performance_results) / len(performance_results)
            
            print(f"Average Throughput: {avg_throughput:.1f} RPS")
            print(f"Average Processing Time: {avg_processing_time:.1f}ms")
        
        print(f"\\nOrchestration Status:")
        print(f"  Total Agents: {orchestration_status['total_agents']}")
        print(f"  Healthy Agents: {orchestration_status['agent_status_counts'].get('healthy', 0)}")
        print(f"  Load Balancing: {orchestration_status['load_balancing_strategy']}")
        
        return {
            "performance_results": performance_results,
            "orchestration_status": orchestration_status,
            "success_rate": success_rate
        }
    
    finally:
        await orchestrator.stop_orchestration()


async def test_failure_scenarios_and_recovery():
    """Test failure scenarios and recovery mechanisms."""
    logger.info("Testing failure scenarios and recovery...")
    
    pipeline = ProcessingPipeline({"graceful_degradation": True})
    
    failure_scenarios = [
        {
            "name": "Empty Audio Input",
            "input": {"audio_data": b""},
            "expected_failure": True
        },
        {
            "name": "Invalid Language Code",
            "input": {"text_input": "Hello", "language": "invalid_lang"},
            "expected_failure": False  # Should fallback to default
        },
        {
            "name": "Extremely Long Text",
            "input": {"text_input": "Hello " * 1000},  # Very long text
            "expected_failure": False  # Should handle gracefully
        },
        {
            "name": "Special Characters",
            "input": {"text_input": "!@#$%^&*()_+{}|:<>?[]\\;'\",./ 测试 🎉"},
            "expected_failure": False
        },
        {
            "name": "Empty Text Input",
            "input": {"text_input": ""},
            "expected_failure": True
        }
    ]
    
    results = []
    
    for scenario in failure_scenarios:
        logger.info(f"Testing failure scenario: {scenario['name']}")
        
        try:
            result = await process_voice(
                session_id=f"failure_test_{len(results)}",
                user_id="failure_test_user",
                **scenario["input"]
            )
            
            # Analyze result
            actual_failure = result.status.value == "failed"
            expected_failure = scenario["expected_failure"]
            
            test_passed = (
                (expected_failure and actual_failure) or
                (not expected_failure and not actual_failure)
            )
            
            scenario_result = {
                "scenario": scenario["name"],
                "expected_failure": expected_failure,
                "actual_failure": actual_failure,
                "test_passed": test_passed,
                "processing_time_ms": result.processing_time_ms,
                "error_message": result.error_message,
                "graceful_degradation": not actual_failure or result.error_message is not None
            }
            
        except Exception as e:
            # Unexpected exception
            scenario_result = {
                "scenario": scenario["name"],
                "expected_failure": scenario["expected_failure"],
                "actual_failure": True,
                "test_passed": scenario["expected_failure"],
                "processing_time_ms": 0,
                "error_message": str(e),
                "graceful_degradation": False
            }
        
        results.append(scenario_result)
    
    print("\\n" + "="*60)
    print("FAILURE SCENARIOS AND RECOVERY TESTS")
    print("="*60)
    
    for result in results:
        status = "✅ PASSED" if result["test_passed"] else "❌ FAILED"
        print(f"{result['scenario']}: {status}")
        print(f"  Expected Failure: {result['expected_failure']}")
        print(f"  Actual Failure: {result['actual_failure']}")
        print(f"  Graceful Degradation: {result['graceful_degradation']}")
        if result["error_message"]:
            print(f"  Error: {result['error_message']}")
    
    return results


async def test_e2e_testing_framework():
    """Test the end-to-end testing framework."""
    logger.info("Testing E2E testing framework...")
    
    # Initialize E2E framework
    e2e_framework = E2ETestingFramework()
    
    # Create default test suites
    e2e_framework.create_default_test_suites()
    
    # Run functional test suite
    functional_results = await e2e_framework.run_test_suite(
        "functional_basic",
        parallel_execution=False
    )
    
    # Run a smaller performance test
    performance_results = await e2e_framework.run_test_suite(
        "performance_load",
        parallel_execution=True
    )
    
    print("\\n" + "="*60)
    print("E2E TESTING FRAMEWORK TESTS")
    print("="*60)
    
    print(f"Functional Tests:")
    print(f"  Status: {functional_results['status']}")
    print(f"  Success Rate: {functional_results['success_rate']:.1f}%")
    print(f"  Scenarios: {functional_results['total_scenarios']}")
    print(f"  Execution Time: {functional_results['execution_time_seconds']:.1f}s")
    
    print(f"\\nPerformance Tests:")
    print(f"  Status: {performance_results['status']}")
    print(f"  Success Rate: {performance_results['success_rate']:.1f}%")
    print(f"  Scenarios: {performance_results['total_scenarios']}")
    print(f"  Execution Time: {performance_results['execution_time_seconds']:.1f}s")
    
    if functional_results.get('performance_stats'):
        perf_stats = functional_results['performance_stats']
        print(f"\\nFunctional Performance Stats:")
        print(f"  Avg Execution Time: {perf_stats['avg_execution_time_ms']:.1f}ms")
        print(f"  Min Execution Time: {perf_stats['min_execution_time_ms']:.1f}ms")
        print(f"  Max Execution Time: {perf_stats['max_execution_time_ms']:.1f}ms")
    
    return {
        "functional_results": functional_results,
        "performance_results": performance_results
    }


async def test_specialized_features_integration():
    """Test integration of specialized feature agents."""
    logger.info("Testing specialized features integration...")
    
    feature_manager = SpecializedFeatureManager()
    
    # Test different feature combinations
    test_cases = [
        {
            "name": "Emotion Detection Only",
            "features": [FeatureType.EMOTION_DETECTION],
            "text": "I'm so excited about this new feature!",
            "expected_emotion": "excited"
        },
        {
            "name": "Accent Adaptation Only", 
            "features": [FeatureType.ACCENT_ADAPTATION],
            "text": "Hello, how are you today?",
            "context": {"target_accent": "british"}
        },
        {
            "name": "Arabic Support",
            "features": [FeatureType.ARABIC_SUPPORT],
            "text": "مرحبا، كيف حالك؟",
            "context": {"arabic_dialect": "msa"}
        },
        {
            "name": "Multiple Features",
            "features": [FeatureType.EMOTION_DETECTION, FeatureType.ACCENT_ADAPTATION],
            "text": "I'm really happy with the service!",
            "context": {"target_accent": "american"}
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        logger.info(f"Testing: {test_case['name']}")
        
        # Generate mock audio data
        audio_data = b"MOCK_AUDIO_" + test_case["text"].encode()[:50] + b"_END" + b"0" * 1000
        
        # Process features
        feature_results = await feature_manager.process_features(
            audio_data=audio_data,
            text=test_case["text"],
            context=test_case.get("context", {}),
            requested_features=test_case["features"]
        )
        
        # Analyze results
        test_success = True
        feature_details = {}
        
        for feature_type, result in feature_results.items():
            feature_details[feature_type.value] = {
                "success": result.success,
                "processing_time_ms": result.processing_time_ms,
                "confidence": result.confidence,
                "data_keys": list(result.data.keys()) if result.success else []
            }
            
            if not result.success:
                test_success = False
        
        test_result = {
            "test_case": test_case["name"],
            "success": test_success,
            "features_tested": len(test_case["features"]),
            "features_successful": len([r for r in feature_results.values() if r.success]),
            "feature_details": feature_details
        }
        
        results.append(test_result)
    
    # Get performance metrics
    performance_metrics = feature_manager.get_feature_performance()
    
    print("\\n" + "="*60)
    print("SPECIALIZED FEATURES INTEGRATION TESTS")
    print("="*60)
    
    for result in results:
        status = "✅ PASSED" if result["success"] else "❌ FAILED"
        print(f"{result['test_case']}: {status}")
        print(f"  Features Tested: {result['features_tested']}")
        print(f"  Features Successful: {result['features_successful']}")
        
        for feature, details in result["feature_details"].items():
            print(f"    {feature}: {'✅' if details['success'] else '❌'} ({details['processing_time_ms']:.1f}ms)")
    
    print(f"\\nFeature Performance Summary:")
    for feature, stats in performance_metrics.items():
        if stats['count'] > 0:
            print(f"  {feature}: {stats['avg_ms']:.1f}ms avg ({stats['count']} calls)")
    
    return {
        "test_results": results,
        "performance_metrics": performance_metrics
    }


async def main():
    """Main comprehensive system test function."""
    try:
        print("🚀 Starting Comprehensive System Tests...")
        
        # Run all test categories
        conversation_results = await test_complete_voice_conversations()
        load_results = await test_system_performance_under_load()
        failure_results = await test_failure_scenarios_and_recovery()
        e2e_results = await test_e2e_testing_framework()
        features_results = await test_specialized_features_integration()
        
        # Generate overall summary
        print("\\n" + "="*60)
        print("COMPREHENSIVE SYSTEM TEST SUMMARY")
        print("="*60)
        
        # Conversation tests
        conv_success = all(r["success"] for r in conversation_results)
        print(f"Voice Conversations: {'✅ PASSED' if conv_success else '❌ FAILED'}")
        print(f"  Scenarios: {len(conversation_results)}")
        
        # Load tests
        load_success = load_results["success_rate"] >= 90  # 90% success rate threshold
        print(f"Performance Under Load: {'✅ PASSED' if load_success else '❌ FAILED'}")
        print(f"  Success Rate: {load_results['success_rate']:.1f}%")
        
        # Failure tests
        failure_success = all(r["test_passed"] for r in failure_results)
        print(f"Failure Scenarios: {'✅ PASSED' if failure_success else '❌ FAILED'}")
        print(f"  Scenarios: {len(failure_results)}")
        
        # E2E framework tests
        e2e_success = (
            e2e_results["functional_results"]["status"] in ["passed", "partial"] and
            e2e_results["performance_results"]["status"] in ["passed", "partial"]
        )
        print(f"E2E Testing Framework: {'✅ PASSED' if e2e_success else '❌ FAILED'}")
        
        # Features tests
        features_success = all(r["success"] for r in features_results["test_results"])
        print(f"Specialized Features: {'✅ PASSED' if features_success else '❌ FAILED'}")
        print(f"  Feature Tests: {len(features_results['test_results'])}")
        
        # Overall result
        all_tests_passed = all([
            conv_success, load_success, failure_success, e2e_success, features_success
        ])
        
        print(f"\\nOverall System Test Result: {'🎉 ALL PASSED' if all_tests_passed else '⚠️ SOME FAILED'}")
        
        # Save detailed results
        detailed_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_success": all_tests_passed,
            "conversation_tests": conversation_results,
            "load_tests": load_results,
            "failure_tests": failure_results,
            "e2e_tests": e2e_results,
            "features_tests": features_results
        }
        
        with open("comprehensive_system_test_results.json", "w") as f:
            json.dump(detailed_results, f, indent=2, default=str)
        
        print(f"\\n📊 Detailed results saved to: comprehensive_system_test_results.json")
        
        return 0 if all_tests_passed else 1
        
    except Exception as e:
        print(f"\\n💥 Comprehensive system test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)