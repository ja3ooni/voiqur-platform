import React from 'react';
import { render, screen } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import audioStreamReducer from '../../store/slices/audioStreamSlice';
import AudioVisualization from './AudioVisualization';
import TranscriptionDisplay from './TranscriptionDisplay';
import WebSocketAudioStream from './WebSocketAudioStream';

// Mock store for testing
const createMockStore = () => {
  return configureStore({
    reducer: {
      audioStream: audioStreamReducer,
    },
  });
};

// Mock audio data
const mockVisualizationData = {
  frequencyData: new Uint8Array([100, 120, 80, 90, 110]),
  waveformData: new Float32Array([0.1, -0.2, 0.3, -0.1, 0.2]),
  volume: 0.5,
  timestamp: Date.now(),
};

const mockTranscriptionResults = [
  {
    text: 'Hello world',
    confidence: 0.95,
    isFinal: true,
    timestamp: Date.now() - 1000,
    language: 'en',
    words: [
      { word: 'Hello', confidence: 0.98, startTime: 0, endTime: 0.5 },
      { word: 'world', confidence: 0.92, startTime: 0.6, endTime: 1.0 },
    ],
  },
];

describe('Audio Components', () => {
  let store: ReturnType<typeof createMockStore>;

  beforeEach(() => {
    store = createMockStore();
  });

  describe('AudioVisualization', () => {
    it('renders without crashing', () => {
      render(
        <AudioVisualization
          data={mockVisualizationData}
          width={400}
          height={200}
        />
      );
      
      expect(screen.getByText('Audio Visualization')).toBeInTheDocument();
    });

    it('displays volume percentage', () => {
      render(
        <AudioVisualization
          data={mockVisualizationData}
          width={400}
          height={200}
          showVolume={true}
        />
      );
      
      expect(screen.getByText('50%')).toBeInTheDocument();
    });

    it('shows controls when enabled', () => {
      render(
        <AudioVisualization
          data={mockVisualizationData}
          width={400}
          height={200}
          showControls={true}
        />
      );
      
      expect(screen.getByText('Sensitivity')).toBeInTheDocument();
      expect(screen.getByText('Smoothing')).toBeInTheDocument();
    });
  });

  describe('TranscriptionDisplay', () => {
    it('renders without crashing', () => {
      render(
        <TranscriptionDisplay
          currentTranscription=""
          transcriptionHistory={[]}
          isProcessing={false}
          onClear={() => {}}
        />
      );
      
      expect(screen.getByText('Real-time Transcription')).toBeInTheDocument();
    });

    it('displays current transcription', () => {
      render(
        <TranscriptionDisplay
          currentTranscription="Test transcription"
          transcriptionHistory={[]}
          isProcessing={false}
          onClear={() => {}}
        />
      );
      
      expect(screen.getByText('Test transcription')).toBeInTheDocument();
    });

    it('shows transcription history', () => {
      render(
        <TranscriptionDisplay
          currentTranscription=""
          transcriptionHistory={mockTranscriptionResults}
          isProcessing={false}
          onClear={() => {}}
        />
      );
      
      expect(screen.getByText('Hello world')).toBeInTheDocument();
      expect(screen.getByText('95%')).toBeInTheDocument();
    });

    it('displays processing indicator when active', () => {
      render(
        <TranscriptionDisplay
          currentTranscription=""
          transcriptionHistory={[]}
          isProcessing={true}
          onClear={() => {}}
        />
      );
      
      expect(screen.getByText(/Processing/)).toBeInTheDocument();
    });
  });

  describe('WebSocketAudioStream', () => {
    it('renders without crashing', () => {
      render(
        <Provider store={store}>
          <WebSocketAudioStream />
        </Provider>
      );
      
      expect(screen.getByText('WebSocket Audio Stream')).toBeInTheDocument();
    });

    it('shows connection controls', () => {
      render(
        <Provider store={store}>
          <WebSocketAudioStream />
        </Provider>
      );
      
      expect(screen.getByText('Connect')).toBeInTheDocument();
    });

    it('displays metrics when enabled', () => {
      render(
        <Provider store={store}>
          <WebSocketAudioStream showMetrics={true} />
        </Provider>
      );
      
      expect(screen.getByText('Avg Latency')).toBeInTheDocument();
      expect(screen.getByText('Data Rate')).toBeInTheDocument();
    });
  });
});