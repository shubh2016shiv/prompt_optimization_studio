/**
 * ConfigurationPanel Component
 * 
 * The left panel containing all configuration inputs:
 * - Prompt input
 * - Variable declarations
 * - Provider selection
 * - Model selection
 * - API key
 * - Endpoint override
 * - How it works guide
 */

import { PanelHeader, FieldLabel } from '@/components/layout';
import { PromptInput } from './PromptInput';
import { VariableInput } from './VariableInput';
import { ProviderSelector } from './ProviderSelector';
import { ModelSelector } from './ModelSelector';
import { ApiKeyInput } from './ApiKeyInput';
import { EndpointInput } from './EndpointInput';
import { HowItWorksGuide } from './HowItWorksGuide';

/**
 * Complete configuration panel for the left sidebar.
 */
export function ConfigurationPanel() {
  return (
    <>
      {/* Prompt Section */}
      <section className="p-4 border-b border-[var(--border)]">
        <PanelHeader icon="✍" title="Prompt Input" />
        <div className="space-y-3">
          <PromptInput />
          <VariableInput />
        </div>
      </section>

      {/* Model Section */}
      <section className="p-4 border-b border-[var(--border)]">
        <PanelHeader icon="🎯" title="Target Model" />
        <div className="space-y-3">
          <div>
            <FieldLabel>Provider</FieldLabel>
            <ProviderSelector />
          </div>
          <div>
            <FieldLabel>Model</FieldLabel>
            <ModelSelector />
          </div>
          <ApiKeyInput />
          <EndpointInput />
        </div>
      </section>

      {/* How It Works Section */}
      <section className="p-4 flex-1">
        <HowItWorksGuide />
      </section>
    </>
  );
}
