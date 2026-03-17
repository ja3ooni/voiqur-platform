import React, { useEffect, useRef, useState, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Alert,
  Chip,
  LinearProgress,
  Grid,
  Card,
  CardContent,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Stop as StopIcon,

  Settings as SettingsIcon,
  SignalWifi4Bar as ConnectedIcon,
  SignalWifiOff as DisconnectedIcon,
  NetworkCheck as LatencyIcon,
  VolumeUp as VolumeIcon,
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
} from '../../store/slices/audioStreamSlice';
import { AudioStreamService } from '../../services/audioStreamService';

interface WebSocketAudioStreamProps {
  wsUrl?: string;
  autoConnect?: boolean;
  showMetrics?: boolean;
  onStreamStart?: () => void;
  onStreamStop?: () => void;
  onTranscription?: (text: string, confidence: number) => void;
}

interface StreamMetrics {
  packetsReceived: number;
  packetsLost: number;
  averageLatency: number;
  dataRate: number; // bytes per second
  connectionUptime: number;
  lastPacketTime: number;
}

const WebSocketAudioStream: React.FC<WebSocketAudioStreamProps> = ({
  wsUrl = 'ws://localhost:8000/ws/audio',
  autoConnect = false,
  showMetrics = true,
  onStreamStart,
  onStreamStop,
  onTranscription,
}) => {
  const dispatch = useDispatch();
  const audioState = useSelector((state: RootState) => state.audioStream);
  const [audioService] = useState(() => new AudioStreamService(wsUrl));
  const [streamMetrics, setStreamMetrics] = useState<StreamMetrics>({
    packetsReceived: 0,
    packetsLost: 0,
    averageLatency: 0,
    dataRate: 0,
    connectionUptime: 0,
    lastPacketTime: 0,
  });
  const [connectionQuality, setConnectionQuality] = useState<'excellent' | 'good' | 'fair' | 'poor'>('excellent');
  const [isStreaming, setIsStreaming] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  
  const metricsInterval = useRef<NodeJS.Timeout>();
  const connectionStartTime = useRef<number>(0);
  const latencyHistory = useRef<number[]>([]);
  const dataRateHistory = useRef<Array<{ size: number; time: number }>>([]);

  // Define callback functions first
  const stopMetricsTracking = useCallback(() => {
    if (metricsInterval.current) {
      clearInterval(metricsInterval.current);
      metricsInterval.current = undefined;
    }
  }, []);

  const updateLatencyMetrics = useCallback((latency: number) => {
    latencyHistory.current.push(latency);
    if (latencyHistory.current.length > 10) {
      latencyHistory.current.shift();
    }
    
    const avgLatency = latencyHistory.current.reduce((sum, l) => sum + l, 0) / latencyHistory.current.length;
    setStreamMetrics(prev => ({
      ...prev,
      averageLatency: avgLatency,
    }));
  }, []);

  const updateDataRate = useCallback((dataSize: number) => {
    const now = Date.now();
    const newEntry = { size: dataSize, time: now };
    
    // Update the ref with proper typing
    const currentHistory = [...dataRateHistory.current, newEntry];
    
    // Keep only last 5 seconds of data
    const filteredHistory = currentHistory.filter(
      entry => now - entry.time < 5000
    );
    
    dataRateHistory.current = filteredHistory;
    
    if (filteredHistory.length > 1) {
      const totalSize = filteredHistory.reduce((sum, entry) => sum + entry.size, 0);
      const timeSpan = (now - filteredHistory[0].time) / 1000;
      const rate = totalSize / timeSpan;
      
      setStreamMetrics(prev => ({
        ...prev,
        dataRate: rate,
      }));
    }
  }, []);

  const assessConnectionQuality = useCallback(() => {
    const avgLatency = streamMetrics.averageLatency;
    const dataRate = streamMetrics.dataRate;
    
    if (avgLatency < 50 && dataRate > 1000) {
      setConnectionQuality('excellent');
    } else if (avgLatency < 100 && dataRate > 500) {
      setConnectionQuality('good');
    } else if (avgLatency < 200 && dataRate > 200) {
      setConnectionQuality('fair');
    } else {
      setConnectionQuality('poor');
    }
  }, [streamMetrics.averageLatency, streamMetrics.dataRate]);

  const startMetricsTracking = useCallback(() => {
    metricsInterval.current = setInterval(() => {
      const now = Date.now();
      const uptime = connectionStartTime.current ? now - connectionStartTime.current : 0;
      
      setStreamMetrics(prev => ({
        ...prev,
        connectionUptime: uptime,
      }));

      // Assess connection quality
      assessConnectionQuality();
    }, 1000);
  }, [assessConnectionQuality]);

  const handleConnect = useCallback(async () => {
    try {
      dispatch(setError(null));
      await audioService.connect();
    } catch (error) {
      console.error('Failed to connect:', error);
    }
  }, [audioService, dispatch]);

  // Initialize audio service and event handlers
  useEffect(() => {
    // Connection handler
    audioService.onConnection((connected) => {
      dispatch(setConnected(connected));
      if (connected) {
        connectionStartTime.current = Date.now();
        startMetricsTracking();
      } else {
        stopMetricsTracking();
        setIsStreaming(false);
      }
    });

    // Transcription handler with enhanced processing
    audioService.onTranscription((result) => {
      dispatch(addTranscriptionResult(result));
      onTranscription?.(result.text, result.confidence);
      
      // Update metrics
      setStreamMetrics(prev => ({
        ...prev,
        packetsReceived: prev.packetsReceived + 1,
        lastPacketTime: Date.now(),
      }));
    });

    // Visualization handler
    audioService.onVisualization((data) => {
      dispatch(updateVisualizationData({
        ...data,
        timestamp: Date.now(),
      }));
      
      // Calculate data rate
      const dataSize = data.frequencyData.length + data.waveformData.length * 4; // rough estimate
      updateDataRate(dataSize);
    });

    // Error handler
    audioService.onError((error) => {
      dispatch(setError(error));
      setIsStreaming(false);
    });

    // Latency handler with quality assessment
    audioService.onLatency((latency) => {
      dispatch(updateLatency(latency));
      updateLatencyMetrics(latency);
    });

    // Auto-connect if enabled
    if (autoConnect) {
      handleConnect();
    }

    return () => {
      audioService.disconnect();
      stopMetricsTracking();
    };
  }, [audioService, dispatch, autoConnect, onTranscription, handleConnect, startMetricsTracking, stopMetricsTracking, updateDataRate, updateLatencyMetrics]);

  const handleDisconnect = () => {
    audioService.disconnect();
    setIsStreaming(false);
  };

  const handleStartStreaming = async () => {
    try {
      dispatch(setError(null));
      dispatch(setProcessing(true));
      await audioService.startRecording();
      dispatch(setRecording(true));
      setIsStreaming(true);
      onStreamStart?.();
    } catch (error) {
      dispatch(setProcessing(false));
      console.error('Failed to start streaming:', error);
    }
  };

  const handleStopStreaming = () => {
    audioService.stopRecording();
    dispatch(setRecording(false));
    dispatch(setProcessing(false));
    setIsStreaming(false);
    onStreamStop?.();
  };

  const getQualityColor = (quality: string) => {
    switch (quality) {
      case 'excellent': return 'success';
      case 'good': return 'info';
      case 'fair': return 'warning';
      case 'poor': return 'error';
      default: return 'default';
    }
  };

  const formatUptime = (ms: number) => {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    
    if (hours > 0) {
      return `${hours}h ${minutes % 60}m ${seconds % 60}s`;
    } else if (minutes > 0) {
      return `${minutes}m ${seconds % 60}s`;
    } else {
      return `${seconds}s`;
    }
  };

  const formatDataRate = (bytesPerSecond: number) => {
    if (bytesPerSecond > 1024 * 1024) {
      return `${(bytesPerSecond / (1024 * 1024)).toFixed(1)} MB/s`;
    } else if (bytesPerSecond > 1024) {
      return `${(bytesPerSecond / 1024).toFixed(1)} KB/s`;
    } else {
      return `${bytesPerSecond.toFixed(0)} B/s`;
    }
  };

  return (
    <Paper elevation={2} sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h6">
          WebSocket Audio Stream
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Chip
            icon={audioState.isConnected ? <ConnectedIcon /> : <DisconnectedIcon />}
            label={audioState.isConnected ? 'Connected' : 'Disconnected'}
            color={audioState.isConnected ? 'success' : 'error'}
            variant="outlined"
            size="small"
          />
          {audioState.isConnected && (
            <Chip
              label={connectionQuality.toUpperCase()}
              color={getQualityColor(connectionQuality) as any}
              size="small"
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
            Connect
          </Button>
        ) : (
          <>
            <Button
              variant="outlined"
              onClick={handleDisconnect}
              startIcon={<DisconnectedIcon />}
            >
              Disconnect
            </Button>
            
            {!isStreaming ? (
              <Button
                variant="contained"
                color="success"
                onClick={handleStartStreaming}
                startIcon={<PlayIcon />}
                disabled={audioState.isProcessing}
              >
                Start Stream
              </Button>
            ) : (
              <Button
                variant="contained"
                color="error"
                onClick={handleStopStreaming}
                startIcon={<StopIcon />}
              >
                Stop Stream
              </Button>
            )}
          </>
        )}

        <Tooltip title="Settings">
          <IconButton onClick={() => setShowSettings(!showSettings)}>
            <SettingsIcon />
          </IconButton>
        </Tooltip>
      </Box>

      {/* Streaming Progress */}
      {isStreaming && (
        <Box sx={{ mb: 2 }}>
          <LinearProgress 
            variant="indeterminate" 
            sx={{ 
              height: 6, 
              borderRadius: 3,
              backgroundColor: 'rgba(0,0,0,0.1)',
              '& .MuiLinearProgress-bar': {
                borderRadius: 3,
              }
            }} 
          />
          <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
            Streaming audio data in real-time...
          </Typography>
        </Box>
      )}

      {/* Metrics Display */}
      {showMetrics && audioState.isConnected && (
        <Grid container spacing={2} sx={{ mb: 2 }}>
          <Grid item xs={6} sm={3}>
            <Card variant="outlined" sx={{ textAlign: 'center' }}>
              <CardContent sx={{ py: 1 }}>
                <Typography variant="h6" color="primary">
                  {Math.round(streamMetrics.averageLatency)}ms
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Avg Latency
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={6} sm={3}>
            <Card variant="outlined" sx={{ textAlign: 'center' }}>
              <CardContent sx={{ py: 1 }}>
                <Typography variant="h6" color="info.main">
                  {formatDataRate(streamMetrics.dataRate)}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Data Rate
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={6} sm={3}>
            <Card variant="outlined" sx={{ textAlign: 'center' }}>
              <CardContent sx={{ py: 1 }}>
                <Typography variant="h6" color="success.main">
                  {streamMetrics.packetsReceived}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Packets
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={6} sm={3}>
            <Card variant="outlined" sx={{ textAlign: 'center' }}>
              <CardContent sx={{ py: 1 }}>
                <Typography variant="h6" color="text.primary">
                  {formatUptime(streamMetrics.connectionUptime)}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Uptime
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Error Display */}
      {audioState.error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => dispatch(setError(null))}>
          {audioState.error}
        </Alert>
      )}

      {/* Real-time Status */}
      {audioState.isConnected && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, p: 1, backgroundColor: 'rgba(0,0,0,0.02)', borderRadius: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <LatencyIcon fontSize="small" color={audioState.latency < 100 ? 'success' : 'warning'} />
            <Typography variant="caption">
              {audioState.latency}ms
            </Typography>
          </Box>
          
          {audioState.visualizationData && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <VolumeIcon fontSize="small" color="primary" />
              <Typography variant="caption">
                {Math.round(audioState.visualizationData.volume * 100)}%
              </Typography>
            </Box>
          )}
          
          <Box sx={{ flex: 1 }} />
          
          <Typography variant="caption" color="text.secondary">
            {new Date().toLocaleTimeString()}
          </Typography>
        </Box>
      )}
    </Paper>
  );
};

export default WebSocketAudioStream;