"""
Dataset Curation and Training Pipeline Agent

This agent handles automated dataset discovery, validation, and curation
for EU-compliant voice assistant training data.
"""

import asyncio
import logging
import os
import json
import hashlib
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime

# Optional imports with fallbacks
try:
    import requests
except ImportError:
    requests = None

try:
    import torch
    import torchaudio
except ImportError:
    torch = None
    torchaudio = None

try:
    from datasets import load_dataset, Dataset
except ImportError:
    load_dataset = None
    Dataset = None

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    from urllib.parse import urlparse
except ImportError:
    urlparse = None

import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DatasetMetadata:
    """Metadata for a discovered dataset"""
    name: str
    source: str
    license: str
    language: str
    size_gb: float
    num_samples: int
    sample_rate: int
    duration_hours: float
    quality_score: float
    compliance_status: str
    last_updated: datetime
    download_url: str
    description: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['last_updated'] = self.last_updated.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DatasetMetadata':
        """Create from dictionary"""
        data['last_updated'] = datetime.fromisoformat(data['last_updated'])
        return cls(**data)

@dataclass
class LicenseInfo:
    """License information for compliance checking"""
    license_id: str
    is_eu_compliant: bool
    allows_commercial: bool
    requires_attribution: bool
    description: str

class DatasetDiscovery:
    """Automated dataset discovery from open-source repositories"""
    
    def __init__(self):
        self.eu_compliant_licenses = {
            'cc0-1.0': LicenseInfo('cc0-1.0', True, True, False, 'Creative Commons Zero'),
            'cc-by-4.0': LicenseInfo('cc-by-4.0', True, True, True, 'Creative Commons Attribution'),
            'cc-by-sa-4.0': LicenseInfo('cc-by-sa-4.0', True, True, True, 'Creative Commons Attribution-ShareAlike'),
            'apache-2.0': LicenseInfo('apache-2.0', True, True, True, 'Apache License 2.0'),
            'mit': LicenseInfo('mit', True, True, True, 'MIT License'),
            'bsd-3-clause': LicenseInfo('bsd-3-clause', True, True, True, 'BSD 3-Clause License')
        }
        
        self.known_datasets = {
            'mozilla-foundation/common_voice_17_0': {
                'languages': ['en', 'de', 'fr', 'es', 'it', 'pt', 'nl', 'pl', 'cs', 'hu', 'et', 'lv', 'lt', 'mt', 'sk', 'sl', 'bg', 'hr', 'ro', 'el', 'sv', 'da', 'fi'],
                'license': 'cc0-1.0',
                'type': 'speech'
            },
            'facebook/voxpopuli': {
                'languages': ['en', 'de', 'fr', 'es', 'it', 'pt', 'nl', 'pl', 'cs', 'hu', 'et', 'lv', 'lt', 'sk', 'sl', 'bg', 'hr', 'ro', 'el', 'sv', 'da', 'fi'],
                'license': 'cc0-1.0',
                'type': 'speech'
            },
            'openslr/granary': {
                'languages': ['multi'],
                'license': 'cc-by-4.0',
                'type': 'speech'
            }
        }
    
    async def discover_datasets(self, languages: List[str] = None) -> List[DatasetMetadata]:
        """
        Discover datasets from various sources
        
        Args:
            languages: List of target languages (ISO codes)
            
        Returns:
            List of discovered dataset metadata
        """
        if languages is None:
            languages = ['en', 'de', 'fr', 'es', 'it', 'pt', 'nl', 'pl', 'cs', 'hu', 'et', 'lv', 'lt', 'mt', 'sk', 'sl', 'bg', 'hr', 'ro', 'el', 'sv', 'da', 'fi']
        
        discovered_datasets = []
        
        # Discover from Hugging Face Hub
        hf_datasets = await self._discover_huggingface_datasets(languages)
        discovered_datasets.extend(hf_datasets)
        
        # Discover from OpenSLR
        openslr_datasets = await self._discover_openslr_datasets(languages)
        discovered_datasets.extend(openslr_datasets)
        
        # Discover from known high-quality sources
        known_datasets = await self._discover_known_datasets(languages)
        discovered_datasets.extend(known_datasets)
        
        logger.info(f"Discovered {len(discovered_datasets)} datasets")
        return discovered_datasets
    
    async def _discover_huggingface_datasets(self, languages: List[str]) -> List[DatasetMetadata]:
        """Discover datasets from Hugging Face Hub"""
        datasets = []
        
        for dataset_id, info in self.known_datasets.items():
            if any(lang in info['languages'] for lang in languages):
                try:
                    metadata = await self._get_huggingface_metadata(dataset_id, info)
                    if metadata:
                        datasets.append(metadata)
                except Exception as e:
                    logger.warning(f"Failed to get metadata for {dataset_id}: {e}")
        
        return datasets
    
    async def _discover_openslr_datasets(self, languages: List[str]) -> List[DatasetMetadata]:
        """Discover datasets from OpenSLR"""
        # This would implement OpenSLR API discovery
        # For now, return empty list as OpenSLR doesn't have a unified API
        return []
    
    async def _discover_known_datasets(self, languages: List[str]) -> List[DatasetMetadata]:
        """Discover from curated list of known high-quality datasets"""
        datasets = []
        
        # MOSEL dataset
        mosel_metadata = DatasetMetadata(
            name="MOSEL",
            source="openslr",
            license="cc-by-4.0",
            language="multi",
            size_gb=950.0,
            num_samples=950000,
            sample_rate=16000,
            duration_hours=950.0,
            quality_score=0.95,
            compliance_status="compliant",
            last_updated=datetime.now(),
            download_url="https://www.openslr.org/94/",
            description="Multilingual Open Speech Dataset for Language Learning"
        )
        datasets.append(mosel_metadata)
        
        # CHiME dataset for noise augmentation
        chime_metadata = DatasetMetadata(
            name="CHiME",
            source="chime",
            license="cc-by-4.0",
            language="en",
            size_gb=50.0,
            num_samples=50000,
            sample_rate=16000,
            duration_hours=100.0,
            quality_score=0.90,
            compliance_status="compliant",
            last_updated=datetime.now(),
            download_url="https://spandh.dcs.shef.ac.uk/chime_challenge/",
            description="Computational Hearing in Multisource Environments"
        )
        datasets.append(chime_metadata)
        
        return datasets
    
    async def _get_huggingface_metadata(self, dataset_id: str, info: Dict) -> Optional[DatasetMetadata]:
        """Get metadata for a Hugging Face dataset"""
        try:
            # This would use the Hugging Face API to get actual metadata
            # For now, return mock data based on known information
            
            if 'common_voice' in dataset_id:
                return DatasetMetadata(
                    name="Mozilla Common Voice 17.0",
                    source="huggingface",
                    license=info['license'],
                    language="multi",
                    size_gb=100.0,
                    num_samples=1000000,
                    sample_rate=48000,
                    duration_hours=9000.0,
                    quality_score=0.92,
                    compliance_status="compliant",
                    last_updated=datetime.now(),
                    download_url=f"https://huggingface.co/datasets/{dataset_id}",
                    description="Mozilla Common Voice multilingual speech dataset"
                )
            elif 'voxpopuli' in dataset_id:
                return DatasetMetadata(
                    name="VoxPopuli",
                    source="huggingface",
                    license=info['license'],
                    language="multi",
                    size_gb=500.0,
                    num_samples=400000,
                    sample_rate=16000,
                    duration_hours=100000.0,
                    quality_score=0.94,
                    compliance_status="compliant",
                    last_updated=datetime.now(),
                    download_url=f"https://huggingface.co/datasets/{dataset_id}",
                    description="VoxPopuli multilingual speech corpus"
                )
            
        except Exception as e:
            logger.error(f"Error getting metadata for {dataset_id}: {e}")
            return None

