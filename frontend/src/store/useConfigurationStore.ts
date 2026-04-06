/**
 * Configuration Store
 * 
 * Manages the left panel state: raw prompt, variables, provider, model, API key.
 * Uses Zustand for efficient state management with selective re-renders.
 */

import { create } from 'zustand';
import type { ProviderId, Model, InputVariableRow, InputVariablesMode } from '@/types';
import { 
  PROVIDERS, 
  DEFAULT_PROVIDER_ID, 
  DEFAULT_MODEL_ID 
} from '@/constants';

function createRowId() {
  return `var_${Math.random().toString(36).slice(2, 9)}`;
}

function createEmptyVariableRow(): InputVariableRow {
  return {
    id: createRowId(),
    name: '',
    description: '',
  };
}

function normalizeVariableName(name: string): string {
  return name.replace(/[{}]/g, '').trim();
}

export function serializeInputVariables(
  mode: InputVariablesMode,
  raw: string,
  rows: InputVariableRow[]
): string | undefined {
  if (mode === 'raw') {
    const trimmed = raw.trim();
    return trimmed.length > 0 ? trimmed : undefined;
  }

  const lines = rows
    .map((row) => {
      const cleanName = normalizeVariableName(row.name);
      const cleanDescription = row.description.trim();

      if (!cleanName && !cleanDescription) {
        return null;
      }

      if (cleanName && cleanDescription) {
        return `{{${cleanName}}} - ${cleanDescription}`;
      }

      if (cleanName) {
        return `{{${cleanName}}}`;
      }

      return cleanDescription;
    })
    .filter((line): line is string => Boolean(line));

  return lines.length > 0 ? lines.join('\n') : undefined;
}

interface ConfigurationState {
  /** The raw prompt text to optimize */
  rawPrompt: string;
  /** Freeform input variables text (raw mode fallback) */
  inputVariablesRaw: string;
  /** Structured input variables for row mode */
  inputVariableRows: InputVariableRow[];
  /** Current input variables editor mode */
  inputVariablesMode: InputVariablesMode;
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
  /** Update freeform input variables */
  setInputVariablesRaw: (variables: string) => void;
  /** Switch input variables editor mode */
  setInputVariablesMode: (mode: InputVariablesMode) => void;
  /** Add a new structured variable row */
  addInputVariableRow: () => void;
  /** Update a structured variable row */
  updateInputVariableRow: (
    id: string,
    patch: Partial<Pick<InputVariableRow, 'name' | 'description'>>
  ) => void;
  /** Remove a structured variable row */
  removeInputVariableRow: (id: string) => void;
  /** Replace all structured variable rows */
  setInputVariableRows: (rows: InputVariableRow[]) => void;
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
  inputVariablesRaw: '',
  inputVariableRows: [createEmptyVariableRow()],
  inputVariablesMode: 'rows',
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
  
  setInputVariablesRaw: (variables) => set({ inputVariablesRaw: variables }),

  setInputVariablesMode: (mode) => set({ inputVariablesMode: mode }),

  addInputVariableRow: () =>
    set((state) => ({
      inputVariableRows: [...state.inputVariableRows, createEmptyVariableRow()],
    })),

  updateInputVariableRow: (id, patch) =>
    set((state) => ({
      inputVariableRows: state.inputVariableRows.map((row) =>
        row.id === id ? { ...row, ...patch } : row
      ),
    })),

  removeInputVariableRow: (id) =>
    set((state) => {
      const nextRows = state.inputVariableRows.filter((row) => row.id !== id);
      return {
        inputVariableRows: nextRows.length > 0 ? nextRows : [createEmptyVariableRow()],
      };
    }),

  setInputVariableRows: (rows) =>
    set({
      inputVariableRows: rows.length > 0 ? rows : [createEmptyVariableRow()],
    }),
  
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
 * Selector to get serialized input variables for API payloads.
 */
export function useSerializedInputVariables(): string | undefined {
  return useConfigurationStore((state) =>
    serializeInputVariables(
      state.inputVariablesMode,
      state.inputVariablesRaw,
      state.inputVariableRows
    )
  );
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
