import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { AudioStreamState, AudioStreamConfig, TranscriptionResult, AudioVisualizationData } from '../../types/audio';

const initialState: AudioStreamState = {
  isRecording: false,
  isConnected: false,
  isProcessing: false,
  currentTranscription: '',
  transcriptionHistory: [],
  audioConfig: {
    sampleRate: 16000,
    channels: 1,
    bitDepth: 16,
    bufferSize: 4096,
  },
  visualizationData: null,
  error: null,
  latency: 0,
};

const audioStreamSlice = createSlice({
  name: 'audioStream',
  initialState,
  reducers: {
    setRecording: (state, action: PayloadAction<boolean>) => {
      state.isRecording = action.payload;
      if (!action.payload) {
        state.isProcessing = false;
      }
    },
    setConnected: (state, action: PayloadAction<boolean>) => {
      state.isConnected = action.payload;
      if (!action.payload) {
        state.isRecording = false;
        state.isProcessing = false;
      }
    },
    setProcessing: (state, action: PayloadAction<boolean>) => {
      state.isProcessing = action.payload;
    },
    updateCurrentTranscription: (state, action: PayloadAction<string>) => {
      state.currentTranscription = action.payload;
    },
    addTranscriptionResult: (state, action: PayloadAction<TranscriptionResult>) => {
      const result = action.payload;
      
      // If it's a final result, add to history and clear current
      if (result.isFinal) {
        state.transcriptionHistory.push(result);
        state.currentTranscription = '';
        
        // Keep only last 50 results to prevent memory issues
        if (state.transcriptionHistory.length > 50) {
          state.transcriptionHistory = state.transcriptionHistory.slice(-50);
        }
      } else {
        // Update current transcription with partial result
        state.currentTranscription = result.text;
      }
    },
    updateVisualizationData: (state, action: PayloadAction<AudioVisualizationData>) => {
      state.visualizationData = action.payload;
    },
    updateAudioConfig: (state, action: PayloadAction<Partial<AudioStreamConfig>>) => {
      state.audioConfig = { ...state.audioConfig, ...action.payload };
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },
    updateLatency: (state, action: PayloadAction<number>) => {
      state.latency = action.payload;
    },
    clearTranscription: (state) => {
      state.currentTranscription = '';
      state.transcriptionHistory = [];
    },
    resetAudioStream: (state) => {
      return { ...initialState, audioConfig: state.audioConfig };
    },
  },
});

export const {
  setRecording,
  setConnected,
  setProcessing,
  updateCurrentTranscription,
  addTranscriptionResult,
  updateVisualizationData,
  updateAudioConfig,
  setError,
  updateLatency,
  clearTranscription,
  resetAudioStream,
} = audioStreamSlice.actions;

export default audioStreamSlice.reducer;