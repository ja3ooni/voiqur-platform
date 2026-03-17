import React, { useState } from 'react';
import {
  Box,
  Grid,
  Paper,
  Typography,
  Switch,
  FormControlLabel,
  Tabs,
  Tab,
  Card,
  CardContent,
  Divider,
  Chip,
  Alert,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  GraphicEq as VisualizationIcon,
  Transcribe as TranscriptionIcon,
  Settings as SettingsIcon,
} from '@mui/icons-material';
import { useSelector } from 'react-redux';
import { RootState } from '../../store/store';
import AudioVisualization from './AudioVisualization';
import TranscriptionDisplay from './TranscriptionDisplay';
import WebSocketAudioStream from './WebSocketAudioStream';
import AudioStreamingPanel from './AudioStreamingPanel';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`audio-tabpanel-${index}`}
      aria-labelledby={`audio-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 0 }}>{children}</Box>}
    </div>
  );
}

const RealTimeAudioDashboard: React.FC = () => {
  const audioState = useSelector((state: RootState) => state.audioStream);
  const [activeTab, setActiveTab] = useState(0);
  const [dashboardSettings, setDashboardSettings] = useState({
    showMetrics: true,
    autoScroll: true,
    showWordConfidence: true,
    darkMode: false,
    compactView: false,
  });

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const handleSettingChange = (setting: string) => (event: React.ChangeEvent<HTMLInputElement>) => {
    setDashboardSettings(prev => ({
      ...prev,
      [setting]: event.target.checked,
    }));
  };

  const getPerformanceStatus = () => {
    if (!audioState.isConnected) return { status: 'disconnected', color: 'error' };
    if (audioState.latency > 200) return { status: 'poor', color: 'error' };
    if (audioState.latency > 100) return { status: 'fair', color: 'warning' };
    if (audioState.latency > 50) return { status: 'good', color: 'info' };
    return { status: 'excellent', color: 'success' };
  };

  const performanceStatus = getPerformanceStatus();

  return (
    <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column', p: 2, gap: 2 }}>
      {/* Header */}
      <Paper elevation={2} sx={{ p: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Typography variant="h4" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <DashboardIcon />
            Real-Time Audio Dashboard
          </Typography>
          
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            {/* Performance Indicator */}
            <Card variant="outlined" sx={{ minWidth: 120 }}>
              <CardContent sx={{ py: 1, textAlign: 'center' }}>
                <Typography variant="caption" color="text.secondary">
                  Performance
                </Typography>
                <Typography variant="h6" color={`${performanceStatus.color}.main`}>
                  {performanceStatus.status.toUpperCase()}
                </Typography>
              </CardContent>
            </Card>

            {/* Connection Status */}
            <Chip
              label={audioState.isConnected ? 'CONNECTED' : 'DISCONNECTED'}
              color={audioState.isConnected ? 'success' : 'error'}
              variant="filled"
            />

            {/* Latency Display */}
            {audioState.isConnected && (
              <Chip
                label={`${audioState.latency}ms`}
                color={performanceStatus.color as any}
                variant="outlined"
              />
            )}
          </Box>
        </Box>
      </Paper>

      {/* Main Content */}
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* Navigation Tabs */}
        <Paper elevation={1} sx={{ mb: 2 }}>
          <Tabs value={activeTab} onChange={handleTabChange} variant="fullWidth">
            <Tab 
              icon={<DashboardIcon />} 
              label="Overview" 
              id="audio-tab-0"
              aria-controls="audio-tabpanel-0"
            />
            <Tab 
              icon={<VisualizationIcon />} 
              label="Visualization" 
              id="audio-tab-1"
              aria-controls="audio-tabpanel-1"
            />
            <Tab 
              icon={<TranscriptionIcon />} 
              label="Transcription" 
              id="audio-tab-2"
              aria-controls="audio-tabpanel-2"
            />
            <Tab 
              icon={<SettingsIcon />} 
              label="Settings" 
              id="audio-tab-3"
              aria-controls="audio-tabpanel-3"
            />
          </Tabs>
        </Paper>

        {/* Tab Content */}
        <Box sx={{ flex: 1, overflow: 'hidden' }}>
          {/* Overview Tab */}
          <TabPanel value={activeTab} index={0}>
            <Grid container spacing={2} sx={{ height: '100%' }}>
              {/* WebSocket Stream Control */}
              <Grid item xs={12}>
                <WebSocketAudioStream
                  showMetrics={dashboardSettings.showMetrics}
                  autoConnect={false}
                />
              </Grid>
              
              {/* Split View: Visualization + Transcription */}
              <Grid item xs={12} md={6} sx={{ height: '400px' }}>
                <AudioVisualization
                  data={audioState.visualizationData}
                  width={500}
                  height={300}
                  showControls={true}
                  theme={dashboardSettings.darkMode ? 'dark' : 'light'}
                />
              </Grid>
              
              <Grid item xs={12} md={6} sx={{ height: '400px' }}>
                <TranscriptionDisplay
                  currentTranscription={audioState.currentTranscription}
                  transcriptionHistory={audioState.transcriptionHistory}
                  isProcessing={audioState.isProcessing}
                  onClear={() => {}}
                  showWordLevelConfidence={dashboardSettings.showWordConfidence}
                  autoScroll={dashboardSettings.autoScroll}
                  showTimestamps={true}
                />
              </Grid>
            </Grid>
          </TabPanel>

          {/* Visualization Tab */}
          <TabPanel value={activeTab} index={1}>
            <Grid container spacing={2} sx={{ height: '100%' }}>
              <Grid item xs={12} sx={{ height: '100%' }}>
                <AudioVisualization
                  data={audioState.visualizationData}
                  width={800}
                  height={500}
                  showControls={true}
                  theme={dashboardSettings.darkMode ? 'dark' : 'light'}
                />
              </Grid>
            </Grid>
          </TabPanel>

          {/* Transcription Tab */}
          <TabPanel value={activeTab} index={2}>
            <Grid container spacing={2} sx={{ height: '100%' }}>
              <Grid item xs={12} sx={{ height: '100%' }}>
                <TranscriptionDisplay
                  currentTranscription={audioState.currentTranscription}
                  transcriptionHistory={audioState.transcriptionHistory}
                  isProcessing={audioState.isProcessing}
                  onClear={() => {}}
                  showWordLevelConfidence={dashboardSettings.showWordConfidence}
                  autoScroll={dashboardSettings.autoScroll}
                  showTimestamps={true}
                  maxHistoryItems={50}
                />
              </Grid>
            </Grid>
          </TabPanel>

          {/* Settings Tab */}
          <TabPanel value={activeTab} index={3}>
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Paper elevation={2} sx={{ p: 3 }}>
                  <Typography variant="h6" gutterBottom>
                    Display Settings
                  </Typography>
                  <Divider sx={{ mb: 2 }} />
                  
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={dashboardSettings.showMetrics}
                          onChange={handleSettingChange('showMetrics')}
                        />
                      }
                      label="Show Performance Metrics"
                    />
                    
                    <FormControlLabel
                      control={
                        <Switch
                          checked={dashboardSettings.autoScroll}
                          onChange={handleSettingChange('autoScroll')}
                        />
                      }
                      label="Auto-scroll Transcription"
                    />
                    
                    <FormControlLabel
                      control={
                        <Switch
                          checked={dashboardSettings.showWordConfidence}
                          onChange={handleSettingChange('showWordConfidence')}
                        />
                      }
                      label="Show Word-level Confidence"
                    />
                    
                    <FormControlLabel
                      control={
                        <Switch
                          checked={dashboardSettings.darkMode}
                          onChange={handleSettingChange('darkMode')}
                        />
                      }
                      label="Dark Mode Visualization"
                    />
                    
                    <FormControlLabel
                      control={
                        <Switch
                          checked={dashboardSettings.compactView}
                          onChange={handleSettingChange('compactView')}
                        />
                      }
                      label="Compact View"
                    />
                  </Box>
                </Paper>
              </Grid>
              
              <Grid item xs={12} md={6}>
                <Paper elevation={2} sx={{ p: 3 }}>
                  <Typography variant="h6" gutterBottom>
                    Audio Configuration
                  </Typography>
                  <Divider sx={{ mb: 2 }} />
                  
                  <AudioStreamingPanel />
                </Paper>
              </Grid>

              {/* System Information */}
              <Grid item xs={12}>
                <Paper elevation={2} sx={{ p: 3 }}>
                  <Typography variant="h6" gutterBottom>
                    System Information
                  </Typography>
                  <Divider sx={{ mb: 2 }} />
                  
                  <Grid container spacing={2}>
                    <Grid item xs={6} sm={3}>
                      <Card variant="outlined">
                        <CardContent sx={{ textAlign: 'center' }}>
                          <Typography variant="h6" color="primary">
                            {audioState.transcriptionHistory.length}
                          </Typography>
                          <Typography variant="caption">
                            Total Transcriptions
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                    
                    <Grid item xs={6} sm={3}>
                      <Card variant="outlined">
                        <CardContent sx={{ textAlign: 'center' }}>
                          <Typography variant="h6" color="info.main">
                            {audioState.audioConfig.sampleRate / 1000}kHz
                          </Typography>
                          <Typography variant="caption">
                            Sample Rate
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                    
                    <Grid item xs={6} sm={3}>
                      <Card variant="outlined">
                        <CardContent sx={{ textAlign: 'center' }}>
                          <Typography variant="h6" color="success.main">
                            {audioState.audioConfig.channels === 1 ? 'Mono' : 'Stereo'}
                          </Typography>
                          <Typography variant="caption">
                            Audio Channels
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                    
                    <Grid item xs={6} sm={3}>
                      <Card variant="outlined">
                        <CardContent sx={{ textAlign: 'center' }}>
                          <Typography variant="h6" color="warning.main">
                            {audioState.audioConfig.bufferSize}
                          </Typography>
                          <Typography variant="caption">
                            Buffer Size
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                  </Grid>
                </Paper>
              </Grid>
            </Grid>
          </TabPanel>
        </Box>
      </Box>

      {/* Status Bar */}
      {audioState.error && (
        <Alert severity="error" sx={{ mt: 1 }}>
          {audioState.error}
        </Alert>
      )}
    </Box>
  );
};

export default RealTimeAudioDashboard;