class LicenseValidator:
    """Validates dataset licenses for EU compliance"""
    
    def __init__(self):
        self.discovery = DatasetDiscovery()
    
    def validate_license(self, license_id: str) -> Tuple[bool, str]:
        """
        Validate if a license is EU compliant
        
        Args:
            license_id: License identifier (e.g., 'cc0-1.0')
            
        Returns:
            Tuple of (is_compliant, reason)
        """
        license_id = license_id.lower().strip()
        
        if license_id in self.discovery.eu_compliant_licenses:
            license_info = self.discovery.eu_compliant_licenses[license_id]
            return True, f"License {license_id} is EU compliant: {license_info.description}"
        
        # Check for variations and common aliases
        license_aliases = {
            'cc0': 'cc0-1.0',
            'cc-by': 'cc-by-4.0',
            'creative commons zero': 'cc0-1.0',
            'public domain': 'cc0-1.0'
        }
        
        for alias, canonical in license_aliases.items():
            if alias in license_id:
                if canonical in self.discovery.eu_compliant_licenses:
                    return True, f"License {license_id} (mapped to {canonical}) is EU compliant"
        
        return False, f"License {license_id} is not in the approved EU compliant license list"
    
    def check_commercial_use(self, license_id: str) -> bool:
        """Check if license allows commercial use"""
        license_id = license_id.lower().strip()
        if license_id in self.discovery.eu_compliant_licenses:
            return self.discovery.eu_compliant_licenses[license_id].allows_commercial
        return False

