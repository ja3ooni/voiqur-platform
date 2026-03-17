"""
Training Data Preparation Pipeline

This module handles preprocessing of various datasets (Granary, Mozilla Common Voice, 
VoxPopuli, MOSEL), synthetic data generation using XTTS-v2, and data augmentation
with noise/accent mixing using CHiME dataset.
"""

import asyncio
import logging
import os
import json
import random
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing as mp

# Optional imports with fallbacks
try:
    import numpy as np
except ImportError:
    np = None

try:
    import torch
    import torchaudio
except ImportError:
    torch = None
    torchaudio = None

try:
    import librosa
except ImportError:
    librosa = None

try:
    from datasets import Dataset, DatasetDict, load_dataset, Audio
except ImportError:
    Dataset = None
    DatasetDict = None
    load_dataset = None
    Audio = None

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    from transformers import AutoTokenizer
except ImportError:
    AutoTokenizer = None

try:
    import soundfile as sf
except ImportError:
    sf = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class AudioSample:
    """Represents a single audio sample with metadata"""
    audio_path: str
    text: str
    language: str
    speaker_id: Optional[str] = None
    duration: float = 0.0
    sample_rate: int = 16000
    dataset_source: str = ""
    quality_score: float = 1.0

@dataclass
class PreprocessingConfig:
    """Configuration for data preprocessing"""
    target_sample_rate: int = 16000
    max_duration: float = 30.0
    min_duration: float = 0.5
    normalize_audio: bool = True
    trim_silence: bool = True
    augment_data: bool = True
    synthetic_data_ratio: float = 0.2
    noise_augmentation_ratio: float = 0.3

class DatasetPreprocessor:
    """Base class for dataset-specific preprocessing"""
    
    def __init__(self, config: PreprocessingConfig):
        self.config = config
        self.target_sr = config.target_sample_rate
    
    def preprocess_audio(self, audio_path: str, target_path: str = None) -> Tuple[np.ndarray, int]:
        """
        Preprocess a single audio file
        
        Args:
            audio_path: Path to input audio file
            target_path: Optional path to save processed audio
            
        Returns:
            Tuple of (processed_audio, sample_rate)
        """
        try:
            # Load audio
            audio, sr = librosa.load(audio_path, sr=None)
            
            # Resample if needed
            if sr != self.target_sr:
                audio = librosa.resample(audio, orig_sr=sr, target_sr=self.target_sr)
                sr = self.target_sr
            
            # Trim silence
            if self.config.trim_silence:
                audio, _ = librosa.effects.trim(audio, top_db=20)
            
            # Normalize
            if self.config.normalize_audio:
                audio = librosa.util.normalize(audio)
            
            # Check duration constraints
            duration = len(audio) / sr
            if duration < self.config.min_duration or duration > self.config.max_duration:
                return None, sr
            
            # Save if target path provided
            if target_path:
                sf.write(target_path, audio, sr)
            
            return audio, sr
            
        except Exception as e:
            logger.error(f"Error preprocessing {audio_path}: {e}")
            return None, 0

