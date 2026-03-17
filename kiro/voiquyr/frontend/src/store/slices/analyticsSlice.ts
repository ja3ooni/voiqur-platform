import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { AnalyticsState, PerformanceMetrics, UserAnalytics, SystemHealth } from '../../types/analytics';

// Mock API calls - replace with actual API endpoints
export const fetchPerformanceMetrics = createAsyncThunk(
  'analytics/fetchPerformanceMetrics',
  async () => {
    // Simulate API call with mock data
    await new Promise(resolve => setTimeout(resolve, 500));
    
    const mockMetrics: PerformanceMetrics = {
      latency: {
        stt: 45,
        llm: 120,
        tts: 80,
        endToEnd: 245
      },
      accuracy: {
        sttAccuracy: 0.94,
        intentRecognition: 0.89,
        emotionDetection: 0.87,
        accentDetection: 0.91
      },
      usage: {
        totalSessions: 1247,
        activeSessions: 23,
        totalRequests: 15678,
        requestsPerMinute: 45,
        averageSessionDuration: 180
      }
    };
    
    return mockMetrics;
  }
);

export const fetchUserAnalytics = createAsyncThunk(
  'analytics/fetchUserAnalytics',
  async () => {
    await new Promise(resolve => setTimeout(resolve, 300));
    
    const mockAnalytics: UserAnalytics = {
      conversationInsights: {
        totalConversations: 892,
        averageConversationLength: 8.5,
        mostUsedLanguages: [
          { language: 'English', count: 456 },
          { language: 'French', count: 234 },
          { language: 'German', count: 123 },
          { language: 'Spanish', count: 79 }
        ],
        emotionDistribution: [
          { emotion: 'Neutral', percentage: 45 },
          { emotion: 'Happy', percentage: 25 },
          { emotion: 'Frustrated', percentage: 15 },
          { emotion: 'Excited', percentage: 10 },
          { emotion: 'Sad', percentage: 5 }
        ],
        intentDistribution: [
          { intent: 'Information Request', count: 345 },
          { intent: 'Task Completion', count: 267 },
          { intent: 'Support', count: 189 },
          { intent: 'Casual Chat', count: 91 }
        ]
      },
      userBehavior: {
        peakUsageHours: Array.from({ length: 24 }, (_, i) => ({
          hour: i,
          usage: Math.floor(Math.random() * 100) + 10
        })),
        sessionDuration: [
          { duration: 30, count: 123 },
          { duration: 60, count: 234 },
          { duration: 120, count: 345 },
          { duration: 300, count: 189 },
          { duration: 600, count: 67 }
        ],
        dropoffPoints: [
          { step: 'Initial Connection', dropoffRate: 5 },
          { step: 'Voice Recognition', dropoffRate: 12 },
          { step: 'Intent Processing', dropoffRate: 8 },
          { step: 'Response Generation', dropoffRate: 3 }
        ]
      }
    };
    
    return mockAnalytics;
  }
);

export const fetchSystemHealth = createAsyncThunk(
  'analytics/fetchSystemHealth',
  async () => {
    await new Promise(resolve => setTimeout(resolve, 200));
    
    const mockHealth: SystemHealth = {
      services: [
        {
          name: 'STT Service',
          status: 'healthy',
          uptime: 86400,
          responseTime: 45,
          errorRate: 0.2,
          lastCheck: new Date().toISOString()
        },
        {
          name: 'LLM Service',
          status: 'healthy',
          uptime: 86400,
          responseTime: 120,
          errorRate: 0.5,
          lastCheck: new Date().toISOString()
        },
        {
          name: 'TTS Service',
          status: 'warning',
          uptime: 82800,
          responseTime: 95,
          errorRate: 2.1,
          lastCheck: new Date().toISOString()
        },
        {
          name: 'Emotion Detection',
          status: 'healthy',
          uptime: 86400,
          responseTime: 35,
          errorRate: 0.8,
          lastCheck: new Date().toISOString()
        },
        {
          name: 'Accent Recognition',
          status: 'healthy',
          uptime: 86400,
          responseTime: 28,
          errorRate: 1.2,
          lastCheck: new Date().toISOString()
        }
      ],
      resources: {
        cpu: { usage: 65, available: 100 },
        memory: { usage: 78, available: 100 },
        gpu: { usage: 82, available: 100 },
        storage: { usage: 45, available: 100 }
      },
      alerts: [
        {
          id: '1',
          severity: 'warning',
          message: 'TTS Service response time above threshold (95ms > 90ms)',
          timestamp: new Date(Date.now() - 300000).toISOString(),
          acknowledged: false,
          service: 'TTS Service'
        },
        {
          id: '2',
          severity: 'info',
          message: 'GPU utilization high but within normal range (82%)',
          timestamp: new Date(Date.now() - 600000).toISOString(),
          acknowledged: true,
          service: 'System Resources'
        }
      ]
    };
    
    return mockHealth;
  }
);

