import React, { useEffect, useRef, useState } from 'react';
import {
  Box,
  Paper,
  Button,
  Typography,
  Grid,
  Alert,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  Divider,
} from '@mui/material';
import {
  Mic as MicIcon,
  MicOff as MicOffIcon,
  Settings as SettingsIcon,
  SignalWifiConnectedNoInternet4 as DisconnectedIcon,
  SignalWifi4Bar as ConnectedIcon,
} from '@mui/icons-material';
import { useDispatch, useSelector } from 'react-redux';
import { RootState } from '../../store/store';
import {
  setRecording,
  setConnected,
  setProcessing,
  addTranscriptionResult,
  updateVisualizationData,
  setError,
  updateLatency,
  clearTranscription,
  updateAudioConfig,
} from '../../store/slices/audioStreamSlice';
import { AudioStreamService } from '../../services/audioStreamService';
import AudioVisualization from './AudioVisualization';
import TranscriptionDisplay from './TranscriptionDisplay';

const AudioStreamingPanel: React.FC = () => {
  const dispatch = useDispatch();
  const audioState = useSelector((state: RootState) => state.audioStream);
  const [audioService] = useState(() => new AudioStreamService());
  const [showSettings, setShowSettings] = useState(false);
  const serviceInitialized = useRef(false);

  // Initialize audio service
  useEffect(() => {
    if (serviceInitialized.current) return;
    serviceInitialized.current = true;

    // Set up event handlers
    audioService.onConnection((connected) => {
      dispatch(setConnected(connected));
    });

    audioService.onTranscription((result) => {
      dispatch(addTranscriptionResult(result));
    });

    audioService.onVisualization((data) => {
      dispatch(updateVisualizationData({
        ...data,
        timestamp: Date.now(),
      }));
    });

    audioService.onError((error) => {
      dispatch(setError(error));
    });

    audioService.onLatency((latency) => {
      dispatch(updateLatency(latency));
    });

    // Cleanup on unmount
    return () => {
      audioService.disconnect();
    };
  }, [audioService, dispatch]);

  const handleConnect = async () => {
    try {
      dispatch(setError(null));
      await audioService.connect();
    } catch (error) {
      console.error('Failed to connect:', error);
    }
  };

  const handleDisconnect = () => {
    audioService.disconnect();
  };

  const handleStartRecording = async () => {
    try {
      dispatch(setError(null));
      dispatch(setProcessing(true));
      await audioService.startRecording();
      dispatch(setRecording(true));
    } catch (error) {
      dispatch(setProcessing(false));
      console.error('Failed to start recording:', error);
    }
  };

  const handleStopRecording = () => {
    audioService.stopRecording();
    dispatch(setRecording(false));
    dispatch(setProcessing(false));
  };

  const handleClearTranscription = () => {
    dispatch(clearTranscription());
  };

  const handleConfigChange = (key: string, value: any) => {
    const newConfig = { [key]: value };
    dispatch(updateAudioConfig(newConfig));
    audioService.updateConfig(newConfig);
  };

  const getStatusColor = () => {
    if (!audioState.isConnected) return 'error';
    if (audioState.isRecording) return 'success';
    return 'warning';
  };

  const getStatusText = () => {
    if (!audioState.isConnected) return 'Disconnected';
    if (audioState.isRecording) return 'Recording';
    if (audioState.isProcessing) return 'Processing';
    return 'Connected';
  };

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 2 }}>
      {/* Header with Controls */}
      <Paper elevation={2} sx={{ p: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Typography variant="h5">
            Real-time Audio Streaming
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Chip
              icon={audioState.isConnected ? <ConnectedIcon /> : <DisconnectedIcon />}
              label={getStatusText()}
              color={getStatusColor()}
              variant="outlined"
            />
            {audioState.isConnected && audioState.latency > 0 && (
              <Chip
                label={`${audioState.latency}ms`}
                size="small"
                color={audioState.latency < 100 ? 'success' : audioState.latency < 200 ? 'warning' : 'error'}
              />
            )}
          </Box>
        </Box>

        {/* Connection Controls */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
          {!audioState.isConnected ? (
            <Button
              variant="contained"
              onClick={handleConnect}
              startIcon={<ConnectedIcon />}
            >
              Connect to Audio Service
            </Button>
          ) : (
            <Button
              variant="outlined"
              onClick={handleDisconnect}
              startIcon={<DisconnectedIcon />}
            >
              Disconnect
            </Button>
          )}

          {audioState.isConnected && (
            <>
              {!audioState.isRecording ? (
                <Button
                  variant="contained"
                  color="success"
                  onClick={handleStartRecording}
                  startIcon={<MicIcon />}
                  disabled={audioState.isProcessing}
                >
                  Start Recording
                </Button>
              ) : (
                <Button
                  variant="contained"
                  color="error"
                  onClick={handleStopRecording}
                  startIcon={<MicOffIcon />}
                >
                  Stop Recording
                </Button>
              )}
            </>
          )}

          <Button
            variant="outlined"
            onClick={() => setShowSettings(!showSettings)}
            startIcon={<SettingsIcon />}
          >
            Settings
          </Button>
        </Box>

        {/* Settings Panel */}
        {showSettings && (
          <>
            <Divider sx={{ my: 2 }} />
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6} md={3}>
                <FormControl fullWidth size="small">
                  <InputLabel>Sample Rate</InputLabel>
                  <Select
                    value={audioState.audioConfig.sampleRate}
                    label="Sample Rate"
                    onChange={(e) => handleConfigChange('sampleRate', e.target.value)}
                  >
                    <MenuItem value={8000}>8 kHz</MenuItem>
                    <MenuItem value={16000}>16 kHz</MenuItem>
                    <MenuItem value={22050}>22.05 kHz</MenuItem>
                    <MenuItem value={44100}>44.1 kHz</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <FormControl fullWidth size="small">
                  <InputLabel>Channels</InputLabel>
                  <Select
                    value={audioState.audioConfig.channels}
                    label="Channels"
                    onChange={(e) => handleConfigChange('channels', e.target.value)}
                  >
                    <MenuItem value={1}>Mono</MenuItem>
                    <MenuItem value={2}>Stereo</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <FormControl fullWidth size="small">
                  <InputLabel>Bit Depth</InputLabel>
                  <Select
                    value={audioState.audioConfig.bitDepth}
                    label="Bit Depth"
                    onChange={(e) => handleConfigChange('bitDepth', e.target.value)}
                  >
                    <MenuItem value={8}>8-bit</MenuItem>
                    <MenuItem value={16}>16-bit</MenuItem>
                    <MenuItem value={24}>24-bit</MenuItem>
                    <MenuItem value={32}>32-bit</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <FormControl fullWidth size="small">
                  <InputLabel>Buffer Size</InputLabel>
                  <Select
                    value={audioState.audioConfig.bufferSize}
                    label="Buffer Size"
                    onChange={(e) => handleConfigChange('bufferSize', e.target.value)}
                  >
                    <MenuItem value={1024}>1024</MenuItem>
                    <MenuItem value={2048}>2048</MenuItem>
                    <MenuItem value={4096}>4096</MenuItem>
                    <MenuItem value={8192}>8192</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
            </Grid>
          </>
        )}

        {/* Error Display */}
        {audioState.error && (
          <Alert severity="error" sx={{ mt: 2 }} onClose={() => dispatch(setError(null))}>
            {audioState.error}
          </Alert>
        )}
      </Paper>

      {/* Main Content */}
      <Grid container spacing={2} sx={{ flex: 1, overflow: 'hidden' }}>
        {/* Audio Visualization */}
        <Grid item xs={12} lg={6}>
          <AudioVisualization
            data={audioState.visualizationData}
            width={400}
            height={200}
          />
        </Grid>

        {/* Transcription Display */}
        <Grid item xs={12} lg={6} sx={{ height: '100%' }}>
          <TranscriptionDisplay
            currentTranscription={audioState.currentTranscription}
            transcriptionHistory={audioState.transcriptionHistory}
            isProcessing={audioState.isProcessing}
            onClear={handleClearTranscription}
          />
        </Grid>
      </Grid>
    </Box>
  );
};

export default AudioStreamingPanel;