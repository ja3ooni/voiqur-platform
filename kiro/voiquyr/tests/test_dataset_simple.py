"""
Simple test for Dataset Curation and Training Pipeline

This test validates the core functionality without external dependencies.
"""

import asyncio
import tempfile
import shutil
import os
import json
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.append('src')

# Import the modules we're testing
from agents.dataset_agent import (
    DatasetAgent, DatasetDiscovery, LicenseValidator, 
    DatasetQualityAssessment, DatasetFilter, DatasetMetadata
)
from agents.data_preparation import (
    DataPreparationPipeline, SyntheticDataGenerator, 
    PreprocessingConfig, AudioSample
)
from agents.model_training import (
    TrainingConfig, ModelMetrics, ModelEvaluator
)

def create_mock_dataset_metadata(name: str = "test_dataset") -> DatasetMetadata:
    """Create mock dataset metadata for testing"""
    return DatasetMetadata(
        name=name,
        source="test",
        license="cc0-1.0",
        language="en",
        size_gb=10.0,
        num_samples=10000,
        sample_rate=16000,
        duration_hours=10.0,
        quality_score=0.9,
        compliance_status="compliant",
        last_updated=datetime.now(),
        download_url="https://example.com",
        description=f"Mock dataset {name} for testing"
    )

async def test_dataset_discovery():
    """Test dataset discovery functionality"""
    print("Testing dataset discovery...")
    
    discovery = DatasetDiscovery()
    
    # Test basic discovery
    datasets = await discovery.discover_datasets(['en', 'de'])
    assert isinstance(datasets, list), "Discovery should return a list"
    assert len(datasets) > 0, "Should discover at least some datasets"
    
    # Check dataset metadata structure
    for dataset in datasets:
        assert isinstance(dataset, DatasetMetadata), "Should return DatasetMetadata objects"
        assert dataset.name, "Dataset should have a name"
        assert dataset.license, "Dataset should have a license"
        assert dataset.duration_hours > 0, "Dataset should have positive duration"
    
    print(f"✓ Discovered {len(datasets)} datasets")
    return True

async def test_license_validation():
    """Test license validation"""
    print("Testing license validation...")
    
    validator = LicenseValidator()
    
    # Test compliant licenses
    compliant_licenses = ['cc0-1.0', 'cc-by-4.0', 'apache-2.0', 'mit']
    for license_id in compliant_licenses:
        is_compliant, reason = validator.validate_license(license_id)
        assert is_compliant, f"License {license_id} should be compliant: {reason}"
    
    # Test non-compliant licenses
    non_compliant_licenses = ['gpl-3.0', 'proprietary', 'unknown']
    for license_id in non_compliant_licenses:
        is_compliant, reason = validator.validate_license(license_id)
        assert not is_compliant, f"License {license_id} should not be compliant"
    
    # Test commercial use
    commercial_ok = validator.check_commercial_use('cc0-1.0')
    assert commercial_ok, "CC0 should allow commercial use"
    
    print("✓ License validation working correctly")
    return True

async def test_quality_assessment():
    """Test dataset quality assessment"""
    print("Testing quality assessment...")
    
    assessor = DatasetQualityAssessment()
    
    # Test high-quality dataset
    high_quality_metadata = DatasetMetadata(
        name="High Quality Dataset",
        source="huggingface",
        license="cc0-1.0",
        language="en",
        size_gb=100.0,
        num_samples=100000,
        sample_rate=48000,
        duration_hours=1000.0,
        quality_score=0.0,
        compliance_status="compliant",
        last_updated=datetime.now(),
        download_url="https://example.com",
        description="High quality test dataset"
    )
    
    quality_score = await assessor.assess_quality(high_quality_metadata)
    assert 0.0 <= quality_score <= 1.0, "Quality score should be between 0 and 1"
    assert quality_score > 0.7, f"High quality dataset should score > 0.7, got {quality_score}"
    
    # Test low-quality dataset
    low_quality_metadata = DatasetMetadata(
        name="Low Quality Dataset",
        source="unknown",
        license="unknown",
        language="en",
        size_gb=1.0,
        num_samples=100,
        sample_rate=8000,
        duration_hours=0.1,
        quality_score=0.0,
        compliance_status="non-compliant",
        last_updated=datetime(2020, 1, 1),
        download_url="https://example.com",
        description="Low quality test dataset"
    )
    
    low_quality_score = await assessor.assess_quality(low_quality_metadata)
    assert low_quality_score < quality_score, "Low quality dataset should score lower"
    
    print(f"✓ Quality assessment working (high: {quality_score:.2f}, low: {low_quality_score:.2f})")
    return True

