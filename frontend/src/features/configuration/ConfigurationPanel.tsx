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

function StepBadge({ step }: { step: number }) {
  return (
    <span
      className="inline-flex items-center justify-center w-4 h-4 rounded-full font-bold shrink-0"
      style={{
        fontSize: 'var(--text-xs)',
        backgroundColor: 'var(--primary-action-soft)',
        color: 'var(--primary-action)',
        border: '1px solid var(--primary-action-glow)',
      }}
    >
      {step}
    </span>
  );
}

/**
 * Complete configuration panel for the left sidebar.
 */
export function ConfigurationPanel() {
  return (
    <>
      {/* Step 1 — Prompt */}
      <section className="p-4 border-b border-[var(--border)]">
        <PanelHeader
          icon={<StepBadge step={1} />}
          title="Your Prompt"
        />
        <div className="space-y-3">
          <PromptInput />
          <VariableInput />
        </div>
      </section>

      {/* Step 2 — Model */}
      <section className="p-4 border-b border-[var(--border)]">
        <PanelHeader
          icon={<StepBadge step={2} />}
          title="Target Model"
        />
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

      {/* How It Works — collapsible reference */}
      <section className="p-4 flex-1">
        <HowItWorksGuide />
      </section>
    </>
  );
}