class CommonVoicePreprocessor(DatasetPreprocessor):
    """Preprocessor for Mozilla Common Voice dataset"""
    
    async def preprocess_dataset(self, dataset_path: str, output_dir: str, languages: List[str] = None) -> List[AudioSample]:
        """
        Preprocess Mozilla Common Voice dataset
        
        Args:
            dataset_path: Path to Common Voice dataset
            output_dir: Output directory for processed files
            languages: List of target languages
            
        Returns:
            List of processed audio samples
        """
        logger.info("Preprocessing Mozilla Common Voice dataset")
        
        output_path = Path(output_dir) / "common_voice"
        output_path.mkdir(parents=True, exist_ok=True)
        
        processed_samples = []
        
        try:
            # Load dataset from Hugging Face
            if languages is None:
                languages = ['en', 'de', 'fr', 'es', 'it']
            
            for lang in languages:
                logger.info(f"Processing Common Voice for language: {lang}")
                
                try:
                    # Load dataset for specific language
                    dataset = load_dataset("mozilla-foundation/common_voice_17_0", lang, split="train")
                    
                    # Process samples
                    lang_samples = await self._process_common_voice_samples(
                        dataset, output_path / lang, lang
                    )
                    processed_samples.extend(lang_samples)
                    
                except Exception as e:
                    logger.warning(f"Failed to process Common Voice for {lang}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error preprocessing Common Voice: {e}")
        
        logger.info(f"Processed {len(processed_samples)} Common Voice samples")
        return processed_samples
    
    async def _process_common_voice_samples(self, dataset: Dataset, output_dir: Path, language: str) -> List[AudioSample]:
        """Process Common Voice samples for a specific language"""
        output_dir.mkdir(parents=True, exist_ok=True)
        samples = []
        
        # Process in batches to avoid memory issues
        batch_size = 1000
        for i in range(0, len(dataset), batch_size):
            batch = dataset[i:i+batch_size]
            
            for j, item in enumerate(batch):
                try:
                    # Get audio data
                    audio_data = item['audio']
                    text = item['sentence']
                    
                    # Skip if text is too short or long
                    if len(text.strip()) < 10 or len(text.strip()) > 500:
                        continue
                    
                    # Create output filename
                    sample_id = f"{language}_{i+j:06d}"
                    audio_filename = f"{sample_id}.wav"
                    audio_path = output_dir / audio_filename
                    
                    # Process audio
                    processed_audio, sr = self.preprocess_audio(None)  # Will implement direct processing
                    if processed_audio is not None:
                        # Save processed audio
                        sf.write(str(audio_path), processed_audio, sr)
                        
                        # Create sample metadata
                        sample = AudioSample(
                            audio_path=str(audio_path),
                            text=text.strip(),
                            language=language,
                            speaker_id=item.get('client_id', 'unknown'),
                            duration=len(processed_audio) / sr,
                            sample_rate=sr,
                            dataset_source="common_voice",
                            quality_score=0.9
                        )
                        samples.append(sample)
                
                except Exception as e:
                    logger.warning(f"Error processing Common Voice sample {i+j}: {e}")
                    continue
        
        return samples

class VoxPopuliPreprocessor(DatasetPreprocessor):
    """Preprocessor for VoxPopuli dataset"""
    
    async def preprocess_dataset(self, dataset_path: str, output_dir: str, languages: List[str] = None) -> List[AudioSample]:
        """Preprocess VoxPopuli dataset"""
        logger.info("Preprocessing VoxPopuli dataset")
        
        output_path = Path(output_dir) / "voxpopuli"
        output_path.mkdir(parents=True, exist_ok=True)
        
        processed_samples = []
        
        try:
            if languages is None:
                languages = ['en', 'de', 'fr', 'es', 'it', 'pl']
            
            for lang in languages:
                logger.info(f"Processing VoxPopuli for language: {lang}")
                
                try:
                    # Load VoxPopuli dataset
                    dataset = load_dataset("facebook/voxpopuli", lang, split="train")
                    
                    # Process samples
                    lang_samples = await self._process_voxpopuli_samples(
                        dataset, output_path / lang, lang
                    )
                    processed_samples.extend(lang_samples)
                    
                except Exception as e:
                    logger.warning(f"Failed to process VoxPopuli for {lang}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error preprocessing VoxPopuli: {e}")
        
        logger.info(f"Processed {len(processed_samples)} VoxPopuli samples")
        return processed_samples
    
    async def _process_voxpopuli_samples(self, dataset: Dataset, output_dir: Path, language: str) -> List[AudioSample]:
        """Process VoxPopuli samples for a specific language"""
        output_dir.mkdir(parents=True, exist_ok=True)
        samples = []
        
        # Process samples
        for i, item in enumerate(dataset):
            try:
                # Get audio and text
                audio_data = item['audio']
                text = item['normalized_text']
                
                # Skip if text is empty or too short
                if not text or len(text.strip()) < 10:
                    continue
                
                # Create output filename
                sample_id = f"{language}_{i:06d}"
                audio_filename = f"{sample_id}.wav"
                audio_path = output_dir / audio_filename
                
                # Process audio (simplified for now)
                audio_array = np.array(audio_data['array'])
                sr = audio_data['sampling_rate']
                
                # Resample if needed
                if sr != self.target_sr:
                    audio_array = librosa.resample(audio_array, orig_sr=sr, target_sr=self.target_sr)
                    sr = self.target_sr
                
                # Apply preprocessing
                if self.config.normalize_audio:
                    audio_array = librosa.util.normalize(audio_array)
                
                # Check duration
                duration = len(audio_array) / sr
                if duration < self.config.min_duration or duration > self.config.max_duration:
                    continue
                
                # Save processed audio
                sf.write(str(audio_path), audio_array, sr)
                
                # Create sample metadata
                sample = AudioSample(
                    audio_path=str(audio_path),
                    text=text.strip(),
                    language=language,
                    speaker_id=item.get('speaker_id', 'unknown'),
                    duration=duration,
                    sample_rate=sr,
                    dataset_source="voxpopuli",
                    quality_score=0.95
                )
                samples.append(sample)
                
                # Limit processing for demo
                if len(samples) >= 1000:
                    break
            
            except Exception as e:
                logger.warning(f"Error processing VoxPopuli sample {i}: {e}")
                continue
        
        return samples

