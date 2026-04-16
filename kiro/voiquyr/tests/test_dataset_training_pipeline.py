"""
Test Dataset Curation and Training Pipeline

This test file validates the dataset discovery, data preparation, and model training
components of the EUVoice AI platform.
"""

import pytest
pytest.importorskip("torch")

import asyncio
import tempfile
import shutil
import os
import json
import torch
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

# Import the modules we're testing
from src.agents.dataset_agent import (
    DatasetAgent, DatasetDiscovery, LicenseValidator, 
    DatasetQualityAssessment, DatasetFilter, DatasetMetadata
)
from src.agents.data_preparation import (
    DataPreparationPipeline, CommonVoicePreprocessor, VoxPopuliPreprocessor,
    SyntheticDataGenerator, DataAugmentation, PreprocessingConfig, AudioSample
)
from src.agents.model_training import (
    TrainingPipeline, LoRATrainer, ModelEvaluator, 
    TrainingConfig, ModelMetrics
)

class TestDatasetDiscovery:
    """Test dataset discovery functionality"""
    
    @pytest.fixture
    def discovery(self):
        return DatasetDiscovery()
    
    @pytest.mark.asyncio
    async def test_discover_datasets(self, discovery):
        """Test basic dataset discovery"""
        languages = ['en', 'de', 'fr']
        datasets = await discovery.discover_datasets(languages)
        
        assert isinstance(datasets, list)
        assert len(datasets) > 0
        
        # Check that all datasets have required metadata
        for dataset in datasets:
            assert isinstance(dataset, DatasetMetadata)
            assert dataset.name
            assert dataset.license
            assert dataset.language
            assert dataset.duration_hours > 0
    
    @pytest.mark.asyncio
    async def test_discover_huggingface_datasets(self, discovery):
        """Test Hugging Face dataset discovery"""
        languages = ['en', 'de']
        hf_datasets = await discovery._discover_huggingface_datasets(languages)
        
        assert isinstance(hf_datasets, list)
        # Should find at least Common Voice and VoxPopuli
        dataset_names = [d.name for d in hf_datasets]
        assert any('common_voice' in name.lower() for name in dataset_names)
    
    @pytest.mark.asyncio
    async def test_discover_known_datasets(self, discovery):
        """Test discovery of curated known datasets"""
        languages = ['en', 'multi']
        known_datasets = await discovery._discover_known_datasets(languages)
        
        assert isinstance(known_datasets, list)
        assert len(known_datasets) >= 2  # Should include MOSEL and CHiME
        
        # Check for specific datasets
        dataset_names = [d.name for d in known_datasets]
        assert 'MOSEL' in dataset_names
        assert 'CHiME' in dataset_names

class TestLicenseValidator:
    """Test license validation functionality"""
    
    @pytest.fixture
    def validator(self):
        return LicenseValidator()
    
    def test_validate_compliant_licenses(self, validator):
        """Test validation of EU-compliant licenses"""
        compliant_licenses = ['cc0-1.0', 'cc-by-4.0', 'apache-2.0', 'mit']
        
        for license_id in compliant_licenses:
            is_compliant, reason = validator.validate_license(license_id)
            assert is_compliant, f"License {license_id} should be compliant: {reason}"
    
    def test_validate_non_compliant_licenses(self, validator):
        """Test validation of non-compliant licenses"""
        non_compliant_licenses = ['gpl-3.0', 'proprietary', 'unknown-license']
        
        for license_id in non_compliant_licenses:
            is_compliant, reason = validator.validate_license(license_id)
            assert not is_compliant, f"License {license_id} should not be compliant"
    
    def test_license_aliases(self, validator):
        """Test license alias recognition"""
        aliases = [
            ('cc0', True),
            ('creative commons zero', True),
            ('public domain', True),
            ('cc-by', True)
        ]
        
        for alias, expected_compliant in aliases:
            is_compliant, _ = validator.validate_license(alias)
            assert is_compliant == expected_compliant
    
    def test_commercial_use_check(self, validator):
        """Test commercial use permission checking"""
        commercial_licenses = ['cc0-1.0', 'cc-by-4.0', 'apache-2.0', 'mit']
        
        for license_id in commercial_licenses:
            allows_commercial = validator.check_commercial_use(license_id)
            assert allows_commercial, f"License {license_id} should allow commercial use"

