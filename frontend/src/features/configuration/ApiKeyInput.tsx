/**
 * ApiKeyInput Component
 * 
 * Secure input for the LLM provider API key with show/hide toggle.
 */

import { Input } from '@/components/ui';
import { FieldLabel } from '@/components/layout';
import { useConfigurationStore, useCurrentProvider } from '@/store';

/**
 * API key input with visibility toggle.
 */
export function ApiKeyInput() {
  const apiKey = useConfigurationStore((state) => state.apiKey);
  const setApiKey = useConfigurationStore((state) => state.setApiKey);
  const showApiKey = useConfigurationStore((state) => state.showApiKey);
  const toggleShowApiKey = useConfigurationStore((state) => state.toggleShowApiKey);
  const provider = useCurrentProvider();

  return (
    <div>
      <FieldLabel required>{provider?.keyHint || 'API Key'}</FieldLabel>
      <Input
        type={showApiKey ? 'text' : 'password'}
        value={apiKey}
        onChange={(e) => setApiKey(e.target.value)}
        placeholder={provider?.keyPlaceholder}
        style={{ color: apiKey ? provider?.color : undefined }}
        rightIcon={
          <button
            type="button"
            onClick={toggleShowApiKey}
            className="text-[10.5px] text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] transition-colors"
          >
            {showApiKey ? 'hide' : 'show'}
          </button>
        }
      />
    </div>
  );
}
