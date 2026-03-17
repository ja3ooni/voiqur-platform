export enum Region {
  EU_FRANKFURT = 'EU (Frankfurt)',
  ME_BAHRAIN = 'ME (Bahrain)',
  ASIA_MUMBAI = 'Asia (Mumbai)',
  ASIA_SINGAPORE = 'Asia (Singapore)',
  ASIA_TOKYO = 'Asia (Tokyo)',
}

export enum CallStatus {
  ACTIVE = 'Active',
  COMPLETED = 'Completed',
  FAILED = 'Failed',
  QUEUED = 'Queued',
}

export interface LatencyMetric {
  timestamp: string;
  ttfb: number; // Time to first byte
  e2e: number; // End to end latency
  region: Region;
}

export interface SipTrunk {
  id: string;
  name: string;
  provider: string;
  uri: string;
  status: 'Connected' | 'Disconnected' | 'Error';
  region: Region;
}

export interface SimulationStep {
  id: string;
  label: string;
  duration: number; // ms
  status: 'pending' | 'processing' | 'completed' | 'cancelled';
  type: 'vad' | 'stt' | 'llm' | 'tts' | 'network';
}