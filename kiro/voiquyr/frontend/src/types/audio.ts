// Real-time Audio Processing Types

export interface AudioStreamConfig {
  sampleRate: number;
  channels: number;
  bitDepth: number;
  bufferSize: number;
}

export interface TranscriptionResult {
  text: string;
  confidence: number;
  isFinal: boolean;
  timestamp: number;
  language?: string;
  words?: WordResult[];
}

export interface WordResult {
  word: string;
  confidence: number;
  startTime: number;
  endTime: number;
}

export interface AudioVisualizationData {
  frequencyData: Uint8Array;
  waveformData: Float32Array;
  volume: number;
  timestamp: number;
}

export interface WebSocketMessage {
  type: 'audio' | 'transcription' | 'error' | 'config' | 'status' | 'heartbeat' | 'metrics';
  data: any;
  timestamp: number;
  messageId?: string;
  sequenceNumber?: number;
}

export interface AudioStreamState {
  isRecording: boolean;
  isConnected: boolean;
  isProcessing: boolean;
  currentTranscription: string;
  transcriptionHistory: TranscriptionResult[];
  audioConfig: AudioStreamConfig;
  visualizationData: AudioVisualizationData | null;
  error: string | null;
  latency: number;
}

export interface AudioStreamActions {
  startRecording: () => void;
  stopRecording: () => void;
  connect: () => void;
  disconnect: () => void;
  clearTranscription: () => void;
  updateConfig: (config: Partial<AudioStreamConfig>) => void;
}

export interface StreamMetrics {
  packetsReceived: number;
  packetsLost: number;
  averageLatency: number;
  dataRate: number;
  connectionUptime: number;
  lastPacketTime: number;
  jitter: number;
  bufferHealth: number;
}

export interface AudioQualityMetrics {
  signalToNoiseRatio: number;
  volumeLevel: number;
  clippingDetected: boolean;
  backgroundNoiseLevel: number;
  speechDetected: boolean;
}

export interface RealTimeProcessingConfig {
  enableVAD: boolean; // Voice Activity Detection
  noiseReduction: boolean;
  echoCancellation: boolean;
  autoGainControl: boolean;
  adaptiveFiltering: boolean;
  realTimeTranscription: boolean;
  partialResults: boolean;
  confidenceThreshold: number;
}