class TestDatasetQualityAssessment:
    """Test dataset quality assessment"""
    
    @pytest.fixture
    def assessor(self):
        return DatasetQualityAssessment()
    
    @pytest.mark.asyncio
    async def test_assess_quality_high_quality(self, assessor):
        """Test quality assessment for high-quality dataset"""
        metadata = DatasetMetadata(
            name="High Quality Dataset",
            source="huggingface",
            license="cc0-1.0",
            language="en",
            size_gb=100.0,
            num_samples=100000,
            sample_rate=48000,
            duration_hours=1000.0,
            quality_score=0.0,  # Will be calculated
            compliance_status="compliant",
            last_updated=datetime.now(),
            download_url="https://example.com",
            description="Test dataset"
        )
        
        quality_score = await assessor.assess_quality(metadata)
        
        assert 0.0 <= quality_score <= 1.0
        assert quality_score > 0.8  # Should be high quality
    
    @pytest.mark.asyncio
    async def test_assess_quality_low_quality(self, assessor):
        """Test quality assessment for low-quality dataset"""
        metadata = DatasetMetadata(
            name="Low Quality Dataset",
            source="unknown",
            license="unknown",
            language="en",
            size_gb=1.0,
            num_samples=100,
            sample_rate=8000,
            duration_hours=0.5,
            quality_score=0.0,
            compliance_status="non-compliant",
            last_updated=datetime(2020, 1, 1),
            download_url="https://example.com",
            description="Test dataset"
        )
        
        quality_score = await assessor.assess_quality(metadata)
        
        assert 0.0 <= quality_score <= 1.0
        assert quality_score < 0.5  # Should be low quality

class TestDatasetFilter:
    """Test dataset filtering functionality"""
    
    @pytest.fixture
    def filter_instance(self):
        return DatasetFilter(min_quality_score=0.7, require_eu_compliance=True)
    
    @pytest.mark.asyncio
    async def test_filter_datasets(self, filter_instance):
        """Test dataset filtering"""
        # Create test datasets
        good_dataset = DatasetMetadata(
            name="Good Dataset",
            source="huggingface",
            license="cc0-1.0",
            language="en",
            size_gb=50.0,
            num_samples=50000,
            sample_rate=16000,
            duration_hours=100.0,
            quality_score=0.9,
            compliance_status="compliant",
            last_updated=datetime.now(),
            download_url="https://example.com",
            description="Good test dataset"
        )
        
        bad_dataset = DatasetMetadata(
            name="Bad Dataset",
            source="unknown",
            license="proprietary",
            language="en",
            size_gb=1.0,
            num_samples=100,
            sample_rate=8000,
            duration_hours=0.1,
            quality_score=0.3,
            compliance_status="non-compliant",
            last_updated=datetime(2020, 1, 1),
            download_url="https://example.com",
            description="Bad test dataset"
        )
        
        datasets = [good_dataset, bad_dataset]
        filtered_datasets = await filter_instance.filter_datasets(datasets)
        
        assert len(filtered_datasets) == 1
        assert filtered_datasets[0].name == "Good Dataset"

