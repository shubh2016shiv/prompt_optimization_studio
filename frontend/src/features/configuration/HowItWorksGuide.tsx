/**
 * HowItWorksGuide Component
 * 
 * A compact visual guide explaining the four-step workflow.
 * Descriptions are hidden behind tooltips to reduce visual noise.
 */

import { PanelHeader } from '@/components/layout';
import { Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui';

const STEPS = [
  {
    number: '1',
    icon: '🔍',
    title: 'Analyse Gaps',
    description: 'Runs a TCRTE coverage audit across 5 dimensions and scores your prompt. Identifies what\'s structurally missing before generating anything.',
  },
  {
    number: '2',
    icon: '💬',
    title: 'Answer Questions',
    description: 'Fills the identified gaps through a short targeted Q&A. No prompt engineering knowledge needed — just answer in plain language.',
  },
  {
    number: '3',
    icon: '⬡',
    title: 'Optimise',
    description: 'Generates 3 production-ready variants using CoRe, RAL-Writer, and output guards. Conservative, Structured, and Advanced — pick the right fit.',
  },
  {
    number: '4',
    icon: '✦',
    title: 'Refine in Chat',
    description: 'The AI chat is seeded with all 3 variants, your gap answers, and TCRTE scores. Iterate conversationally without re-running the full workflow.',
  },
];

/**
 * Compact guide section — title + tooltip on hover for each step.
 */
export function HowItWorksGuide() {
  return (
    <div>
      <PanelHeader icon="⟳" title="How It Works" />
      
      <div className="flex flex-col gap-1.5">
        {STEPS.map((step) => (
          <Tooltip key={step.number} delayDuration={200}>
            <TooltipTrigger asChild>
              <div
                className="flex items-center gap-2.5 px-2 py-1.5 rounded-md cursor-default transition-colors hover:bg-[var(--surface-raised)]"
              >
                {/* Step number */}
                <div
                  className="w-5 h-5 shrink-0 rounded-full flex items-center justify-center font-bold"
                  style={{
                    fontSize: 'var(--text-xs)',
                    backgroundColor: 'var(--accent-soft)',
                    border: '1px solid rgba(108, 138, 255, 0.2)',
                    color: 'var(--accent)',
                  }}
                >
                  {step.number}
                </div>
                
                {/* Title only — description is in tooltip */}
                <span
                  className="font-semibold text-[var(--text-primary)]"
                  style={{ fontSize: 'var(--text-sm)' }}
                >
                  {step.icon} {step.title}
                </span>

                {/* Info hint */}
                <span
                  className="ml-auto text-[var(--text-tertiary)]"
                  style={{ fontSize: 'var(--text-xs)' }}
                >
                  ?
                </span>
              </div>
            </TooltipTrigger>
            <TooltipContent side="right" className="max-w-[220px] leading-relaxed">
              {step.description}
            </TooltipContent>
          </Tooltip>
        ))}
      </div>
    </div>
  );
}
