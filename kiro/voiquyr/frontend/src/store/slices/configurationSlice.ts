import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { ConfigurationState, VoiceAssistantConfig, VoiceModel, Language, Accent } from '../../types/voiceAssistant';

const initialState: ConfigurationState = {
  currentConfig: null,
  availableModels: [
    {
      id: 'mistral-voxtral-small',
      name: 'Mistral Voxtral Small',
      description: 'High-accuracy speech recognition for EU languages',
      type: 'stt',
      languages: ['en', 'fr', 'de', 'es', 'it', 'pt', 'nl', 'pl', 'cs', 'hr', 'et', 'mt'],
      provider: 'Mistral AI',
      isActive: true,
    },
    {
      id: 'mistral-small-3.1',
      name: 'Mistral Small 3.1',
      description: 'Advanced dialog management and reasoning',
      type: 'llm',
      languages: ['en', 'fr', 'de', 'es', 'it', 'pt', 'nl', 'pl', 'cs', 'hr', 'et', 'mt'],
      provider: 'Mistral AI',
      isActive: true,
    },
    {
      id: 'xtts-v2',
      name: 'XTTS-v2',
      description: 'Natural voice synthesis with EU accent support',
      type: 'tts',
      languages: ['en', 'fr', 'de', 'es', 'it', 'pt', 'nl', 'pl', 'cs', 'hr', 'et', 'mt'],
      provider: 'Coqui AI',
      isActive: true,
    },
  ],
  availableLanguages: [
    { code: 'en', name: 'English', nativeName: 'English', region: 'Global', isLowResource: false },
    { code: 'fr', name: 'French', nativeName: 'Français', region: 'France', isLowResource: false },
    { code: 'de', name: 'German', nativeName: 'Deutsch', region: 'Germany', isLowResource: false },
    { code: 'es', name: 'Spanish', nativeName: 'Español', region: 'Spain', isLowResource: false },
    { code: 'it', name: 'Italian', nativeName: 'Italiano', region: 'Italy', isLowResource: false },
    { code: 'pt', name: 'Portuguese', nativeName: 'Português', region: 'Portugal', isLowResource: false },
    { code: 'nl', name: 'Dutch', nativeName: 'Nederlands', region: 'Netherlands', isLowResource: false },
    { code: 'pl', name: 'Polish', nativeName: 'Polski', region: 'Poland', isLowResource: false },
    { code: 'cs', name: 'Czech', nativeName: 'Čeština', region: 'Czech Republic', isLowResource: true },
    { code: 'hr', name: 'Croatian', nativeName: 'Hrvatski', region: 'Croatia', isLowResource: true },
    { code: 'et', name: 'Estonian', nativeName: 'Eesti', region: 'Estonia', isLowResource: true },
    { code: 'mt', name: 'Maltese', nativeName: 'Malti', region: 'Malta', isLowResource: true },
  ],
  availableAccents: [
    { id: 'en-gb', name: 'British English', languageCode: 'en', region: 'United Kingdom', confidence: 0.95 },
    { id: 'en-us', name: 'American English', languageCode: 'en', region: 'United States', confidence: 0.95 },
    { id: 'fr-fr', name: 'Metropolitan French', languageCode: 'fr', region: 'France', confidence: 0.92 },
    { id: 'de-de', name: 'Standard German', languageCode: 'de', region: 'Germany', confidence: 0.93 },
    { id: 'es-es', name: 'Castilian Spanish', languageCode: 'es', region: 'Spain', confidence: 0.91 },
  ],
  isLoading: false,
  error: null,
};

const configurationSlice = createSlice({
  name: 'configuration',
  initialState,
  reducers: {
    setCurrentConfig: (state, action: PayloadAction<VoiceAssistantConfig>) => {
      state.currentConfig = action.payload;
    },
    updateConfigModel: (state, action: PayloadAction<{ type: 'stt' | 'llm' | 'tts'; model: VoiceModel }>) => {
      if (state.currentConfig) {
        state.currentConfig.models[action.payload.type] = action.payload.model;
        state.currentConfig.updatedAt = new Date().toISOString();
      }
    },
    updateConfigLanguages: (state, action: PayloadAction<Language[]>) => {
      if (state.currentConfig) {
        state.currentConfig.languages = action.payload;
        state.currentConfig.updatedAt = new Date().toISOString();
      }
    },
    updatePrimaryLanguage: (state, action: PayloadAction<string>) => {
      if (state.currentConfig) {
        state.currentConfig.primaryLanguage = action.payload;
        state.currentConfig.updatedAt = new Date().toISOString();
      }
    },
    updateConfigAccents: (state, action: PayloadAction<Accent[]>) => {
      if (state.currentConfig) {
        state.currentConfig.accents = action.payload;
        state.currentConfig.updatedAt = new Date().toISOString();
      }
    },
    updateConfigSettings: (state, action: PayloadAction<Partial<VoiceAssistantConfig['settings']>>) => {
      if (state.currentConfig) {
        state.currentConfig.settings = { ...state.currentConfig.settings, ...action.payload };
        state.currentConfig.updatedAt = new Date().toISOString();
      }
    },
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },
    createNewConfig: (state, action: PayloadAction<{ name: string; description: string }>) => {
      const newConfig: VoiceAssistantConfig = {
        id: `config-${Date.now()}`,
        name: action.payload.name,
        description: action.payload.description,
        models: {
          stt: state.availableModels.find(m => m.type === 'stt')!,
          llm: state.availableModels.find(m => m.type === 'llm')!,
          tts: state.availableModels.find(m => m.type === 'tts')!,
        },
        languages: [state.availableLanguages[0]], // Default to English
        primaryLanguage: 'en',
        accents: [state.availableAccents[0]], // Default to first accent
        conversationFlows: [],
        settings: {
          responseLatency: 100,
          confidenceThreshold: 0.8,
          enableEmotionDetection: true,
          enableAccentAdaptation: true,
          enableLipSync: false,
        },
        isActive: false,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
      state.currentConfig = newConfig;
    },
  },
});

export const {
  setCurrentConfig,
  updateConfigModel,
  updateConfigLanguages,
  updatePrimaryLanguage,
  updateConfigAccents,
  updateConfigSettings,
  setLoading,
  setError,
  createNewConfig,
} = configurationSlice.actions;

export default configurationSlice.reducer;