class TestDatasetAgent:
    """Test main dataset agent functionality"""
    
    @pytest.fixture
    def temp_dir(self):
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def agent(self, temp_dir):
        return DatasetAgent(cache_dir=temp_dir)
    
    @pytest.mark.asyncio
    async def test_discover_and_validate_datasets(self, agent):
        """Test end-to-end dataset discovery and validation"""
        languages = ['en', 'de']
        datasets = await agent.discover_and_validate_datasets(languages)
        
        assert isinstance(datasets, list)
        assert len(datasets) > 0
        
        # All returned datasets should be validated
        for dataset in datasets:
            assert dataset.quality_score >= 0.7  # Default threshold
            assert dataset.duration_hours >= 1.0
            assert dataset.sample_rate >= 16000
    
    @pytest.mark.asyncio
    async def test_get_dataset_summary(self, agent):
        """Test dataset summary generation"""
        summary = await agent.get_dataset_summary()
        
        assert isinstance(summary, dict)
        assert 'total_datasets' in summary
        assert 'total_duration_hours' in summary
        assert 'languages' in summary
        assert 'datasets' in summary
        
        assert summary['total_datasets'] >= 0
        assert summary['total_duration_hours'] >= 0.0

class TestDataPreparation:
    """Test data preparation pipeline"""
    
    @pytest.fixture
    def temp_dir(self):
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def config(self):
        return PreprocessingConfig(
            target_sample_rate=16000,
            max_duration=10.0,
            min_duration=1.0,
            synthetic_data_ratio=0.1,
            noise_augmentation_ratio=0.1
        )
    
    @pytest.fixture
    def pipeline(self, config, temp_dir):
        return DataPreparationPipeline(config, cache_dir=temp_dir)
    
    def test_preprocessing_config(self, config):
        """Test preprocessing configuration"""
        assert config.target_sample_rate == 16000
        assert config.max_duration == 10.0
        assert config.min_duration == 1.0
        assert config.normalize_audio is True
        assert config.trim_silence is True
    
    @pytest.mark.asyncio
    async def test_synthetic_data_generation(self, temp_dir):
        """Test synthetic data generation"""
        config = PreprocessingConfig()
        generator = SyntheticDataGenerator(config)
        
        # Test with small number of samples
        synthetic_samples = await generator.generate_synthetic_data(
            temp_dir, num_samples=10, languages=['en']
        )
        
        assert isinstance(synthetic_samples, list)
        assert len(synthetic_samples) <= 10  # May be less due to errors
        
        for sample in synthetic_samples:
            assert isinstance(sample, AudioSample)
            assert sample.dataset_source == "synthetic_xtts"
            assert sample.language == "en"
            assert os.path.exists(sample.audio_path)
    
    @pytest.mark.asyncio
    async def test_data_augmentation(self, temp_dir):
        """Test data augmentation"""
        config = PreprocessingConfig()
        augmentation = DataAugmentation(config)
        
        # Create a test audio sample
        test_audio = np.random.randn(16000).astype(np.float32)  # 1 second of audio
        test_audio_path = os.path.join(temp_dir, "test_audio.wav")
        
        import soundfile as sf
        sf.write(test_audio_path, test_audio, 16000)
        
        # Create test sample
        test_sample = AudioSample(
            audio_path=test_audio_path,
            text="Test audio sample",
            language="en",
            duration=1.0,
            sample_rate=16000,
            dataset_source="test"
        )
        
        # Apply augmentation
        augmented_samples = await augmentation.augment_samples([test_sample], temp_dir)
        
        assert len(augmented_samples) > 1  # Should include original + augmented
        
        # Check that augmented files exist
        augmented_only = [s for s in augmented_samples if s.audio_path != test_audio_path]
        for sample in augmented_only:
            assert os.path.exists(sample.audio_path)
            assert "aug_" in sample.dataset_source

