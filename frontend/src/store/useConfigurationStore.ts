/**
 * Configuration Store
 * 
 * Manages the left panel state: raw prompt, variables, provider, model, API key.
 * Uses Zustand for efficient state management with selective re-renders.
 */

import { create } from 'zustand';
import type { ProviderId, Model } from '@/types';
import { 
  PROVIDERS, 
  DEFAULT_PROVIDER_ID, 
  DEFAULT_MODEL_ID 
} from '@/constants';

interface ConfigurationState {
  /** The raw prompt text to optimize */
  rawPrompt: string;
  /** Declared input variables (e.g., "{{documents}} - array of PDFs") */
  inputVariables: string;
  /** Selected LLM provider */
  providerId: ProviderId;
  /** Selected model ID */
  modelId: string;
  /** API key for the selected provider */
  apiKey: string;
  /** Custom API endpoint override (optional) */
  endpointOverride: string;
  /** Whether the API key is visible in the input */
  showApiKey: boolean;
}

interface ConfigurationActions {
  /** Update the raw prompt */
  setRawPrompt: (prompt: string) => void;
  /** Update the input variables */
  setInputVariables: (variables: string) => void;
  /** Change the provider (resets model to first available) */
  setProvider: (providerId: ProviderId) => void;
  /** Change the model */
  setModelId: (modelId: string) => void;
  /** Update the API key */
  setApiKey: (key: string) => void;
  /** Update the endpoint override */
  setEndpointOverride: (endpoint: string) => void;
  /** Toggle API key visibility */
  toggleShowApiKey: () => void;
  /** Reset all configuration to defaults */
  resetConfiguration: () => void;
}

type ConfigurationStore = ConfigurationState & ConfigurationActions;

const initialState: ConfigurationState = {
  rawPrompt: '',
  inputVariables: '',
  providerId: DEFAULT_PROVIDER_ID,
  modelId: DEFAULT_MODEL_ID,
  apiKey: '',
  endpointOverride: '',
  showApiKey: false,
};

/**
 * Zustand store for configuration state.
 * 
 * Usage:
 * ```tsx
 * const rawPrompt = useConfigurationStore(state => state.rawPrompt);
 * const setRawPrompt = useConfigurationStore(state => state.setRawPrompt);
 * ```
 */
export const useConfigurationStore = create<ConfigurationStore>((set) => ({
  ...initialState,

  setRawPrompt: (prompt) => set({ rawPrompt: prompt }),
  
  setInputVariables: (variables) => set({ inputVariables: variables }),
  
  setProvider: (providerId) => {
    const provider = PROVIDERS[providerId];
    const firstModel = provider?.models[0];
    set({ 
      providerId, 
      modelId: firstModel?.id ?? DEFAULT_MODEL_ID,
      apiKey: '', // Clear API key when changing provider
      endpointOverride: '',
    });
  },
  
  setModelId: (modelId) => set({ modelId }),
  
  setApiKey: (key) => set({ apiKey: key }),
  
  setEndpointOverride: (endpoint) => set({ endpointOverride: endpoint }),
  
  toggleShowApiKey: () => set((state) => ({ showApiKey: !state.showApiKey })),
  
  resetConfiguration: () => set(initialState),
}));

/**
 * Selector to get the current provider object.
 */
export function useCurrentProvider() {
  const providerId = useConfigurationStore((state) => state.providerId);
  return PROVIDERS[providerId];
}

/**
 * Selector to get the current model object.
 */
export function useCurrentModel(): Model | null {
  const providerId = useConfigurationStore((state) => state.providerId);
  const modelId = useConfigurationStore((state) => state.modelId);
  const provider = PROVIDERS[providerId];
  return provider?.models.find((m) => m.id === modelId) ?? null;
}

/**
 * Selector to check if the current model is a reasoning model.
 */
export function useIsReasoningModel(): boolean {
  const model = useCurrentModel();
  return model?.reasoning ?? false;
}

/**
 * Selector to check if configuration is valid for API calls.
 */
export function useIsConfigurationValid(): boolean {
  const rawPrompt = useConfigurationStore((state) => state.rawPrompt);
  const apiKey = useConfigurationStore((state) => state.apiKey);
  return rawPrompt.trim().length > 0 && apiKey.trim().length > 0;
}
