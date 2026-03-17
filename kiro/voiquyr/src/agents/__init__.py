"""
EUVoice AI Platform - Specialized Agents
"""

# Import existing agents with error handling
try:
    from .stt_agent import STTAgent
except ImportError:
    STTAgent = None

try:
    from .llm_agent import LLMAgent
except Exception:
    LLMAgent = None

try:
    from .tts_agent import TTSAgent
except ImportError:
    TTSAgent = None

try:
    from .emotion_agent import EmotionAgent
except ImportError:
    EmotionAgent = None

try:
    from .accent_agent import AccentAgent
except ImportError:
    AccentAgent = None

try:
    from .lip_sync_agent import LipSyncAgent
except ImportError:
    LipSyncAgent = None

try:
    from .arabic_agent import ArabicAgent
except ImportError:
    ArabicAgent = None

# Import new dataset and training agents
try:
    from .dataset_agent import DatasetAgent, DatasetDiscovery, LicenseValidator, DatasetQualityAssessment, DatasetFilter, DatasetMetadata
except ImportError:
    DatasetAgent = None
    DatasetDiscovery = None
    LicenseValidator = None
    DatasetQualityAssessment = None
    DatasetFilter = None
    DatasetMetadata = None

try:
    from .data_preparation import DataPreparationPipeline, CommonVoicePreprocessor, VoxPopuliPreprocessor, SyntheticDataGenerator, DataAugmentation, PreprocessingConfig, AudioSample
except ImportError:
    DataPreparationPipeline = None
    CommonVoicePreprocessor = None
    VoxPopuliPreprocessor = None
    SyntheticDataGenerator = None
    DataAugmentation = None
    PreprocessingConfig = None
    AudioSample = None

try:
    from .model_training import TrainingPipeline, LoRATrainer, ModelEvaluator, TrainingConfig, ModelMetrics
except ImportError:
    TrainingPipeline = None
    LoRATrainer = None
    ModelEvaluator = None
    TrainingConfig = None
    ModelMetrics = None

__all__ = [
    # Existing agents
    'STTAgent',
    'LLMAgent', 
    'TTSAgent',
    'EmotionAgent',
    'AccentAgent',
    'LipSyncAgent',
    'ArabicAgent',
    # Dataset agents
    'DatasetAgent',
    'DatasetDiscovery',
    'LicenseValidator',
    'DatasetQualityAssessment',
    'DatasetFilter',
    'DatasetMetadata',
    # Data preparation
    'DataPreparationPipeline',
    'CommonVoicePreprocessor',
    'VoxPopuliPreprocessor',
    'SyntheticDataGenerator',
    'DataAugmentation',
    'PreprocessingConfig',
    'AudioSample',
    # Model training
    'TrainingPipeline',
    'LoRATrainer',
    'ModelEvaluator',
    'TrainingConfig',
    'ModelMetrics'
]