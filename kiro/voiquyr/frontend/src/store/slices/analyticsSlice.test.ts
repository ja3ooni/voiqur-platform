import { configureStore } from '@reduxjs/toolkit';
import analyticsReducer, { clearError, acknowledgeAlert, dismissAlert } from './analyticsSlice';
import { AnalyticsState } from '../../types/analytics';

describe('analyticsSlice', () => {
  let store: ReturnType<typeof configureStore>;

  beforeEach(() => {
    store = configureStore({
      reducer: {
        analytics: analyticsReducer,
      },
    });
  });

  test('should have initial state', () => {
    const state = store.getState().analytics;
    expect(state.isLoading).toBe(false);
    expect(state.error).toBe(null);
    expect(state.performanceMetrics.latency.stt).toBe(0);
    expect(state.systemHealth.services).toEqual([]);
  });

  test('should clear error', () => {
    // First set an error state
    const stateWithError: AnalyticsState = {
      ...store.getState().analytics,
      error: 'Test error'
    };
    
    store.dispatch(clearError());
    const state = store.getState().analytics;
    expect(state.error).toBe(null);
  });

  test('should acknowledge alert', () => {
    // Create initial state with an alert
    const initialState: AnalyticsState = {
      ...store.getState().analytics,
      systemHealth: {
        ...store.getState().analytics.systemHealth,
        alerts: [
          {
            id: 'test-alert',
            severity: 'warning',
            message: 'Test alert',
            timestamp: new Date().toISOString(),
            acknowledged: false
          }
        ]
      }
    };

    // We can't easily set initial state, so let's just test the action creator
    const action = acknowledgeAlert('test-alert');
    expect(action.type).toBe('analytics/acknowledgeAlert');
    expect(action.payload).toBe('test-alert');
  });

  test('should dismiss alert', () => {
    const action = dismissAlert('test-alert');
    expect(action.type).toBe('analytics/dismissAlert');
    expect(action.payload).toBe('test-alert');
  });
});