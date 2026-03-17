// Voice Assistant Configuration Types

export interface VoiceModel {
  id: string;
  name: string;
  description: string;
  type: 'stt' | 'llm' | 'tts';
  languages: string[];
  provider: string;
  isActive: boolean;
}

export interface Language {
  code: string;
  name: string;
  nativeName: string;
  region: string;
  isLowResource: boolean;
}

export interface Accent {
  id: string;
  name: string;
  languageCode: string;
  region: string;
  confidence: number;
}

export interface ConversationNode {
  id: string;
  type: 'trigger' | 'response' | 'condition' | 'action';
  position: { x: number; y: number };
  data: {
    label: string;
    content?: string;
    conditions?: string[];
    actions?: string[];
  };
  connections: string[];
}

export interface ConversationFlow {
  id: string;
  name: string;
  description: string;
  nodes: ConversationNode[];
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface VoiceAssistantConfig {
  id: string;
  name: string;
  description: string;
  models: {
    stt: VoiceModel;
    llm: VoiceModel;
    tts: VoiceModel;
  };
  languages: Language[];
  primaryLanguage: string;
  accents: Accent[];
  conversationFlows: ConversationFlow[];
  settings: {
    responseLatency: number;
    confidenceThreshold: number;
    enableEmotionDetection: boolean;
    enableAccentAdaptation: boolean;
    enableLipSync: boolean;
  };
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface ConfigurationState {
  currentConfig: VoiceAssistantConfig | null;
  availableModels: VoiceModel[];
  availableLanguages: Language[];
  availableAccents: Accent[];
  isLoading: boolean;
  error: string | null;
}