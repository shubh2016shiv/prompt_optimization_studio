/**
 * IdleState Component
 *
 * Centered onboarding view with capability bar and 2x2 workflow grid.
 */

import { m } from 'framer-motion';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui';

const FLOW_STEPS = [
  {
    id: 'analyse',
    number: '01',
    label: 'Analyse',
    description: 'Run TCRTE gap audit across all five dimensions.',
    meta: '~30s',
    color: 'var(--teal)',
    soft: 'var(--teal-soft)',
  },
  {
    id: 'interview',
    number: '02',
    label: 'Interview',
    description: 'Answer focused questions to close missing context.',
    meta: '3-8 prompts',
    color: 'var(--accent)',
    soft: 'var(--accent-soft)',
  },
  {
    id: 'optimise',
    number: '03',
    label: 'Optimise',
    description: 'Generate three production-ready prompt variants.',
    meta: '~20s',
    color: 'var(--purple)',
    soft: 'var(--purple-soft)',
  },
  {
    id: 'refine',
    number: '04',
    label: 'Refine',
    description: 'Iterate in chat with full workflow context loaded.',
    meta: 'Conversational',
    color: 'var(--pink)',
    soft: 'var(--pink-soft)',
  },
];

const CAPABILITIES = [
  {
    label: 'TCRTE',
    tooltip: 'Five-dimension coverage framework: Task, Context, Role, Tone, and Execution.',
  },
  {
    label: '9 Frameworks',
    tooltip: 'Includes KERNEL, XML Structured, TextGrad, CREATE, and additional optimizers.',
  },
  {
    label: '3 Variants',
    tooltip: 'Each run produces Conservative, Structured, and Advanced prompt variants.',
  },
  {
    label: 'CoRe + RAL',
    tooltip: 'Context Repetition and RAL writer strategies for attention blind spots.',
  },
  {
    label: 'Auto-Select',
    tooltip: 'Automatically picks framework strategy based on task type and model.',
  },
];

export function IdleState() {
  return (
    <m.div
      className="h-full overflow-y-auto px-6 py-6"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.25 }}
    >
      <div className="mx-auto" style={{ maxWidth: 820 }}>
        <div className="text-center mb-4">
          <h2 style={{ fontSize: '18px', color: 'var(--text-primary)', fontWeight: 700 }}>
            Engineering-grade prompt optimisation
          </h2>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: 8 }}>
            Paste your prompt in the left panel, then run a full TCRTE audit before generating variants.
          </p>
        </div>

        <div className="flex flex-wrap items-center justify-center gap-2 mb-5">
          {CAPABILITIES.map((capability) => (
            <Tooltip key={capability.label} delayDuration={120}>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  className="px-2.5 py-1 rounded-full"
                  style={{
                    fontSize: '12px',
                    color: 'var(--teal)',
                    backgroundColor: 'rgba(45, 212, 191, 0.14)',
                    border: '1px solid rgba(45, 212, 191, 0.28)',
                  }}
                >
                  {capability.label}
                </button>
              </TooltipTrigger>
              <TooltipContent side="top" className="max-w-[250px] leading-relaxed">
                {capability.tooltip}
              </TooltipContent>
            </Tooltip>
          ))}
        </div>

        <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))' }}>
          {FLOW_STEPS.map((step, index) => (
            <m.div
              key={step.id}
              className="rounded-xl p-3.5"
              style={{
                minHeight: 108,
                backgroundColor: 'var(--surface-3)',
                border: `1px solid ${step.color}40`,
                borderLeft: `3px solid ${step.color}`,
              }}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25, delay: index * 0.06 }}
            >
              <div className="flex items-start justify-between gap-2">
                <span
                  className="px-1.5 py-0.5 rounded"
                  style={{
                    fontSize: '10px',
                    color: step.color,
                    backgroundColor: step.soft,
                    border: `1px solid ${step.color}50`,
                    fontWeight: 700,
                  }}
                >
                  {step.number}
                </span>
                <span style={{ fontSize: '10px', color: 'var(--text-tertiary)' }}>{step.meta}</span>
              </div>

              <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', marginTop: 10 }}>
                {step.label}
              </div>
              <p
                style={{
                  fontSize: '12px',
                  color: 'var(--text-secondary)',
                  lineHeight: 1.5,
                  marginTop: 6,
                }}
              >
                {step.description}
              </p>
            </m.div>
          ))}
        </div>
      </div>
    </m.div>
  );
}
