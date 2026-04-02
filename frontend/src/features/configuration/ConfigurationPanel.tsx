/**
 * ConfigurationPanel Component
 *
 * Left panel with three collapsible accordion sections:
 *   1. Prompt   — textarea, variables, task type
 *   2. Model    — provider, model, framework, API key, endpoint
 *   3. Guide    — how it works reference
 *
 * Task type and framework selectors are moved here from the workflow panel,
 * where they conceptually belong (they are configuration, not workflow controls).
 */

import { useState } from 'react';
import { m, AnimatePresence } from 'framer-motion';
import { PromptInput } from './PromptInput';
import { VariableInput } from './VariableInput';
import { ProviderSelector } from './ProviderSelector';
import { ModelSelector } from './ModelSelector';
import { ApiKeyInput } from './ApiKeyInput';
import { EndpointInput } from './EndpointInput';
import { HowItWorksGuide } from './HowItWorksGuide';
import { TaskTypeSelector } from '@/features/workflow/controls/TaskTypeSelector';
import { FrameworkSelector } from '@/features/workflow/controls/FrameworkSelector';

// ─── Accordion Section ─────────────────────────────────────────
interface AccordionSectionProps {
  id: string;
  title: string;
  icon: string;
  badge?: string;
  badgeColor?: string;
  isOpen: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}

function AccordionSection({
  title,
  icon,
  badge,
  badgeColor = 'var(--accent)',
  isOpen,
  onToggle,
  children,
}: AccordionSectionProps) {
  return (
    <div
      className="border-b border-[var(--border)]"
      style={{ backgroundColor: isOpen ? 'transparent' : undefined }}
    >
      {/* Header trigger */}
      <button
        onClick={onToggle}
        className="w-full px-4 py-3 flex items-center gap-2.5 text-left transition-colors hover:bg-[var(--surface-raised)] focus:outline-none"
        aria-expanded={isOpen}
      >
        {/* Icon */}
        <span style={{ fontSize: '14px' }}>{icon}</span>

        {/* Title */}
        <span
          className="flex-1 font-semibold"
          style={{ fontSize: 'var(--text-sm)', color: 'var(--text-primary)' }}
        >
          {title}
        </span>

        {/* Optional badge */}
        {badge && (
          <span
            className="px-1.5 py-0.5 rounded font-bold font-mono"
            style={{
              fontSize: '9px',
              color: badgeColor,
              backgroundColor: `${badgeColor}18`,
              border: `1px solid ${badgeColor}30`,
              letterSpacing: '0.3px',
            }}
          >
            {badge}
          </span>
        )}

        {/* Chevron */}
        <m.span
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ duration: 0.2 }}
          style={{ fontSize: '10px', color: 'var(--text-tertiary)', display: 'block' }}
        >
          ▾
        </m.span>
      </button>

      {/* Content */}
      <AnimatePresence initial={false}>
        {isOpen && (
          <m.div
            key="content"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: [0.4, 0, 0.2, 1] }}
            style={{ overflow: 'hidden' }}
          >
            <div className="px-4 pb-4 pt-1 space-y-4 accordion-content">
              {children}
            </div>
          </m.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ─── Section title label ───────────────────────────────────────
function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="mb-1.5 font-semibold"
      style={{ fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)', letterSpacing: '0.5px', textTransform: 'uppercase' }}
    >
      {children}
    </div>
  );
}

// ─── ConfigurationPanel ────────────────────────────────────────
export function ConfigurationPanel() {
  // Start with Prompt open, others closed
  const [openSection, setOpenSection] = useState<string>('prompt');

  const toggle = (id: string) =>
    setOpenSection((prev) => (prev === id ? '' : id));

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Panel title */}
      <div
        className="px-4 py-2.5 shrink-0 flex items-center gap-2"
        style={{ borderBottom: '1px solid var(--border)', backgroundColor: 'var(--surface)' }}
      >
        <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-tertiary)', letterSpacing: '0.8px', textTransform: 'uppercase' }}>
          Configuration
        </span>
        <span
          className="ml-auto px-2 py-0.5 rounded-full font-bold"
          style={{
            fontSize: '9px',
            color: 'var(--teal)',
            backgroundColor: 'var(--teal-soft)',
            border: '1px solid var(--teal-glow)',
            letterSpacing: '0.5px',
          }}
        >
          Step 1
        </span>
      </div>

      {/* Accordion sections */}
      <div className="flex-1 overflow-y-auto">
        {/* ① Prompt */}
        <AccordionSection
          id="prompt"
          title="Your Prompt"
          icon="✏️"
          badge="required"
          badgeColor="var(--teal)"
          isOpen={openSection === 'prompt'}
          onToggle={() => toggle('prompt')}
        >
          <PromptInput />
          <div>
            <FieldLabel>Input Variables</FieldLabel>
            <VariableInput />
          </div>
          <div>
            <FieldLabel>Task Type</FieldLabel>
            <TaskTypeSelector compact />
          </div>
        </AccordionSection>

        {/* ② Model */}
        <AccordionSection
          id="model"
          title="Target Model"
          icon="🧠"
          isOpen={openSection === 'model'}
          onToggle={() => toggle('model')}
        >
          <div>
            <FieldLabel>Provider</FieldLabel>
            <ProviderSelector />
          </div>
          <div>
            <FieldLabel>Model</FieldLabel>
            <ModelSelector />
          </div>
          <div>
            <FieldLabel>Framework</FieldLabel>
            <FrameworkSelector compact />
          </div>
          <ApiKeyInput />
          <EndpointInput />
        </AccordionSection>

        {/* ③ Guide */}
        <AccordionSection
          id="guide"
          title="How It Works"
          icon="⟳"
          isOpen={openSection === 'guide'}
          onToggle={() => toggle('guide')}
        >
          <HowItWorksGuide />
        </AccordionSection>
      </div>
    </div>
  );
}