class DatasetQualityAssessment:
    """Assesses dataset quality for training suitability"""
    
    def __init__(self):
        self.min_sample_rate = 16000
        self.min_duration_hours = 1.0
        self.min_samples = 1000
    
    async def assess_quality(self, metadata: DatasetMetadata, sample_path: Optional[str] = None) -> float:
        """
        Assess dataset quality score (0.0 to 1.0)
        
        Args:
            metadata: Dataset metadata
            sample_path: Optional path to sample files for audio analysis
            
        Returns:
            Quality score between 0.0 and 1.0
        """
        score = 0.0
        
        # Sample rate quality (0.2 weight)
        if metadata.sample_rate >= 48000:
            score += 0.2
        elif metadata.sample_rate >= 22050:
            score += 0.15
        elif metadata.sample_rate >= 16000:
            score += 0.1
        
        # Dataset size quality (0.3 weight)
        if metadata.duration_hours >= 1000:
            score += 0.3
        elif metadata.duration_hours >= 100:
            score += 0.25
        elif metadata.duration_hours >= 10:
            score += 0.2
        elif metadata.duration_hours >= 1:
            score += 0.1
        
        # License quality (0.2 weight)
        validator = LicenseValidator()
        is_compliant, _ = validator.validate_license(metadata.license)
        if is_compliant:
            score += 0.2
        
        # Source reputation (0.15 weight)
        reputable_sources = ['huggingface', 'openslr', 'mozilla', 'facebook', 'google']
        if any(source in metadata.source.lower() for source in reputable_sources):
            score += 0.15
        
        # Recency (0.15 weight)
        days_old = (datetime.now() - metadata.last_updated).days
        if days_old <= 365:
            score += 0.15
        elif days_old <= 730:
            score += 0.1
        elif days_old <= 1095:
            score += 0.05
        
        # Audio quality assessment if sample available
        if sample_path and os.path.exists(sample_path):
            audio_score = await self._assess_audio_quality(sample_path)
            score = (score * 0.8) + (audio_score * 0.2)
        
        return min(1.0, score)
    
    async def _assess_audio_quality(self, sample_path: str) -> float:
        """Assess audio quality from sample files"""
        try:
            if torchaudio is None:
                return 0.5  # Default score if torchaudio not available
                
            # Load a few sample files and analyze
            audio_files = list(Path(sample_path).glob("*.wav"))[:10]
            if not audio_files:
                return 0.5  # Default score if no samples
            
            quality_scores = []
            
            for audio_file in audio_files:
                try:
                    waveform, sample_rate = torchaudio.load(str(audio_file))
                    
                    if torch is not None and torchaudio is not None:
                        # Check for clipping
                        clipping_ratio = torch.sum(torch.abs(waveform) > 0.95) / waveform.numel()
                        clipping_score = max(0, 1.0 - clipping_ratio * 10)
                        
                        # Check signal-to-noise ratio (simplified)
                        signal_power = torch.mean(waveform ** 2)
                        snr_score = min(1.0, float(signal_power) * 100)
                        
                        # Check for silence
                        silence_ratio = torch.sum(torch.abs(waveform) < 0.01) / waveform.numel()
                        silence_score = max(0, 1.0 - silence_ratio)
                    else:
                        # Fallback scores if torch is not available
                        clipping_score = 0.8
                        snr_score = 0.7
                        silence_score = 0.9
                    
                    file_score = (clipping_score + snr_score + silence_score) / 3
                    quality_scores.append(file_score)
                    
                except Exception as e:
                    logger.warning(f"Error analyzing {audio_file}: {e}")
                    continue
            
            return sum(quality_scores) / len(quality_scores) if quality_scores else 0.5
            
        except Exception as e:
            logger.error(f"Error in audio quality assessment: {e}")
            return 0.5

class DatasetFilter:
    """Filters datasets based on quality and compliance criteria"""
    
    def __init__(self, min_quality_score: float = 0.7, require_eu_compliance: bool = True):
        self.min_quality_score = min_quality_score
        self.require_eu_compliance = require_eu_compliance
        self.license_validator = LicenseValidator()
        self.quality_assessor = DatasetQualityAssessment()
    
    async def filter_datasets(self, datasets: List[DatasetMetadata]) -> List[DatasetMetadata]:
        """
        Filter datasets based on quality and compliance criteria
        
        Args:
            datasets: List of dataset metadata to filter
            
        Returns:
            Filtered list of compliant, high-quality datasets
        """
        filtered_datasets = []
        
        for dataset in datasets:
            # Check EU compliance
            if self.require_eu_compliance:
                is_compliant, reason = self.license_validator.validate_license(dataset.license)
                if not is_compliant:
                    logger.info(f"Filtering out {dataset.name}: {reason}")
                    continue
            
            # Check quality score
            quality_score = await self.quality_assessor.assess_quality(dataset)
            dataset.quality_score = quality_score
            
            if quality_score < self.min_quality_score:
                logger.info(f"Filtering out {dataset.name}: Quality score {quality_score:.2f} below threshold {self.min_quality_score}")
                continue
            
            # Check minimum requirements
            if dataset.duration_hours < 1.0:
                logger.info(f"Filtering out {dataset.name}: Duration {dataset.duration_hours} hours too short")
                continue
            
            if dataset.sample_rate < 16000:
                logger.info(f"Filtering out {dataset.name}: Sample rate {dataset.sample_rate} Hz too low")
                continue
            
            filtered_datasets.append(dataset)
            logger.info(f"Approved dataset: {dataset.name} (Quality: {quality_score:.2f})")
        
        return filtered_datasets