class TestModelTraining:
    """Test model training functionality"""
    
    @pytest.fixture
    def temp_dir(self):
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def config(self, temp_dir):
        return TrainingConfig(
            model_name="microsoft/speecht5_asr",
            learning_rate=1e-4,
            batch_size=2,
            num_epochs=1,
            use_lora=True,
            lora_r=8,
            output_dir=temp_dir,
            eval_steps=10,
            save_steps=20,
            logging_steps=5
        )
    
    def test_training_config(self, config):
        """Test training configuration"""
        assert config.learning_rate == 1e-4
        assert config.batch_size == 2
        assert config.num_epochs == 1
        assert config.use_lora is True
        assert config.lora_r == 8
        assert len(config.lora_target_modules) > 0
    
    def test_model_metrics(self):
        """Test model metrics dataclass"""
        metrics = ModelMetrics(
            model_name="test_model",
            dataset_name="test_dataset",
            language="en",
            accuracy=0.85,
            f1_score=0.82,
            wer=0.15
        )
        
        assert metrics.model_name == "test_model"
        assert metrics.accuracy == 0.85
        assert metrics.f1_score == 0.82
        assert metrics.wer == 0.15
        assert isinstance(metrics.timestamp, datetime)
    
    @pytest.mark.asyncio
    async def test_model_evaluator(self):
        """Test model evaluation"""
        evaluator = ModelEvaluator()
        
        # Create mock model and dataloader
        mock_model = Mock()
        mock_model.eval = Mock()
        mock_model.parameters = Mock(return_value=[torch.tensor([1.0])])
        
        # Mock forward pass
        mock_outputs = Mock()
        mock_outputs.loss = torch.tensor(0.5)
        mock_outputs.logits = torch.randn(2, 10, 100)  # batch_size=2, seq_len=10, vocab_size=100
        mock_model.return_value = mock_outputs
        
        # Create mock dataloader
        mock_batch = {
            'input_values': torch.randn(2, 16000),
            'labels': torch.randint(0, 100, (2, 10))
        }
        mock_dataloader = [mock_batch]
        
        with patch.object(mock_model, '__call__', return_value=mock_outputs):
            metrics = await evaluator.evaluate_model(
                mock_model, mock_dataloader, "test_model", "test_dataset"
            )
        
        assert isinstance(metrics, ModelMetrics)
        assert metrics.model_name == "test_model"
        assert metrics.dataset_name == "test_dataset"
        assert metrics.validation_loss > 0
    
    def test_model_comparison(self):
        """Test model comparison functionality"""
        evaluator = ModelEvaluator()
        
        # Create test metrics
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
        
        assert 'summary' in comparison
        assert 'best_models' in comparison
        assert 'detailed_comparison' in comparison
        
        assert comparison['summary']['total_models'] == 2
        
        # Check that model2 is identified as best for accuracy
        best_accuracy = comparison['best_models']['test_dataset_en']['best_accuracy']
        assert best_accuracy['model'] == "model2"
        assert best_accuracy['accuracy'] == 0.90

class TestIntegration:
    """Integration tests for the complete pipeline"""
    
    @pytest.fixture
    def temp_dir(self):
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_end_to_end_pipeline(self, temp_dir):
        """Test complete end-to-end pipeline"""
        # 1. Dataset discovery and validation
        dataset_agent = DatasetAgent(cache_dir=os.path.join(temp_dir, "datasets"))
        datasets = await dataset_agent.discover_and_validate_datasets(['en'])
        
        assert len(datasets) > 0
        
        # 2. Data preparation
        prep_config = PreprocessingConfig(
            synthetic_data_ratio=0.05,  # Small ratio for testing
            noise_augmentation_ratio=0.05
        )
        prep_pipeline = DataPreparationPipeline(
            prep_config, 
            cache_dir=os.path.join(temp_dir, "prepared")
        )
        
        # Mock the actual data preparation to avoid downloading large datasets
        with patch.object(prep_pipeline.common_voice_processor, 'preprocess_dataset', 
                         return_value=[]):
            with patch.object(prep_pipeline.voxpopuli_processor, 'preprocess_dataset',
                             return_value=[]):
                prepared_data = await prep_pipeline.prepare_training_data(
                    languages=['en'],
                    include_synthetic=False,  # Skip synthetic for testing
                    include_augmentation=False  # Skip augmentation for testing
                )
        
        assert isinstance(prepared_data, dict)
        
        # 3. Model training setup (without actual training)
        training_config = TrainingConfig(
            batch_size=1,
            num_epochs=1,
            output_dir=os.path.join(temp_dir, "models")
        )
        
        training_pipeline = TrainingPipeline(training_config)
        
        # Verify pipeline is set up correctly
        assert training_pipeline.config.batch_size == 1
        assert training_pipeline.lora_trainer is not None
        assert training_pipeline.evaluator is not None
    
    @pytest.mark.asyncio
    async def test_dataset_to_training_flow(self, temp_dir):
        """Test flow from dataset discovery to training preparation"""
        # Discover datasets
        agent = DatasetAgent(cache_dir=temp_dir)
        datasets = await agent.discover_and_validate_datasets(['en'])
        
        # Get summary
        summary = await agent.get_dataset_summary()
        
        # Verify we have datasets for training
        assert summary['total_datasets'] > 0
        assert summary['total_duration_hours'] > 0
        
        # Verify datasets meet training requirements
        for dataset_info in summary['datasets']:
            assert dataset_info['quality_score'] >= 0.7
            assert dataset_info['duration_hours'] >= 1.0

