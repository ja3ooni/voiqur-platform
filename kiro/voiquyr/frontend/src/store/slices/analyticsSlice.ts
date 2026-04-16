import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { AnalyticsState, PerformanceMetrics, UserAnalytics, SystemHealth } from '../../types/analytics';

const API = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

const authHeader = () => {
  const token = localStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export const fetchPerformanceMetrics = createAsyncThunk(
  'analytics/fetchPerformanceMetrics',
  async (_, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API}/v1/health/detailed`, { headers: authHeader() });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      // Map health endpoint to PerformanceMetrics shape
      return {
        latency: { stt: 0, llm: 0, tts: 0, endToEnd: 0 },
        accuracy: { sttAccuracy: 0, intentRecognition: 0, emotionDetection: 0, accentDetection: 0 },
        usage: {
          totalSessions: 0,
          activeSessions: 0,
          totalRequests: 0,
          requestsPerMinute: 0,
          averageSessionDuration: 0,
        },
        uptime: data.uptime ?? 0,
        cpuUsage: data.performance?.cpu_usage_percent ?? 0,
        memoryUsage: data.performance?.memory_usage_percent ?? 0,
      } as unknown as PerformanceMetrics;
    } catch (e: any) {
      return rejectWithValue(e.message);
    }
  }
);

export const fetchUserAnalytics = createAsyncThunk(
  'analytics/fetchUserAnalytics',
  async (_, { rejectWithValue }) => {
    // No dedicated analytics endpoint yet — return empty shape
    // Will be wired to /api/v1/analytics/ when that router is added
    return {
      conversationInsights: {
        totalConversations: 0,
        averageConversationLength: 0,
        mostUsedLanguages: [],
        emotionDistribution: [],
        intentDistribution: [],
      },
      userBehavior: {
        peakUsageHours: [],
        sessionDuration: [],
        dropoffPoints: [],
      },
    } as UserAnalytics;
  }
);

export const fetchSystemHealth = createAsyncThunk(
  'analytics/fetchSystemHealth',
  async (_, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API}/v1/health/detailed`, { headers: authHeader() });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      return {
        services: Object.entries(data.services ?? {}).map(([name, status]) => ({
          name,
          status: status as string,
          uptime: data.uptime ?? 0,
          responseTime: 0,
          errorRate: 0,
          lastCheck: new Date().toISOString(),
        })),
        resources: {
          cpu: { usage: data.performance?.cpu_usage_percent ?? 0, available: 100 },
          memory: { usage: data.performance?.memory_usage_percent ?? 0, available: 100 },
          gpu: { usage: 0, available: 100 },
          storage: { usage: data.performance?.disk_usage_percent ?? 0, available: 100 },
        },
        alerts: [],
      } as SystemHealth;
    } catch (e: any) {
      return rejectWithValue(e.message);
    }
  }
);

const initialState: AnalyticsState = {
  performanceMetrics: {
    latency: { stt: 0, llm: 0, tts: 0, endToEnd: 0 },
    accuracy: { sttAccuracy: 0, intentRecognition: 0, emotionDetection: 0, accentDetection: 0 },
    usage: { totalSessions: 0, activeSessions: 0, totalRequests: 0, requestsPerMinute: 0, averageSessionDuration: 0 },
  },
  userAnalytics: {
    conversationInsights: {
      totalConversations: 0,
      averageConversationLength: 0,
      mostUsedLanguages: [],
      emotionDistribution: [],
      intentDistribution: [],
    },
    userBehavior: { peakUsageHours: [], sessionDuration: [], dropoffPoints: [] },
  },
  systemHealth: {
    services: [],
    resources: {
      cpu: { usage: 0, available: 100 },
      memory: { usage: 0, available: 100 },
      gpu: { usage: 0, available: 100 },
      storage: { usage: 0, available: 100 },
    },
    alerts: [],
  },
  isLoading: false,
  error: null,
  lastUpdated: null,
};

const analyticsSlice = createSlice({
  name: 'analytics',
  initialState,
  reducers: {
    clearError: (state) => { state.error = null; },
    acknowledgeAlert: (state, action: PayloadAction<string>) => {
      const alert = state.systemHealth.alerts.find(a => a.id === action.payload);
      if (alert) alert.acknowledged = true;
    },
    dismissAlert: (state, action: PayloadAction<string>) => {
      state.systemHealth.alerts = state.systemHealth.alerts.filter(a => a.id !== action.payload);
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchPerformanceMetrics.pending, (state) => { state.isLoading = true; state.error = null; })
      .addCase(fetchPerformanceMetrics.fulfilled, (state, action) => {
        state.isLoading = false;
        state.performanceMetrics = action.payload;
        state.lastUpdated = new Date().toISOString();
      })
      .addCase(fetchPerformanceMetrics.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string || 'Failed to fetch metrics';
      })
      .addCase(fetchUserAnalytics.fulfilled, (state, action) => {
        state.userAnalytics = action.payload;
      })
      .addCase(fetchSystemHealth.pending, (state) => { state.isLoading = true; })
      .addCase(fetchSystemHealth.fulfilled, (state, action) => {
        state.isLoading = false;
        state.systemHealth = action.payload;
        state.lastUpdated = new Date().toISOString();
      })
      .addCase(fetchSystemHealth.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload as string || 'Failed to fetch health';
      });
  },
});

export const { clearError, acknowledgeAlert, dismissAlert } = analyticsSlice.actions;
export default analyticsSlice.reducer;