class DatasetAgent:
    """Main dataset curation agent"""
    
    def __init__(self, cache_dir: str = "./data/datasets"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.discovery = DatasetDiscovery()
        self.validator = LicenseValidator()
        self.quality_assessor = DatasetQualityAssessment()
        self.filter = DatasetFilter()
        
        self.metadata_cache_file = self.cache_dir / "dataset_metadata.json"
    
    async def discover_and_validate_datasets(self, languages: List[str] = None, force_refresh: bool = False) -> List[DatasetMetadata]:
        """
        Main method to discover, validate, and filter datasets
        
        Args:
            languages: Target languages for discovery
            force_refresh: Force refresh of cached metadata
            
        Returns:
            List of validated, high-quality datasets
        """
        logger.info("Starting dataset discovery and validation")
        
        # Check cache first
        if not force_refresh and self.metadata_cache_file.exists():
            cached_datasets = self._load_cached_metadata()
            if cached_datasets:
                logger.info(f"Loaded {len(cached_datasets)} datasets from cache")
                return cached_datasets
        
        # Discover datasets
        discovered_datasets = await self.discovery.discover_datasets(languages)
        logger.info(f"Discovered {len(discovered_datasets)} datasets")
        
        # Filter and validate
        validated_datasets = await self.filter.filter_datasets(discovered_datasets)
        logger.info(f"Validated {len(validated_datasets)} datasets")
        
        # Cache results
        self._cache_metadata(validated_datasets)
        
        return validated_datasets
    
    def _load_cached_metadata(self) -> List[DatasetMetadata]:
        """Load cached dataset metadata"""
        try:
            with open(self.metadata_cache_file, 'r') as f:
                data = json.load(f)
                return [DatasetMetadata.from_dict(item) for item in data]
        except Exception as e:
            logger.warning(f"Failed to load cached metadata: {e}")
            return []
    
    def _cache_metadata(self, datasets: List[DatasetMetadata]):
        """Cache dataset metadata"""
        try:
            data = [dataset.to_dict() for dataset in datasets]
            with open(self.metadata_cache_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Cached metadata for {len(datasets)} datasets")
        except Exception as e:
            logger.error(f"Failed to cache metadata: {e}")
    
    async def get_dataset_summary(self) -> Dict[str, Any]:
        """Get summary of available datasets"""
        datasets = await self.discover_and_validate_datasets()
        
        summary = {
            'total_datasets': len(datasets),
            'total_duration_hours': sum(d.duration_hours for d in datasets),
            'total_size_gb': sum(d.size_gb for d in datasets),
            'languages': list(set(d.language for d in datasets)),
            'licenses': list(set(d.license for d in datasets)),
            'sources': list(set(d.source for d in datasets)),
            'avg_quality_score': sum(d.quality_score for d in datasets) / len(datasets) if datasets else 0,
            'datasets': [
                {
                    'name': d.name,
                    'language': d.language,
                    'duration_hours': d.duration_hours,
                    'quality_score': d.quality_score,
                    'license': d.license
                }
                for d in datasets
            ]
        }
        
        return summary

# Example usage and testing
async def main():
    """Example usage of the dataset agent"""
    agent = DatasetAgent()
    
    # Discover and validate datasets
    datasets = await agent.discover_and_validate_datasets(['en', 'de', 'fr', 'es'])
    
    print(f"Found {len(datasets)} validated datasets:")
    for dataset in datasets:
        print(f"- {dataset.name}: {dataset.duration_hours:.1f}h, Quality: {dataset.quality_score:.2f}")
    
    # Get summary
    summary = await agent.get_dataset_summary()
    print(f"\nDataset Summary:")
    print(f"Total datasets: {summary['total_datasets']}")
    print(f"Total duration: {summary['total_duration_hours']:.1f} hours")
    print(f"Total size: {summary['total_size_gb']:.1f} GB")
    print(f"Average quality: {summary['avg_quality_score']:.2f}")

if __name__ == "__main__":
    asyncio.run(main())