class SyntheticDataGenerator:
    """Generates synthetic training data using XTTS-v2 on EuroParl text"""
    
    def __init__(self, config: PreprocessingConfig):
        self.config = config
        self.europarl_texts = {}
        
    async def generate_synthetic_data(self, output_dir: str, num_samples: int = 10000, languages: List[str] = None) -> List[AudioSample]:
        """
        Generate synthetic speech data using XTTS-v2
        
        Args:
            output_dir: Output directory for synthetic audio
            num_samples: Number of synthetic samples to generate
            languages: Target languages
            
        Returns:
            List of synthetic audio samples
        """
        logger.info(f"Generating {num_samples} synthetic audio samples")
        
        output_path = Path(output_dir) / "synthetic"
        output_path.mkdir(parents=True, exist_ok=True)
        
        if languages is None:
            languages = ['en', 'de', 'fr', 'es', 'it']
        
        # Load EuroParl texts
        await self._load_europarl_texts(languages)
        
        synthetic_samples = []
        
        # Generate samples for each language
        samples_per_lang = num_samples // len(languages)
        
        for lang in languages:
            logger.info(f"Generating synthetic data for {lang}")
            
            lang_samples = await self._generate_language_samples(
                lang, samples_per_lang, output_path / lang
            )
            synthetic_samples.extend(lang_samples)
        
        logger.info(f"Generated {len(synthetic_samples)} synthetic samples")
        return synthetic_samples
    
    async def _load_europarl_texts(self, languages: List[str]):
        """Load EuroParl text corpus for each language"""
        for lang in languages:
            try:
                # This would load actual EuroParl corpus
                # For now, use sample texts
                self.europarl_texts[lang] = [
                    "The European Parliament is committed to multilingual democracy.",
                    "We must ensure that all citizens can participate in European democracy.",
                    "Digital transformation requires inclusive policies for all Europeans.",
                    "Climate change is one of the greatest challenges of our time.",
                    "Education and research are fundamental pillars of European society."
                ] * 100  # Repeat for more samples
                
                logger.info(f"Loaded {len(self.europarl_texts[lang])} texts for {lang}")
                
            except Exception as e:
                logger.error(f"Failed to load EuroParl texts for {lang}: {e}")
                self.europarl_texts[lang] = []
    
    async def _generate_language_samples(self, language: str, num_samples: int, output_dir: Path) -> List[AudioSample]:
        """Generate synthetic samples for a specific language"""
        output_dir.mkdir(parents=True, exist_ok=True)
        samples = []
        
        texts = self.europarl_texts.get(language, [])
        if not texts:
            logger.warning(f"No texts available for {language}")
            return samples
        
        for i in range(num_samples):
            try:
                # Select random text
                text = random.choice(texts)
                
                # Generate synthetic audio (mock implementation)
                # In real implementation, this would use XTTS-v2
                synthetic_audio = await self._synthesize_speech(text, language)
                
                if synthetic_audio is not None:
                    # Save synthetic audio
                    sample_id = f"synthetic_{language}_{i:06d}"
                    audio_filename = f"{sample_id}.wav"
                    audio_path = output_dir / audio_filename
                    
                    sf.write(str(audio_path), synthetic_audio, self.config.target_sample_rate)
                    
                    # Create sample metadata
                    sample = AudioSample(
                        audio_path=str(audio_path),
                        text=text,
                        language=language,
                        speaker_id=f"synthetic_speaker_{i % 10}",
                        duration=len(synthetic_audio) / self.config.target_sample_rate,
                        sample_rate=self.config.target_sample_rate,
                        dataset_source="synthetic_xtts",
                        quality_score=0.85
                    )
                    samples.append(sample)
            
            except Exception as e:
                logger.warning(f"Error generating synthetic sample {i} for {language}: {e}")
                continue
        
        return samples
    
    async def _synthesize_speech(self, text: str, language: str) -> Optional[np.ndarray]:
        """
        Synthesize speech using XTTS-v2 (mock implementation)
        
        In real implementation, this would:
        1. Load XTTS-v2 model
        2. Generate speech from text
        3. Return audio array
        """
        try:
            # Mock synthetic audio generation
            duration = len(text.split()) * 0.5  # Rough estimate
            num_samples = int(duration * self.config.target_sample_rate)
            
            # Generate simple sine wave as placeholder
            t = np.linspace(0, duration, num_samples)
            frequency = 440 + hash(text) % 200  # Vary frequency based on text
            synthetic_audio = 0.1 * np.sin(2 * np.pi * frequency * t)
            
            # Add some noise for realism
            noise = np.random.normal(0, 0.01, num_samples)
            synthetic_audio += noise
            
            return synthetic_audio.astype(np.float32)
            
        except Exception as e:
            logger.error(f"Error synthesizing speech: {e}")
            return None

