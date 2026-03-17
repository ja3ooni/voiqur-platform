import React from 'react';
import {
  Card,
  CardContent,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Box,
  Chip,
  Grid,
  SelectChangeEvent,
} from '@mui/material';
import { useSelector, useDispatch } from 'react-redux';
import { RootState } from '../../store/store';
import { updateConfigModel } from '../../store/slices/configurationSlice';
import { VoiceModel } from '../../types/voiceAssistant';

const ModelSelectionPanel: React.FC = () => {
  const dispatch = useDispatch();
  const { currentConfig, availableModels } = useSelector((state: RootState) => state.configuration);

  const handleModelChange = (type: 'stt' | 'llm' | 'tts') => (event: SelectChangeEvent) => {
    const selectedModel = availableModels.find(model => model.id === event.target.value);
    if (selectedModel) {
      dispatch(updateConfigModel({ type, model: selectedModel }));
    }
  };

  const getModelsByType = (type: 'stt' | 'llm' | 'tts'): VoiceModel[] => {
    return availableModels.filter(model => model.type === type && model.isActive);
  };

  const getModelTypeLabel = (type: 'stt' | 'llm' | 'tts'): string => {
    switch (type) {
      case 'stt': return 'Speech-to-Text Model';
      case 'llm': return 'Language Model';
      case 'tts': return 'Text-to-Speech Model';
    }
  };

  if (!currentConfig) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Voice Model Selection
          </Typography>
          <Typography color="textSecondary">
            Please create a configuration first.
          </Typography>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Voice Model Selection
        </Typography>
        <Typography variant="body2" color="textSecondary" paragraph>
          Select the AI models for speech processing, dialog management, and voice synthesis.
        </Typography>

        <Grid container spacing={3}>
          {(['stt', 'llm', 'tts'] as const).map((modelType) => (
            <Grid item xs={12} md={4} key={modelType}>
              <FormControl fullWidth>
                <InputLabel>{getModelTypeLabel(modelType)}</InputLabel>
                <Select
                  value={currentConfig.models[modelType]?.id || ''}
                  label={getModelTypeLabel(modelType)}
                  onChange={handleModelChange(modelType)}
                >
                  {getModelsByType(modelType).map((model) => (
                    <MenuItem key={model.id} value={model.id}>
                      {model.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              {currentConfig.models[modelType] && (
                <Box mt={2}>
                  <Typography variant="subtitle2" gutterBottom>
                    {currentConfig.models[modelType].name}
                  </Typography>
                  <Typography variant="body2" color="textSecondary" paragraph>
                    {currentConfig.models[modelType].description}
                  </Typography>
                  <Box mb={1}>
                    <Chip
                      label={currentConfig.models[modelType].provider}
                      size="small"
                      color="primary"
                      variant="outlined"
                    />
                  </Box>
                  <Typography variant="caption" color="textSecondary">
                    Supported Languages: {currentConfig.models[modelType].languages.length}
                  </Typography>
                </Box>
              )}
            </Grid>
          ))}
        </Grid>
      </CardContent>
    </Card>
  );
};

export default ModelSelectionPanel;