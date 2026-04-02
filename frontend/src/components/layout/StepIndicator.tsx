/**
 * StepIndicator Component
 *
 * Shows the 4-phase workflow progress in the header.
 * Active step glows teal, completed steps show a checkmark, pending steps are muted.
 */

import { m, AnimatePresence } from 'framer-motion';
import type { WorkflowPhase } from '@/types';

interface StepIndicatorProps {
  phase: WorkflowPhase;
}

const STEPS: { id: string; label: string; phases: WorkflowPhase[] }[] = [
  { id: 'configure', label: 'Configure', phases: ['idle'] },
  { id: 'analyse',   label: 'Analyse',   phases: ['analyzing', 'interview'] },
  { id: 'optimise',  label: 'Optimise',  phases: ['optimizing'] },
  { id: 'results',   label: 'Results',   phases: ['results'] },
];

const PHASE_ORDER: WorkflowPhase[] = ['idle', 'analyzing', 'interview', 'optimizing', 'results'];

function getStepState(
  stepIndex: number,
  currentPhase: WorkflowPhase
): 'pending' | 'active' | 'completed' {
  const currentIndex = PHASE_ORDER.indexOf(currentPhase);

  const step = STEPS[stepIndex];
  if (!step) return 'pending';
  
  const stepPhaseIndices = step.phases.map((p) => PHASE_ORDER.indexOf(p));
  const stepMinIndex = Math.min(...stepPhaseIndices);
  const stepMaxIndex = Math.max(...stepPhaseIndices);

  if (currentIndex < stepMinIndex) return 'pending';
  if (currentIndex > stepMaxIndex) return 'completed';

  return 'active';
}

export function StepIndicator({ phase }: StepIndicatorProps) {
  return (
    <div className="flex items-center gap-1" role="progressbar" aria-label="Workflow progress">
      {STEPS.map((step, index) => {
        const state = getStepState(index, phase);
        const isLast = index === STEPS.length - 1;

        return (
          <div key={step.id} className="flex items-center gap-1">
            {/* Step pill */}
            <m.div
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full border transition-all duration-300 ${
                state === 'active' ? 'glow-breathe' : ''
              }`}
              style={{
                backgroundColor:
                  state === 'active'
                    ? 'var(--step-active-bg)'
                    : state === 'completed'
                    ? 'var(--step-completed-bg)'
                    : 'var(--step-pending-bg)',
                borderColor:
                  state === 'active'
                    ? 'var(--step-active-border)'
                    : state === 'completed'
                    ? 'var(--step-completed-border)'
                    : 'var(--step-pending-border)',
              }}
              layout
            >
              {/* Step number / checkmark */}
              <AnimatePresence mode="wait">
                {state === 'completed' ? (
                  <m.span
                    key="check"
                    initial={{ scale: 0, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    style={{
                      fontSize: '9px',
                      color: 'var(--step-completed-text)',
                      fontWeight: 700,
                    }}
                  >
                    ✓
                  </m.span>
                ) : (
                  <m.span
                    key="num"
                    initial={{ scale: 0.8, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 0.8, opacity: 0 }}
                    transition={{ duration: 0.15 }}
                    style={{
                      fontSize: '9px',
                      fontWeight: 800,
                      color:
                        state === 'active'
                          ? 'var(--step-active-text)'
                          : 'var(--step-pending-text)',
                    }}
                  >
                    {index + 1}
                  </m.span>
                )}
              </AnimatePresence>

              {/* Label — only show for active step on narrow screens */}
              <span
                style={{
                  fontSize: '10px',
                  fontWeight: 600,
                  letterSpacing: '0.3px',
                  color:
                    state === 'active'
                      ? 'var(--step-active-text)'
                      : state === 'completed'
                      ? 'var(--step-completed-text)'
                      : 'var(--step-pending-text)',
                }}
              >
                {step.label}
              </span>
            </m.div>

            {/* Connector */}
            {!isLast && (
              <div
                className="w-4 h-px"
                style={{
                  backgroundColor:
                    getStepState(index + 1, phase) !== 'pending'
                      ? 'var(--step-completed-border)'
                      : 'var(--step-pending-border)',
                  transition: 'background-color 0.4s ease',
                }}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
