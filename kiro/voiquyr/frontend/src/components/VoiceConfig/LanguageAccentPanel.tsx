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
  FormControlLabel,
  Checkbox,
  SelectChangeEvent,
  Divider,
} from '@mui/material';
import { useSelector, useDispatch } from 'react-redux';
import { RootState } from '../../store/store';
import {
  updateConfigLanguages,
  updatePrimaryLanguage,
  updateConfigAccents,
} from '../../store/slices/configurationSlice';
import { Language, Accent } from '../../types/voiceAssistant';

const LanguageAccentPanel: React.FC = () => {
  const dispatch = useDispatch();
  const { currentConfig, availableLanguages, availableAccents } = useSelector(
    (state: RootState) => state.configuration
  );

  const handlePrimaryLanguageChange = (event: SelectChangeEvent) => {
    dispatch(updatePrimaryLanguage(event.target.value));
  };

  const handleLanguageToggle = (language: Language) => {
    if (!currentConfig) return;

    const isSelected = currentConfig.languages.some(lang => lang.code === language.code);
    let updatedLanguages: Language[];

    if (isSelected) {
      // Don't allow removing the primary language
      if (language.code === currentConfig.primaryLanguage) return;
      updatedLanguages = currentConfig.languages.filter(lang => lang.code !== language.code);
    } else {
      updatedLanguages = [...currentConfig.languages, language];
    }

    dispatch(updateConfigLanguages(updatedLanguages));
  };

  const handleAccentToggle = (accent: Accent) => {
    if (!currentConfig) return;

    const isSelected = currentConfig.accents.some(acc => acc.id === accent.id);
    let updatedAccents: Accent[];

    if (isSelected) {
      updatedAccents = currentConfig.accents.filter(acc => acc.id !== accent.id);
    } else {
      updatedAccents = [...currentConfig.accents, accent];
    }

    dispatch(updateConfigAccents(updatedAccents));
  };

  const getAvailableAccentsForLanguages = (): Accent[] => {
    if (!currentConfig) return [];
    const selectedLanguageCodes = currentConfig.languages.map(lang => lang.code);
    return availableAccents.filter(accent => 
      selectedLanguageCodes.includes(accent.languageCode)
    );
  };

  if (!currentConfig) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Language & Accent Configuration
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
          Language & Accent Configuration
        </Typography>
        <Typography variant="body2" color="textSecondary" paragraph>
          Configure supported languages and regional accents for your voice assistant.
        </Typography>

        <Grid container spacing={3}>
          {/* Primary Language Selection */}
          <Grid item xs={12} md={6}>
            <FormControl fullWidth>
              <InputLabel>Primary Language</InputLabel>
              <Select
                value={currentConfig.primaryLanguage}
                label="Primary Language"
                onChange={handlePrimaryLanguageChange}
              >
                {currentConfig.languages.map((language) => (
                  <MenuItem key={language.code} value={language.code}>
                    {language.name} ({language.nativeName})
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>

          {/* Selected Languages Display */}
          <Grid item xs={12} md={6}>
            <Typography variant="subtitle2" gutterBottom>
              Selected Languages ({currentConfig.languages.length})
            </Typography>
            <Box display="flex" flexWrap="wrap" gap={1}>
              {currentConfig.languages.map((language) => (
                <Chip
                  key={language.code}
                  label={`${language.name} (${language.code.toUpperCase()})`}
                  color={language.code === currentConfig.primaryLanguage ? 'primary' : 'default'}
                  variant={language.isLowResource ? 'outlined' : 'filled'}
                  size="small"
                />
              ))}
            </Box>
          </Grid>
        </Grid>

        <Divider sx={{ my: 3 }} />

        {/* Available Languages */}
        <Typography variant="h6" gutterBottom>
          Available Languages
        </Typography>
        <Grid container spacing={2}>
          {availableLanguages.map((language) => {
            const isSelected = currentConfig.languages.some(lang => lang.code === language.code);
            const isPrimary = language.code === currentConfig.primaryLanguage;
            
            return (
              <Grid item xs={12} sm={6} md={4} key={language.code}>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={isSelected}
                      onChange={() => handleLanguageToggle(language)}
                      disabled={isPrimary} // Can't uncheck primary language
                    />
                  }
                  label={
                    <Box>
                      <Typography variant="body2">
                        {language.name} ({language.nativeName})
                      </Typography>
                      <Typography variant="caption" color="textSecondary">
                        {language.region}
                        {language.isLowResource && ' • Low Resource'}
                        {isPrimary && ' • Primary'}
                      </Typography>
                    </Box>
                  }
                />
              </Grid>
            );
          })}
        </Grid>

        <Divider sx={{ my: 3 }} />

        {/* Accent Configuration */}
        <Typography variant="h6" gutterBottom>
          Regional Accents
        </Typography>
        <Typography variant="body2" color="textSecondary" paragraph>
          Select regional accents for improved speech recognition accuracy.
        </Typography>

        <Grid container spacing={2}>
          {getAvailableAccentsForLanguages().map((accent) => {
            const isSelected = currentConfig.accents.some(acc => acc.id === accent.id);
            
            return (
              <Grid item xs={12} sm={6} md={4} key={accent.id}>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={isSelected}
                      onChange={() => handleAccentToggle(accent)}
                    />
                  }
                  label={
                    <Box>
                      <Typography variant="body2">
                        {accent.name}
                      </Typography>
                      <Typography variant="caption" color="textSecondary">
                        {accent.region} • Confidence: {(accent.confidence * 100).toFixed(0)}%
                      </Typography>
                    </Box>
                  }
                />
              </Grid>
            );
          })}
        </Grid>

        {currentConfig.accents.length > 0 && (
          <Box mt={2}>
            <Typography variant="subtitle2" gutterBottom>
              Selected Accents ({currentConfig.accents.length})
            </Typography>
            <Box display="flex" flexWrap="wrap" gap={1}>
              {currentConfig.accents.map((accent) => (
                <Chip
                  key={accent.id}
                  label={accent.name}
                  size="small"
                  color="secondary"
                />
              ))}
            </Box>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default LanguageAccentPanel;