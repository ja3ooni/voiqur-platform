import React, { useEffect, useRef, useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Chip,
  List,
  ListItem,
  ListItemText,
  LinearProgress,
  IconButton,
  Tooltip,
  Badge,
  Fade,
  Collapse,
} from '@mui/material';
import {
  Clear as ClearIcon,
  VolumeUp as VolumeUpIcon,
  Translate as TranslateIcon,
  Speed as SpeedIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
} from '@mui/icons-material';
import { TranscriptionResult } from '../../types/audio';

interface TranscriptionDisplayProps {
  currentTranscription: string;
  transcriptionHistory: TranscriptionResult[];
  isProcessing: boolean;
  onClear: () => void;
  maxHistoryItems?: number;
  showWordLevelConfidence?: boolean;
  autoScroll?: boolean;
  showTimestamps?: boolean;
}

const TranscriptionDisplay: React.FC<TranscriptionDisplayProps> = ({
  currentTranscription,
  transcriptionHistory,
  isProcessing,
  onClear,
  maxHistoryItems = 10,
  showWordLevelConfidence = true,
  autoScroll = true,
  showTimestamps = true,
}) => {
  const currentRef = useRef<HTMLDivElement>(null);
  const historyRef = useRef<HTMLDivElement>(null);
  const [showDetails, setShowDetails] = useState(false);
  const [processingDots, setProcessingDots] = useState('');

  // Auto-scroll to latest transcription
  useEffect(() => {
    if (autoScroll && historyRef.current) {
      historyRef.current.scrollTop = historyRef.current.scrollHeight;
    }
  }, [transcriptionHistory, autoScroll]);

  // Auto-scroll current transcription
  useEffect(() => {
    if (autoScroll && currentRef.current) {
      currentRef.current.scrollTop = currentRef.current.scrollHeight;
    }
  }, [currentTranscription, autoScroll]);

  // Animated processing dots
  useEffect(() => {
    if (!isProcessing) {
      setProcessingDots('');
      return;
    }

    const interval = setInterval(() => {
      setProcessingDots(prev => {
        if (prev.length >= 3) return '';
        return prev + '.';
      });
    }, 500);

    return () => clearInterval(interval);
  }, [isProcessing]);

  const getConfidenceColor = (confidence: number): string => {
    if (confidence >= 0.9) return '#4caf50'; // Green
    if (confidence >= 0.7) return '#ff9800'; // Orange
    if (confidence >= 0.5) return '#f44336'; // Red
    return '#9e9e9e'; // Gray
  };

  const getConfidenceLabel = (confidence: number): string => {
    if (confidence >= 0.9) return 'High';
    if (confidence >= 0.7) return 'Medium';
    if (confidence >= 0.5) return 'Low';
    return 'Very Low';
  };

  const formatTimestamp = (timestamp: number): string => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const displayHistory = transcriptionHistory.slice(-maxHistoryItems);

  const renderWordWithConfidence = (result: TranscriptionResult) => {
    if (!showWordLevelConfidence || !result.words) {
      return (
        <Typography variant="body1" component="span">
          {result.text}
        </Typography>
      );
    }

    return (
      <Box component="span">
        {result.words.map((word, index) => (
          <Tooltip
            key={index}
            title={`Confidence: ${Math.round(word.confidence * 100)}% | ${word.startTime.toFixed(2)}s - ${word.endTime.toFixed(2)}s`}
            arrow
          >
            <Typography
              component="span"
              sx={{
                backgroundColor: `rgba(76, 175, 80, ${word.confidence * 0.3})`,
                padding: '2px 4px',
                margin: '0 1px',
                borderRadius: '3px',
                cursor: 'help',
                color: word.confidence < 0.5 ? 'error.main' : 'inherit',
                fontWeight: word.confidence > 0.9 ? 'bold' : 'normal',
              }}
            >
              {word.word}
            </Typography>
          </Tooltip>
        ))}
      </Box>
    );
  };

  const getProcessingSpeed = () => {
    if (transcriptionHistory.length < 2) return 0;
    const recent = transcriptionHistory.slice(-5);
    const totalTime = recent[recent.length - 1].timestamp - recent[0].timestamp;
    const totalWords = recent.reduce((sum, result) => sum + (result.words?.length || result.text.split(' ').length), 0);
    return totalTime > 0 ? (totalWords / (totalTime / 1000)) * 60 : 0; // words per minute
  };

  return (
    <Paper elevation={2} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box
        sx={{
          p: 2,
          borderBottom: 1,
          borderColor: 'divider',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <Typography variant="h6">
          Real-time Transcription
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {isProcessing && (
            <Fade in={isProcessing}>
              <Chip
                icon={<VolumeUpIcon />}
                label={`Processing${processingDots}`}
                color="primary"
                size="small"
                variant="outlined"
              />
            </Fade>
          )}
          {transcriptionHistory.length > 0 && (
            <Chip
              icon={<SpeedIcon />}
              label={`${Math.round(getProcessingSpeed())} WPM`}
              size="small"
              variant="outlined"
              color="info"
            />
          )}
          <Tooltip title={showDetails ? "Hide details" : "Show details"}>
            <IconButton onClick={() => setShowDetails(!showDetails)} size="small">
              {showDetails ? <VisibilityOffIcon /> : <VisibilityIcon />}
            </IconButton>
          </Tooltip>
          <Tooltip title="Clear transcription">
            <IconButton onClick={onClear} size="small">
              <ClearIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Current Transcription */}
      <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
        <Typography variant="subtitle2" gutterBottom>
          Current Input
        </Typography>
        {isProcessing && <LinearProgress sx={{ mb: 1 }} />}
        <Box
          ref={currentRef}
          sx={{
            minHeight: 60,
            maxHeight: 120,
            overflow: 'auto',
            p: 2,
            backgroundColor: currentTranscription ? 'rgba(33, 150, 243, 0.05)' : '#f5f5f5',
            borderRadius: 2,
            border: currentTranscription ? '2px solid #2196f3' : '1px solid #ddd',
            position: 'relative',
            transition: 'all 0.3s ease',
          }}
        >
          {isProcessing && (
            <LinearProgress 
              sx={{ 
                position: 'absolute', 
                top: 0, 
                left: 0, 
                right: 0,
                borderRadius: '8px 8px 0 0',
              }} 
            />
          )}
          <Typography
            variant="body1"
            sx={{
              fontFamily: currentTranscription ? 'inherit' : 'monospace',
              color: currentTranscription ? 'text.primary' : 'text.secondary',
              fontStyle: currentTranscription ? 'normal' : 'italic',
              lineHeight: 1.6,
              fontSize: '1.1rem',
            }}
          >
            {currentTranscription || 'Speak to see real-time transcription...'}
          </Typography>
          {currentTranscription && (
            <Box sx={{ position: 'absolute', bottom: 4, right: 8 }}>
              <Typography variant="caption" color="primary">
                Live
              </Typography>
            </Box>
          )}
        </Box>
      </Box>

      {/* Transcription History */}
      <Box sx={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <Box sx={{ p: 2, pb: 1, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Typography variant="subtitle2">
            History ({displayHistory.length})
          </Typography>
          {displayHistory.length > 0 && (
            <Badge badgeContent={displayHistory.length} color="primary" max={99}>
              <Typography variant="caption" color="text.secondary">
                Avg: {Math.round(displayHistory.reduce((sum, r) => sum + r.confidence, 0) / displayHistory.length * 100)}%
              </Typography>
            </Badge>
          )}
        </Box>
        
        <Box
          ref={historyRef}
          sx={{
            flex: 1,
            overflow: 'auto',
            px: 2,
            pb: 2,
          }}
        >
          {displayHistory.length === 0 ? (
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100%',
                color: 'text.secondary',
              }}
            >
              <Typography variant="body2" sx={{ fontStyle: 'italic' }}>
                No transcription history yet
              </Typography>
            </Box>
          ) : (
            <List dense>
              {displayHistory.map((result, index) => (
                <ListItem
                  key={`${result.timestamp}-${index}`}
                  sx={{
                    mb: 1,
                    backgroundColor: '#fafafa',
                    borderRadius: 1,
                    border: '1px solid #e0e0e0',
                  }}
                >
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
                        <Box sx={{ flex: 1 }}>
                          {renderWordWithConfidence(result)}
                        </Box>
                        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 0.5 }}>
                          <Chip
                            label={`${Math.round(result.confidence * 100)}%`}
                            size="small"
                            sx={{
                              backgroundColor: getConfidenceColor(result.confidence),
                              color: 'white',
                              fontSize: '0.7rem',
                              height: 20,
                              fontWeight: 'bold',
                            }}
                          />
                          {result.language && (
                            <Chip
                              icon={<TranslateIcon sx={{ fontSize: '0.8rem' }} />}
                              label={result.language.toUpperCase()}
                              size="small"
                              variant="outlined"
                              sx={{ fontSize: '0.7rem', height: 20 }}
                            />
                          )}
                        </Box>
                      </Box>
                    }
                    secondary={
                      <Collapse in={showDetails}>
                        <Box sx={{ mt: 1 }}>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                            {showTimestamps && (
                              <Typography variant="caption" color="text.secondary">
                                {formatTimestamp(result.timestamp)}
                              </Typography>
                            )}
                            <Typography
                              variant="caption"
                              sx={{ color: getConfidenceColor(result.confidence) }}
                            >
                              {getConfidenceLabel(result.confidence)} Confidence
                            </Typography>
                          </Box>
                          {result.words && showWordLevelConfidence && (
                            <Typography variant="caption" color="text.secondary">
                              Words: {result.words.length} | Avg confidence: {Math.round(result.words.reduce((sum, w) => sum + w.confidence, 0) / result.words.length * 100)}%
                            </Typography>
                          )}
                        </Box>
                      </Collapse>
                    }
                  />
                </ListItem>
              ))}
            </List>
          )}
        </Box>
      </Box>
    </Paper>
  );
};

export default TranscriptionDisplay;