# Performance and stress tests
class TestPerformance:
    """Performance tests for the pipeline"""
    
    @pytest.mark.asyncio
    async def test_dataset_discovery_performance(self):
        """Test dataset discovery performance"""
        import time
        
        discovery = DatasetDiscovery()
        
        start_time = time.time()
        datasets = await discovery.discover_datasets(['en', 'de'])
        end_time = time.time()
        
        discovery_time = end_time - start_time
        
        # Should complete within reasonable time
        assert discovery_time < 30.0  # 30 seconds max
        assert len(datasets) > 0
    
    @pytest.mark.asyncio
    async def test_license_validation_performance(self):
        """Test license validation performance"""
        import time
        
        validator = LicenseValidator()
        licenses_to_test = ['cc0-1.0', 'cc-by-4.0', 'apache-2.0', 'mit', 'gpl-3.0'] * 100
        
        start_time = time.time()
        for license_id in licenses_to_test:
            validator.validate_license(license_id)
        end_time = time.time()
        
        validation_time = end_time - start_time
        
        # Should be very fast
        assert validation_time < 1.0  # 1 second max for 500 validations

# Utility functions for testing
def create_mock_audio_sample(temp_dir: str, duration: float = 1.0, sample_rate: int = 16000) -> str:
    """Create a mock audio file for testing"""
    import soundfile as sf
    
    # Generate simple sine wave
    t = np.linspace(0, duration, int(duration * sample_rate))
    audio = 0.1 * np.sin(2 * np.pi * 440 * t)  # 440 Hz sine wave
    
    audio_path = os.path.join(temp_dir, f"mock_audio_{int(duration)}s.wav")
    sf.write(audio_path, audio, sample_rate)
    
    return audio_path

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

# Main test runner
if __name__ == "__main__":
    # Run basic functionality tests
    async def run_basic_tests():
        print("Running basic dataset curation and training pipeline tests...")
        
        # Test dataset discovery
        print("Testing dataset discovery...")
        discovery = DatasetDiscovery()
        datasets = await discovery.discover_datasets(['en'])
        print(f"Discovered {len(datasets)} datasets")
        
        # Test license validation
        print("Testing license validation...")
        validator = LicenseValidator()
        is_compliant, reason = validator.validate_license('cc0-1.0')
        print(f"CC0 license validation: {is_compliant} - {reason}")
        
        # Test quality assessment
        print("Testing quality assessment...")
        assessor = DatasetQualityAssessment()
        test_metadata = create_mock_dataset_metadata()
        quality_score = await assessor.assess_quality(test_metadata)
        print(f"Quality score: {quality_score:.2f}")
        
        # Test dataset agent
        print("Testing dataset agent...")
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = DatasetAgent(cache_dir=temp_dir)
            summary = await agent.get_dataset_summary()
            print(f"Dataset summary: {summary['total_datasets']} datasets, {summary['total_duration_hours']:.1f} hours")
        
        print("Basic tests completed successfully!")
    
    # Run the tests
    asyncio.run(run_basic_tests())