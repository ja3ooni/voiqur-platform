export interface PerformanceMetrics {
  latency: {
    stt: number; // STT processing latency in ms
    llm: number; // LLM response latency in ms
    tts: number; // TTS synthesis latency in ms
    endToEnd: number; // Total pipeline latency in ms
  };
  accuracy: {
    sttAccuracy: number; // STT transcription accuracy (0-1)
    intentRecognition: number; // Intent recognition accuracy (0-1)
    emotionDetection: number; // Emotion detection accuracy (0-1)
    accentDetection: number; // Accent detection accuracy (0-1)
  };
  usage: {
    totalSessions: number;
    activeSessions: number;
    totalRequests: number;
    requestsPerMinute: number;
    averageSessionDuration: number; // in seconds
  };
}

export interface UserAnalytics {
  conversationInsights: {
    totalConversations: number;
    averageConversationLength: number; // in turns
    mostUsedLanguages: Array<{ language: string; count: number }>;
    emotionDistribution: Array<{ emotion: string; percentage: number }>;
    intentDistribution: Array<{ intent: string; count: number }>;
  };
  userBehavior: {
    peakUsageHours: Array<{ hour: number; usage: number }>;
    sessionDuration: Array<{ duration: number; count: number }>;
    dropoffPoints: Array<{ step: string; dropoffRate: number }>;
  };
}

export interface SystemHealth {
  services: Array<{
    name: string;
    status: 'healthy' | 'warning' | 'critical' | 'down';
    uptime: number; // in seconds
    responseTime: number; // in ms
    errorRate: number; // percentage
    lastCheck: string; // ISO timestamp
  }>;
  resources: {
    cpu: { usage: number; available: number };
    memory: { usage: number; available: number };
    gpu: { usage: number; available: number };
    storage: { usage: number; available: number };
  };
  alerts: Array<{
    id: string;
    severity: 'info' | 'warning' | 'error' | 'critical';
    message: string;
    timestamp: string;
    acknowledged: boolean;
    service?: string;
  }>;
}

export interface AnalyticsState {
  performanceMetrics: PerformanceMetrics;
  userAnalytics: UserAnalytics;
  systemHealth: SystemHealth;
  isLoading: boolean;
  error: string | null;
  lastUpdated: string | null;
}

export interface MetricDataPoint {
  timestamp: string;
  value: number;
}

export interface TimeSeriesData {
  label: string;
  data: MetricDataPoint[];
  color?: string;
}