/**
 * ConfigurationPanel Component
 *
 * Left panel with prompt, model, and guide sections.
 */

import { useState } from 'react';
import { m, AnimatePresence } from 'framer-motion';
import { ChevronRight } from 'lucide-react';
import { PromptInput } from './PromptInput';
import { VariableInput } from './VariableInput';
import { ProviderSelector } from './ProviderSelector';
import { ModelSelector } from './ModelSelector';
import { ApiKeyInput } from './ApiKeyInput';
import { EndpointInput } from './EndpointInput';
import { HowItWorksGuide } from './HowItWorksGuide';
import { TaskTypeSelector } from '@/features/workflow/controls/TaskTypeSelector';
import { FrameworkSelector } from '@/features/workflow/controls/FrameworkSelector';
import { useCurrentModel } from '@/store';

interface AccordionSectionProps {
  id: string;
  title: string;
  subtitle?: string;
  isOpen: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}

function AccordionSection({
  title,
  subtitle,
  isOpen,
  onToggle,
  children,
}: AccordionSectionProps) {
  return (
    <div
      className="rounded-xl overflow-hidden min-w-0 shadow-sm"
      style={{
        backgroundColor: 'var(--surface-raised)',
        border: '1px solid var(--border)',
      }}
    >
      <button
        onClick={onToggle}
        className="w-full min-w-0 px-5 py-4 flex items-center gap-3 text-left transition-colors hover:bg-[var(--surface-overlay)] focus:outline-none"
        aria-expanded={isOpen}
      >
        <m.div
          animate={{ rotate: isOpen ? 90 : 0 }}
          transition={{ type: 'spring', stiffness: 300, damping: 25 }}
          className="flex items-center justify-center"
        >
          <ChevronRight size={16} className="text-[var(--text-tertiary)]" />
        </m.div>

        <div className="min-w-0 flex-1">
          <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
            {title}
          </div>
          {!isOpen && subtitle && (
            <div
              className="truncate"
              style={{ fontSize: '11px', color: 'var(--text-tertiary)', marginTop: 1 }}
              title={subtitle}
            >
              {subtitle}
            </div>
          )}
        </div>
      </button>

      <AnimatePresence initial={false}>
        {isOpen && (
          <m.div
            key="content"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 300, damping: 26, opacity: { duration: 0.2 } }}
            style={{ overflow: 'hidden' }}
          >
            <div className="px-5 pb-5 pt-1 accordion-content space-y-5 min-w-0">{children}</div>
          </m.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="mb-1.5"
      style={{
        fontSize: '10px',
        color: 'var(--text-tertiary)',
        fontWeight: 700,
        letterSpacing: '0.06em',
        textTransform: 'uppercase',
      }}
    >
      {children}
    </div>
  );
}

function FieldName({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ fontSize: '12px', fontWeight: 500, color: 'var(--text-primary)', marginBottom: 6 }}>
      {children}
    </div>
  );
}

export function ConfigurationPanel() {
  const [openSection, setOpenSection] = useState<string>('prompt');
  const currentModel = useCurrentModel();

  const toggle = (id: string) =>
    setOpenSection((prev) => (prev === id ? '' : id));

  return (
    <div className="flex flex-col h-full overflow-hidden min-w-0" style={{ backgroundColor: 'var(--surface-2)' }}>
      <div
        className="shrink-0 px-3.5 py-3 flex items-center gap-2"
        style={{ borderBottom: '1px solid var(--border-subtle)' }}
      >
        <span
          style={{
            fontSize: '10px',
            fontWeight: 700,
            color: 'var(--text-tertiary)',
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
          }}
        >
          Configuration
        </span>
        <span
          className="ml-auto px-2 py-0.5 rounded-full"
          style={{
            fontSize: '9px',
            fontWeight: 700,
            color: 'var(--teal)',
            backgroundColor: 'var(--teal-soft)',
            border: '1px solid rgba(45, 212, 191, 0.35)',
          }}
        >
          Step 1
        </span>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-5 min-w-0">
        <AccordionSection
          id="prompt"
          title="Your Prompt"
          isOpen={openSection === 'prompt'}
          onToggle={() => toggle('prompt')}
        >
          <div>
            <FieldName>Your Prompt</FieldName>
            <PromptInput />
          </div>

          <div>
            <SectionLabel>Input Variables</SectionLabel>
            <VariableInput />
          </div>

          <div>
            <SectionLabel>Ask Type</SectionLabel>
            <TaskTypeSelector compact />
          </div>
        </AccordionSection>

        <AccordionSection
          id="model"
          title="Target Model"
          subtitle={currentModel?.label}
          isOpen={openSection === 'model'}
          onToggle={() => toggle('model')}
        >
          <div>
            <SectionLabel>Provider</SectionLabel>
            <ProviderSelector />
          </div>

          <div>
            <SectionLabel>Model</SectionLabel>
            <ModelSelector />
          </div>

          <div>
            <SectionLabel>Framework</SectionLabel>
            <FrameworkSelector compact />
          </div>

          <ApiKeyInput />
          <EndpointInput />
        </AccordionSection>

        <div
          className="rounded-xl p-5 shadow-sm"
          style={{
            backgroundColor: 'var(--surface-raised)',
            border: '1px solid var(--border)',
          }}
        >
          <SectionLabel>How It Works</SectionLabel>
          <HowItWorksGuide />
        </div>
      </div>
    </div>
  );
}
