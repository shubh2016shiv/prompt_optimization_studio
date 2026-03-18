/**
 * HowItWorksGuide Component
 * 
 * A visual guide explaining the four-step workflow.
 */

import { PanelHeader } from '@/components/layout';

const STEPS = [
  {
    number: '1',
    icon: '🔍',
    title: 'Analyse Gaps',
    description: 'TCRTE coverage audit — finds what\'s missing in your prompt',
  },
  {
    number: '2',
    icon: '🎯',
    title: 'Answer Questions',
    description: 'Fill gaps with targeted Q&A — no prompt knowledge needed',
  },
  {
    number: '3',
    icon: '⬡',
    title: 'Optimise',
    description: '3 production variants generated with CoRe, RAL-Writer & guards',
  },
  {
    number: '4',
    icon: '✦',
    title: 'Refine in Chat',
    description: 'AI chat has full context — iterate conversationally',
  },
];

/**
 * Guide section explaining the workflow steps.
 */
export function HowItWorksGuide() {
  return (
    <div>
      <PanelHeader icon="⟳" title="How It Works" />
      
      <div className="space-y-3">
        {STEPS.map((step) => (
          <div key={step.number} className="flex gap-2.5">
            {/* Step number circle */}
            <div
              className="w-5 h-5 shrink-0 rounded-full flex items-center justify-center text-[10.5px] font-bold mt-0.5"
              style={{
                backgroundColor: 'var(--accent-soft)',
                border: '1px solid var(--accent)30',
                color: 'var(--accent)',
              }}
            >
              {step.number}
            </div>
            
            {/* Step content */}
            <div>
              <div className="text-[12px] font-bold text-[var(--text-primary)] mb-0.5">
                {step.icon} {step.title}
              </div>
              <div className="text-[11px] text-[var(--text-tertiary)] leading-relaxed">
                {step.description}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