async def test_dataset_filter():
    """Test dataset filtering"""
    print("Testing dataset filtering...")
    
    filter_instance = DatasetFilter(min_quality_score=0.7, require_eu_compliance=True)
    
    # Create test datasets
    good_dataset = create_mock_dataset_metadata("Good Dataset")
    good_dataset.quality_score = 0.9
    
    bad_dataset = create_mock_dataset_metadata("Bad Dataset")
    bad_dataset.license = "proprietary"
    bad_dataset.quality_score = 0.3
    bad_dataset.duration_hours = 0.1
    
    datasets = [good_dataset, bad_dataset]
    filtered_datasets = await filter_instance.filter_datasets(datasets)
    
    assert len(filtered_datasets) == 1, "Should filter out bad dataset"
    assert filtered_datasets[0].name == "Good Dataset", "Should keep good dataset"
    
    print("✓ Dataset filtering working correctly")
    return True

async def test_dataset_agent():
    """Test main dataset agent"""
    print("Testing dataset agent...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        agent = DatasetAgent(cache_dir=temp_dir)
        
        # Test discovery and validation
        datasets = await agent.discover_and_validate_datasets(['en'])
        assert isinstance(datasets, list), "Should return list of datasets"
        
        # Test summary generation
        summary = await agent.get_dataset_summary()
        assert isinstance(summary, dict), "Summary should be a dictionary"
        assert 'total_datasets' in summary, "Summary should include total datasets"
        assert 'total_duration_hours' in summary, "Summary should include total duration"
        assert summary['total_datasets'] >= 0, "Total datasets should be non-negative"
        
        print(f"✓ Dataset agent working ({summary['total_datasets']} datasets, {summary['total_duration_hours']:.1f}h)")
    
    return True

async def test_preprocessing_config():
    """Test preprocessing configuration"""
    print("Testing preprocessing configuration...")
    
    config = PreprocessingConfig(
        target_sample_rate=16000,
        max_duration=30.0,
        min_duration=0.5,
        synthetic_data_ratio=0.2
    )
    
    assert config.target_sample_rate == 16000, "Sample rate should be set correctly"
    assert config.max_duration == 30.0, "Max duration should be set correctly"
    assert config.synthetic_data_ratio == 0.2, "Synthetic ratio should be set correctly"
    assert config.normalize_audio is True, "Audio normalization should be enabled by default"
    
    print("✓ Preprocessing configuration working correctly")
    return True

async def test_synthetic_data_generator():
    """Test synthetic data generation"""
    print("Testing synthetic data generation...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config = PreprocessingConfig()
        generator = SyntheticDataGenerator(config)
        
        # Test with small number of samples
        synthetic_samples = await generator.generate_synthetic_data(
            temp_dir, num_samples=5, languages=['en']
        )
        
        assert isinstance(synthetic_samples, list), "Should return list of samples"
        
        for sample in synthetic_samples:
            assert isinstance(sample, AudioSample), "Should return AudioSample objects"
            assert sample.dataset_source == "synthetic_xtts", "Should mark as synthetic"
            assert sample.language == "en", "Should have correct language"
            assert os.path.exists(sample.audio_path), "Audio file should exist"
        
        print(f"✓ Generated {len(synthetic_samples)} synthetic samples")
    
    return True

async def test_training_config():
    """Test training configuration"""
    print("Testing training configuration...")
    
    config = TrainingConfig(
        model_name="test_model",
        learning_rate=1e-4,
        batch_size=16,
        num_epochs=5,
        use_lora=True,
        lora_r=16
    )
    
    assert config.model_name == "test_model", "Model name should be set correctly"
    assert config.learning_rate == 1e-4, "Learning rate should be set correctly"
    assert config.use_lora is True, "LoRA should be enabled"
    assert config.lora_r == 16, "LoRA rank should be set correctly"
    assert len(config.lora_target_modules) > 0, "Should have target modules for LoRA"
    
    print("✓ Training configuration working correctly")
    return True

async def test_model_metrics():
    """Test model metrics"""
    print("Testing model metrics...")
    
    metrics = ModelMetrics(
        model_name="test_model",
        dataset_name="test_dataset",
        language="en",
        accuracy=0.85,
        f1_score=0.82,
        wer=0.15,
        training_time=3600.0
    )
    
    assert metrics.model_name == "test_model", "Model name should be set"
    assert metrics.accuracy == 0.85, "Accuracy should be set correctly"
    assert metrics.f1_score == 0.82, "F1 score should be set correctly"
    assert metrics.wer == 0.15, "WER should be set correctly"
    assert isinstance(metrics.timestamp, datetime), "Timestamp should be set automatically"
    
    print("✓ Model metrics working correctly")
    return True

async def test_model_evaluator():
    """Test model evaluator"""
    print("Testing model evaluator...")
    
    evaluator = ModelEvaluator()
    
    # Test model comparison
    metrics1 = ModelMetrics(
        model_name="model1",
        dataset_name="test_dataset",
        language="en",
        accuracy=0.85,
        f1_score=0.82,
        wer=0.15
    )
    
    metrics2 = ModelMetrics(
        model_name="model2",
        dataset_name="test_dataset",
        language="en",
        accuracy=0.90,
        f1_score=0.88,
        wer=0.12
    )
    
    comparison = evaluator.compare_models([metrics1, metrics2])
    
    assert 'summary' in comparison, "Comparison should include summary"
    assert 'best_models' in comparison, "Comparison should include best models"
    assert comparison['summary']['total_models'] == 2, "Should count models correctly"
    
    # Check best model identification
    best_accuracy = comparison['best_models']['test_dataset_en']['best_accuracy']
    assert best_accuracy['model'] == "model2", "Should identify model2 as best accuracy"
    assert best_accuracy['accuracy'] == 0.90, "Should report correct accuracy"
    
    print("✓ Model evaluator working correctly")
    return True

async def test_end_to_end_flow():
    """Test end-to-end workflow"""
    print("Testing end-to-end workflow...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # 1. Dataset discovery
        agent = DatasetAgent(cache_dir=os.path.join(temp_dir, "datasets"))
        datasets = await agent.discover_and_validate_datasets(['en'])
        assert len(datasets) > 0, "Should discover datasets"
        
        # 2. Get summary
        summary = await agent.get_dataset_summary()
        assert summary['total_datasets'] > 0, "Should have datasets in summary"
        
        # 3. Preprocessing configuration
        prep_config = PreprocessingConfig(synthetic_data_ratio=0.1)
        assert prep_config.target_sample_rate == 16000, "Should have correct sample rate"
        
        # 4. Training configuration
        train_config = TrainingConfig(
            batch_size=4,
            num_epochs=1,
            output_dir=os.path.join(temp_dir, "models")
        )
        assert train_config.batch_size == 4, "Should have correct batch size"
        
        print("✓ End-to-end workflow components working correctly")
    
    return True

async def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("Running Dataset Curation and Training Pipeline Tests")
    print("=" * 60)
    
    tests = [
        ("Dataset Discovery", test_dataset_discovery),
        ("License Validation", test_license_validation),
        ("Quality Assessment", test_quality_assessment),
        ("Dataset Filter", test_dataset_filter),
        ("Dataset Agent", test_dataset_agent),
        ("Preprocessing Config", test_preprocessing_config),
        ("Synthetic Data Generator", test_synthetic_data_generator),
        ("Training Config", test_training_config),
        ("Model Metrics", test_model_metrics),
        ("Model Evaluator", test_model_evaluator),
        ("End-to-End Flow", test_end_to_end_flow)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\n--- {test_name} ---")
            result = await test_func()
            if result:
                passed += 1
                print(f"✓ {test_name} PASSED")
            else:
                failed += 1
                print(f"✗ {test_name} FAILED")
        except Exception as e:
            failed += 1
            print(f"✗ {test_name} FAILED: {e}")
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("🎉 All tests passed! Dataset curation and training pipeline is working correctly.")
    else:
        print(f"⚠️  {failed} tests failed. Please check the implementation.")
    
    return failed == 0

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)