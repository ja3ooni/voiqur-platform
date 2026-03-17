import React from 'react';
import {
  Paper,
  Typography,
  Grid,
  Box,
  Card,
  CardContent,
  LinearProgress
} from '@mui/material';
import { PieChart } from '@mui/x-charts/PieChart';
import { useSelector } from 'react-redux';
import { RootState } from '../../store/store';
import SpeedIcon from '@mui/icons-material/Speed';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';

const PerformanceMetricsPanel: React.FC = () => {
  const { performanceMetrics } = useSelector((state: RootState) => state.analytics);

  const latencyData = [
    { label: 'STT', value: performanceMetrics.latency.stt, color: '#1976d2' },
    { label: 'LLM', value: performanceMetrics.latency.llm, color: '#dc004e' },
    { label: 'TTS', value: performanceMetrics.latency.tts, color: '#9c27b0' }
  ];

  const accuracyData = [
    { label: 'STT Accuracy', value: performanceMetrics.accuracy.sttAccuracy * 100 },
    { label: 'Intent Recognition', value: performanceMetrics.accuracy.intentRecognition * 100 },
    { label: 'Emotion Detection', value: performanceMetrics.accuracy.emotionDetection * 100 },
    { label: 'Accent Detection', value: performanceMetrics.accuracy.accentDetection * 100 }
  ];

  const formatLatency = (ms: number) => `${ms}ms`;

  return (
    <Paper sx={{ p: 3, height: '100%' }}>
      <Box display="flex" alignItems="center" mb={3}>
        <SpeedIcon sx={{ mr: 1, color: 'primary.main' }} />
        <Typography variant="h6">Performance Metrics</Typography>
      </Box>

      <Grid container spacing={3}>
        {/* Latency Metrics */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="subtitle1" gutterBottom>
                Processing Latency
              </Typography>
              <Box sx={{ height: 200 }}>
                <PieChart
                  series={[{
                    data: latencyData,
                    highlightScope: { faded: 'global', highlighted: 'item' }
                  }]}
                  width={300}
                  height={200}
                />
              </Box>
              <Box mt={2}>
                <Typography variant="body2" color="text.secondary">
                  End-to-End: <strong>{formatLatency(performanceMetrics.latency.endToEnd)}</strong>
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>    
    {/* Accuracy Metrics */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <CheckCircleIcon sx={{ mr: 1, color: 'success.main' }} />
                <Typography variant="subtitle1">Accuracy Metrics</Typography>
              </Box>
              {accuracyData.map((metric, index) => (
                <Box key={index} mb={2}>
                  <Box display="flex" justifyContent="space-between" mb={1}>
                    <Typography variant="body2">{metric.label}</Typography>
                    <Typography variant="body2" fontWeight="bold">
                      {metric.value.toFixed(1)}%
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={metric.value}
                    sx={{
                      height: 8,
                      borderRadius: 4,
                      backgroundColor: 'grey.200',
                      '& .MuiLinearProgress-bar': {
                        backgroundColor: metric.value >= 90 ? 'success.main' : 
                                       metric.value >= 80 ? 'warning.main' : 'error.main'
                      }
                    }}
                  />
                </Box>
              ))}
            </CardContent>
          </Card>
        </Grid>

        {/* Usage Statistics */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <TrendingUpIcon sx={{ mr: 1, color: 'info.main' }} />
                <Typography variant="subtitle1">Usage Statistics</Typography>
              </Box>
              <Grid container spacing={2}>
                <Grid item xs={6} sm={3}>
                  <Box textAlign="center">
                    <Typography variant="h4" color="primary.main">
                      {performanceMetrics.usage.totalSessions.toLocaleString()}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Total Sessions
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Box textAlign="center">
                    <Typography variant="h4" color="success.main">
                      {performanceMetrics.usage.activeSessions}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Active Sessions
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Box textAlign="center">
                    <Typography variant="h4" color="info.main">
                      {performanceMetrics.usage.requestsPerMinute}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Requests/Min
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Box textAlign="center">
                    <Typography variant="h4" color="warning.main">
                      {Math.round(performanceMetrics.usage.averageSessionDuration / 60)}m
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Avg Session
                    </Typography>
                  </Box>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Paper>
  );
};

export default PerformanceMetricsPanel;