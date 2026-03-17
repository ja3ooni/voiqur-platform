import React from 'react';
import { render, screen } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import analyticsReducer from '../../store/slices/analyticsSlice';
import configurationReducer from '../../store/slices/configurationSlice';
import audioStreamReducer from '../../store/slices/audioStreamSlice';
import AnalyticsDashboard from './AnalyticsDashboard';
import SystemHealthPanel from './SystemHealthPanel';

// Mock store with initial state
const createMockStore = () => {
  return configureStore({
    reducer: {
      analytics: analyticsReducer,
      configuration: configurationReducer,
      audioStream: audioStreamReducer,
    },
  });
};

describe('Analytics Components', () => {
  let store: ReturnType<typeof createMockStore>;

  beforeEach(() => {
    store = createMockStore();
  });

  test('renders AnalyticsDashboard without crashing', () => {
    render(
      <Provider store={store}>
        <AnalyticsDashboard />
      </Provider>
    );
    
    expect(screen.getByText('Analytics & Monitoring')).toBeInTheDocument();
    expect(screen.getByText('Performance Metrics')).toBeInTheDocument();
    expect(screen.getByText('User Analytics')).toBeInTheDocument();
    expect(screen.getByText('System Health')).toBeInTheDocument();
  });



  test('renders SystemHealthPanel with default data', () => {
    render(
      <Provider store={store}>
        <SystemHealthPanel />
      </Provider>
    );
    
    expect(screen.getByText('System Health & Monitoring')).toBeInTheDocument();
    expect(screen.getByText('Service Status')).toBeInTheDocument();
    expect(screen.getByText('Resource Usage')).toBeInTheDocument();
    expect(screen.getByText('System Alerts')).toBeInTheDocument();
  });
});