const initialState: AnalyticsState = {
  performanceMetrics: {
    latency: { stt: 0, llm: 0, tts: 0, endToEnd: 0 },
    accuracy: { sttAccuracy: 0, intentRecognition: 0, emotionDetection: 0, accentDetection: 0 },
    usage: { totalSessions: 0, activeSessions: 0, totalRequests: 0, requestsPerMinute: 0, averageSessionDuration: 0 }
  },
  userAnalytics: {
    conversationInsights: {
      totalConversations: 0,
      averageConversationLength: 0,
      mostUsedLanguages: [],
      emotionDistribution: [],
      intentDistribution: []
    },
    userBehavior: {
      peakUsageHours: [],
      sessionDuration: [],
      dropoffPoints: []
    }
  },
  systemHealth: {
    services: [],
    resources: {
      cpu: { usage: 0, available: 100 },
      memory: { usage: 0, available: 100 },
      gpu: { usage: 0, available: 100 },
      storage: { usage: 0, available: 100 }
    },
    alerts: []
  },
  isLoading: false,
  error: null,
  lastUpdated: null
};

const analyticsSlice = createSlice({
  name: 'analytics',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    acknowledgeAlert: (state, action: PayloadAction<string>) => {
      const alert = state.systemHealth.alerts.find(a => a.id === action.payload);
      if (alert) {
        alert.acknowledged = true;
      }
    },
    dismissAlert: (state, action: PayloadAction<string>) => {
      state.systemHealth.alerts = state.systemHealth.alerts.filter(a => a.id !== action.payload);
    }
  },
  extraReducers: (builder) => {
    builder
      // Performance Metrics
      .addCase(fetchPerformanceMetrics.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchPerformanceMetrics.fulfilled, (state, action) => {
        state.isLoading = false;
        state.performanceMetrics = action.payload;
        state.lastUpdated = new Date().toISOString();
      })
      .addCase(fetchPerformanceMetrics.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.error.message || 'Failed to fetch performance metrics';
      })
      
      // User Analytics
      .addCase(fetchUserAnalytics.pending, (state) => {
        state.isLoading = true;
      })
      .addCase(fetchUserAnalytics.fulfilled, (state, action) => {
        state.isLoading = false;
        state.userAnalytics = action.payload;
        state.lastUpdated = new Date().toISOString();
      })
      .addCase(fetchUserAnalytics.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.error.message || 'Failed to fetch user analytics';
      })
      
      // System Health
      .addCase(fetchSystemHealth.pending, (state) => {
        state.isLoading = true;
      })
      .addCase(fetchSystemHealth.fulfilled, (state, action) => {
        state.isLoading = false;
        state.systemHealth = action.payload;
        state.lastUpdated = new Date().toISOString();
      })
      .addCase(fetchSystemHealth.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.error.message || 'Failed to fetch system health';
      });
  }
});

export const { clearError, acknowledgeAlert, dismissAlert } = analyticsSlice.actions;
export default analyticsSlice.reducer;