class DataAugmentation:
    """Handles data augmentation with noise and accent mixing"""
    
    def __init__(self, config: PreprocessingConfig, chime_dataset_path: str = None):
        self.config = config
        self.chime_path = chime_dataset_path
        self.noise_samples = []
        
    async def load_noise_samples(self):
        """Load noise samples from CHiME dataset"""
        if not self.chime_path or not os.path.exists(self.chime_path):
            logger.warning("CHiME dataset path not available, using synthetic noise")
            return
        
        try:
            # Load noise samples from CHiME dataset
            noise_dir = Path(self.chime_path) / "noise"
            if noise_dir.exists():
                for noise_file in noise_dir.glob("*.wav"):
                    try:
                        noise_audio, sr = librosa.load(str(noise_file), sr=self.config.target_sample_rate)
                        self.noise_samples.append(noise_audio)
                    except Exception as e:
                        logger.warning(f"Failed to load noise file {noise_file}: {e}")
            
            logger.info(f"Loaded {len(self.noise_samples)} noise samples")
            
        except Exception as e:
            logger.error(f"Error loading CHiME noise samples: {e}")
    
    async def augment_samples(self, samples: List[AudioSample], output_dir: str) -> List[AudioSample]:
        """
        Apply data augmentation to samples
        
        Args:
            samples: Original audio samples
            output_dir: Output directory for augmented samples
            
        Returns:
            List including original and augmented samples
        """
        logger.info(f"Augmenting {len(samples)} samples")
        
        output_path = Path(output_dir) / "augmented"
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Load noise samples if not already loaded
        if not self.noise_samples:
            await self.load_noise_samples()
        
        augmented_samples = list(samples)  # Start with original samples
        
        # Apply augmentation to a subset of samples
        num_to_augment = int(len(samples) * self.config.noise_augmentation_ratio)
        samples_to_augment = random.sample(samples, min(num_to_augment, len(samples)))
        
        for i, sample in enumerate(samples_to_augment):
            try:
                # Load original audio
                audio, sr = librosa.load(sample.audio_path, sr=self.config.target_sample_rate)
                
                # Apply various augmentations
                augmented_variants = []
                
                # 1. Add noise
                if self.noise_samples:
                    noisy_audio = self._add_noise(audio, random.choice(self.noise_samples))
                    augmented_variants.append(("noise", noisy_audio))
                
                # 2. Speed perturbation
                speed_factor = random.uniform(0.9, 1.1)
                speed_audio = librosa.effects.time_stretch(audio, rate=speed_factor)
                augmented_variants.append(("speed", speed_audio))
                
                # 3. Pitch shift
                pitch_shift = random.uniform(-2, 2)
                pitch_audio = librosa.effects.pitch_shift(audio, sr=sr, n_steps=pitch_shift)
                augmented_variants.append(("pitch", pitch_audio))
                
                # 4. Volume perturbation
                volume_factor = random.uniform(0.7, 1.3)
                volume_audio = audio * volume_factor
                augmented_variants.append(("volume", volume_audio))
                
                # Save augmented variants
                for aug_type, aug_audio in augmented_variants:
                    aug_filename = f"aug_{aug_type}_{i:06d}.wav"
                    aug_path = output_path / aug_filename
                    
                    sf.write(str(aug_path), aug_audio, sr)
                    
                    # Create augmented sample metadata
                    aug_sample = AudioSample(
                        audio_path=str(aug_path),
                        text=sample.text,
                        language=sample.language,
                        speaker_id=sample.speaker_id,
                        duration=len(aug_audio) / sr,
                        sample_rate=sr,
                        dataset_source=f"{sample.dataset_source}_aug_{aug_type}",
                        quality_score=sample.quality_score * 0.9  # Slightly lower quality
                    )
                    augmented_samples.append(aug_sample)
            
            except Exception as e:
                logger.warning(f"Error augmenting sample {i}: {e}")
                continue
        
        logger.info(f"Created {len(augmented_samples) - len(samples)} augmented samples")
        return augmented_samples
    
    def _add_noise(self, audio: np.ndarray, noise: np.ndarray, snr_db: float = None) -> np.ndarray:
        """Add noise to audio with specified SNR"""
        if snr_db is None:
            snr_db = random.uniform(10, 30)  # Random SNR between 10-30 dB
        
        # Ensure noise is same length as audio
        if len(noise) > len(audio):
            start_idx = random.randint(0, len(noise) - len(audio))
            noise = noise[start_idx:start_idx + len(audio)]
        elif len(noise) < len(audio):
            # Repeat noise to match audio length
            repeats = (len(audio) // len(noise)) + 1
            noise = np.tile(noise, repeats)[:len(audio)]
        
        # Calculate noise scaling factor for desired SNR
        signal_power = np.mean(audio ** 2)
        noise_power = np.mean(noise ** 2)
        
        if noise_power > 0:
            snr_linear = 10 ** (snr_db / 10)
            noise_scale = np.sqrt(signal_power / (snr_linear * noise_power))
            scaled_noise = noise * noise_scale
        else:
            scaled_noise = noise
        
        return audio + scaled_noise

class DataPreparationPipeline:
    """Main pipeline for training data preparation"""
    
    def __init__(self, config: PreprocessingConfig = None, cache_dir: str = "./data/prepared"):
        self.config = config or PreprocessingConfig()
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize processors
        self.common_voice_processor = CommonVoicePreprocessor(self.config)
        self.voxpopuli_processor = VoxPopuliPreprocessor(self.config)
        self.synthetic_generator = SyntheticDataGenerator(self.config)
        self.augmentation = DataAugmentation(self.config)
    
    async def prepare_training_data(self, 
                                   languages: List[str] = None,
                                   include_synthetic: bool = True,
                                   include_augmentation: bool = True) -> Dict[str, List[AudioSample]]:
        """
        Main method to prepare all training data
        
        Args:
            languages: Target languages
            include_synthetic: Whether to generate synthetic data
            include_augmentation: Whether to apply data augmentation
            
        Returns:
            Dictionary mapping dataset types to sample lists
        """
        logger.info("Starting training data preparation pipeline")
        
        if languages is None:
            languages = ['en', 'de', 'fr', 'es', 'it']
        
        all_samples = {}
        
        # 1. Process Common Voice
        logger.info("Processing Mozilla Common Voice dataset")
        cv_samples = await self.common_voice_processor.preprocess_dataset(
            "", str(self.cache_dir), languages
        )
        all_samples['common_voice'] = cv_samples
        
        # 2. Process VoxPopuli
        logger.info("Processing VoxPopuli dataset")
        vp_samples = await self.voxpopuli_processor.preprocess_dataset(
            "", str(self.cache_dir), languages
        )
        all_samples['voxpopuli'] = vp_samples
        
        # 3. Generate synthetic data
        if include_synthetic:
            logger.info("Generating synthetic data")
            num_synthetic = int(len(cv_samples + vp_samples) * self.config.synthetic_data_ratio)
            synthetic_samples = await self.synthetic_generator.generate_synthetic_data(
                str(self.cache_dir), num_synthetic, languages
            )
            all_samples['synthetic'] = synthetic_samples
        
        # 4. Apply data augmentation
        if include_augmentation:
            logger.info("Applying data augmentation")
            all_original_samples = []
            for samples in all_samples.values():
                all_original_samples.extend(samples)
            
            augmented_samples = await self.augmentation.augment_samples(
                all_original_samples, str(self.cache_dir)
            )
            all_samples['augmented'] = augmented_samples
        
        # 5. Save metadata
        await self._save_preparation_metadata(all_samples)
        
        # 6. Generate summary
        summary = self._generate_summary(all_samples)
        logger.info(f"Data preparation complete: {summary}")
        
        return all_samples
    
    async def _save_preparation_metadata(self, all_samples: Dict[str, List[AudioSample]]):
        """Save metadata for prepared samples"""
        metadata_file = self.cache_dir / "preparation_metadata.json"
        
        metadata = {
            'preparation_date': datetime.now().isoformat(),
            'config': {
                'target_sample_rate': self.config.target_sample_rate,
                'max_duration': self.config.max_duration,
                'min_duration': self.config.min_duration,
                'synthetic_data_ratio': self.config.synthetic_data_ratio,
                'noise_augmentation_ratio': self.config.noise_augmentation_ratio
            },
            'datasets': {}
        }
        
        for dataset_type, samples in all_samples.items():
            metadata['datasets'][dataset_type] = {
                'num_samples': len(samples),
                'total_duration': sum(s.duration for s in samples),
                'languages': list(set(s.language for s in samples)),
                'avg_quality_score': sum(s.quality_score for s in samples) / len(samples) if samples else 0
            }
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Saved preparation metadata to {metadata_file}")
    
    def _generate_summary(self, all_samples: Dict[str, List[AudioSample]]) -> str:
        """Generate summary of prepared data"""
        total_samples = sum(len(samples) for samples in all_samples.values())
        total_duration = sum(sum(s.duration for s in samples) for samples in all_samples.values())
        
        summary_parts = [f"{total_samples} total samples", f"{total_duration:.1f} hours"]
        
        for dataset_type, samples in all_samples.items():
            if samples:
                summary_parts.append(f"{len(samples)} {dataset_type}")
        
        return ", ".join(summary_parts)

# Example usage
async def main():
    """Example usage of the data preparation pipeline"""
    config = PreprocessingConfig(
        target_sample_rate=16000,
        max_duration=20.0,
        min_duration=1.0,
        synthetic_data_ratio=0.1,
        noise_augmentation_ratio=0.2
    )
    
    pipeline = DataPreparationPipeline(config)
    
    # Prepare training data
    prepared_data = await pipeline.prepare_training_data(
        languages=['en', 'de', 'fr'],
        include_synthetic=True,
        include_augmentation=True
    )
    
    # Print summary
    for dataset_type, samples in prepared_data.items():
        print(f"{dataset_type}: {len(samples)} samples")
        if samples:
            total_duration = sum(s.duration for s in samples)
            avg_quality = sum(s.quality_score for s in samples) / len(samples)
            print(f"  Duration: {total_duration:.1f}h, Avg Quality: {avg_quality:.2f}")

if __name__ == "__main__":
    import datetime
    asyncio.run(main())