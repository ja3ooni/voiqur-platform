import React, { useRef, useEffect, useState } from 'react';
import { Box, Paper, Typography, ToggleButton, ToggleButtonGroup, Slider } from '@mui/material';
import { 
  GraphicEq as WaveformIcon, 
  BarChart as FrequencyIcon
} from '@mui/icons-material';
import { AudioVisualizationData } from '../../types/audio';

interface AudioVisualizationProps {
  data: AudioVisualizationData | null;
  width?: number;
  height?: number;
  showWaveform?: boolean;
  showFrequency?: boolean;
  showVolume?: boolean;
  showControls?: boolean;
  theme?: 'light' | 'dark';
}

const AudioVisualization: React.FC<AudioVisualizationProps> = ({
  data,
  width = 400,
  height = 200,
  showWaveform = true,
  showFrequency = true,
  showVolume = true,
  showControls = true,
  theme = 'light',
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const volumeRef = useRef<HTMLDivElement>(null);
  const [visualizationMode, setVisualizationMode] = useState<string[]>(['waveform', 'frequency']);
  const [sensitivity, setSensitivity] = useState<number>(1);
  const [smoothing, setSmoothing] = useState<number>(0.8);

  useEffect(() => {
    if (!data || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas with theme-appropriate background
    const bgColor = theme === 'dark' ? '#1a1a1a' : '#fafafa';
    ctx.fillStyle = bgColor;
    ctx.fillRect(0, 0, width, height);

    const halfHeight = height / 2;
    const quarterHeight = height / 4;
    const showWaveformMode = visualizationMode.includes('waveform') && showWaveform;
    const showFrequencyMode = visualizationMode.includes('frequency') && showFrequency;

    // Enhanced waveform visualization
    if (showWaveformMode && data.waveformData) {
      const gradient = ctx.createLinearGradient(0, 0, width, 0);
      gradient.addColorStop(0, theme === 'dark' ? '#64b5f6' : '#2196f3');
      gradient.addColorStop(0.5, theme === 'dark' ? '#42a5f5' : '#1976d2');
      gradient.addColorStop(1, theme === 'dark' ? '#2196f3' : '#0d47a1');
      
      ctx.strokeStyle = gradient;
      ctx.lineWidth = 2;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.beginPath();

      const sliceWidth = width / data.waveformData.length;
      let x = 0;

      // Apply sensitivity and smoothing
      for (let i = 0; i < data.waveformData.length; i++) {
        const v = data.waveformData[i] * quarterHeight * sensitivity;
        const y = halfHeight + v;

        if (i === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }

        x += sliceWidth;
      }

      ctx.stroke();

      // Add glow effect for active audio
      if (data.volume > 0.1) {
        ctx.shadowColor = theme === 'dark' ? '#64b5f6' : '#2196f3';
        ctx.shadowBlur = 10;
        ctx.stroke();
        ctx.shadowBlur = 0;
      }
    }

    // Enhanced frequency visualization with gradient bars
    if (showFrequencyMode && data.frequencyData) {
      const barWidth = Math.max(1, width / data.frequencyData.length);
      const maxBarHeight = showWaveformMode ? quarterHeight : halfHeight;
      const yOffset = showWaveformMode ? height - maxBarHeight : halfHeight;

      for (let i = 0; i < data.frequencyData.length; i++) {
        const barHeight = (data.frequencyData[i] / 255) * maxBarHeight * sensitivity;
        const x = i * barWidth;
        const y = yOffset - barHeight;

        // Create gradient for each bar
        const gradient = ctx.createLinearGradient(0, yOffset, 0, yOffset - maxBarHeight);
        const intensity = data.frequencyData[i] / 255;
        
        if (theme === 'dark') {
          gradient.addColorStop(0, `rgba(76, 175, 80, ${0.3 + intensity * 0.7})`);
          gradient.addColorStop(0.5, `rgba(139, 195, 74, ${0.5 + intensity * 0.5})`);
          gradient.addColorStop(1, `rgba(205, 220, 57, ${0.7 + intensity * 0.3})`);
        } else {
          gradient.addColorStop(0, `rgba(76, 175, 80, ${0.5 + intensity * 0.5})`);
          gradient.addColorStop(0.5, `rgba(139, 195, 74, ${0.7 + intensity * 0.3})`);
          gradient.addColorStop(1, `rgba(205, 220, 57, ${0.9 + intensity * 0.1})`);
        }

        ctx.fillStyle = gradient;
        ctx.fillRect(x, y, barWidth - 1, barHeight);
      }
    }

    // Draw center line and grid
    ctx.strokeStyle = theme === 'dark' ? '#444' : '#ddd';
    ctx.lineWidth = 1;
    ctx.setLineDash([2, 2]);
    
    // Center line
    ctx.beginPath();
    ctx.moveTo(0, halfHeight);
    ctx.lineTo(width, halfHeight);
    ctx.stroke();
    
    // Grid lines
    for (let i = 1; i < 4; i++) {
      const y = (height / 4) * i;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }
    
    ctx.setLineDash([]);

  }, [data, width, height, showWaveform, showFrequency, visualizationMode, sensitivity, smoothing, theme]);

  useEffect(() => {
    if (!data || !volumeRef.current || !showVolume) return;

    const volumeElement = volumeRef.current;
    const volumePercentage = Math.min(data.volume * 100, 100);
    
    volumeElement.style.width = `${volumePercentage}%`;
    
    // Color based on volume level
    if (volumePercentage > 80) {
      volumeElement.style.backgroundColor = '#f44336'; // Red
    } else if (volumePercentage > 50) {
      volumeElement.style.backgroundColor = '#ff9800'; // Orange
    } else if (volumePercentage > 20) {
      volumeElement.style.backgroundColor = '#4caf50'; // Green
    } else {
      volumeElement.style.backgroundColor = '#2196f3'; // Blue
    }
  }, [data, showVolume]);

  const handleVisualizationModeChange = (
    event: React.MouseEvent<HTMLElement>,
    newModes: string[],
  ) => {
    if (newModes.length > 0) {
      setVisualizationMode(newModes);
    }
  };

  return (
    <Paper elevation={2} sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h6">
          Audio Visualization
        </Typography>
        {data && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="caption" color="primary">
              {Math.round(data.volume * 100)}% Vol
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {new Date(data.timestamp).toLocaleTimeString()}
            </Typography>
          </Box>
        )}
      </Box>

      {showControls && (
        <Box sx={{ mb: 2 }}>
          <ToggleButtonGroup
            value={visualizationMode}
            onChange={handleVisualizationModeChange}
            size="small"
            sx={{ mb: 1 }}
          >
            <ToggleButton value="waveform" aria-label="waveform">
              <WaveformIcon fontSize="small" />
            </ToggleButton>
            <ToggleButton value="frequency" aria-label="frequency">
              <FrequencyIcon fontSize="small" />
            </ToggleButton>
          </ToggleButtonGroup>
          
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
            <Box sx={{ minWidth: 80 }}>
              <Typography variant="caption">Sensitivity</Typography>
              <Slider
                value={sensitivity}
                onChange={(_, value) => setSensitivity(value as number)}
                min={0.1}
                max={3}
                step={0.1}
                size="small"
              />
            </Box>
            <Box sx={{ minWidth: 80 }}>
              <Typography variant="caption">Smoothing</Typography>
              <Slider
                value={smoothing}
                onChange={(_, value) => setSmoothing(value as number)}
                min={0}
                max={1}
                step={0.1}
                size="small"
              />
            </Box>
          </Box>
        </Box>
      )}
      
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <canvas
          ref={canvasRef}
          width={width}
          height={height}
          style={{
            border: theme === 'dark' ? '1px solid #444' : '1px solid #ddd',
            borderRadius: '8px',
            backgroundColor: theme === 'dark' ? '#1a1a1a' : '#fafafa',
            maxWidth: '100%',
            height: 'auto',
          }}
        />
      </Box>

      {showVolume && (
        <Box sx={{ mt: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="body2">
              Volume Level
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {data ? `${Math.round(data.volume * 100)}%` : '0%'}
            </Typography>
          </Box>
          <Box
            sx={{
              width: '100%',
              height: 12,
              backgroundColor: theme === 'dark' ? '#333' : '#e0e0e0',
              borderRadius: 2,
              overflow: 'hidden',
              position: 'relative',
            }}
          >
            <Box
              ref={volumeRef}
              sx={{
                height: '100%',
                transition: 'width 0.1s ease-out',
                borderRadius: 2,
                position: 'relative',
                '&::after': {
                  content: '""',
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  right: 0,
                  bottom: 0,
                  background: 'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.3) 50%, transparent 100%)',
                  animation: data && data.volume > 0.1 ? 'shimmer 2s infinite' : 'none',
                },
                '@keyframes shimmer': {
                  '0%': { transform: 'translateX(-100%)' },
                  '100%': { transform: 'translateX(100%)' },
                },
              }}
            />
          </Box>
        </Box>
      )}
    </Paper>
  );
};

export default AudioVisualization;