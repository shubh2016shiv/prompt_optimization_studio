/**
 * StepIndicator Component
 *
 * Four-step gated workflow indicator.
 */

import { m, AnimatePresence } from 'framer-motion';
import type { WorkflowPhase } from '@/types';

interface StepIndicatorProps {
  phase: WorkflowPhase;
}

const STEPS: { id: string; label: string; phases: WorkflowPhase[] }[] = [
  { id: 'configure', label: 'Configure', phases: ['idle'] },
  { id: 'analyse', label: 'Analyse', phases: ['analyzing', 'interview'] },
  { id: 'optimise', label: 'Optimise', phases: ['optimizing'] },
  { id: 'results', label: 'Results', phases: ['results'] },
];

const PHASE_ORDER: WorkflowPhase[] = ['idle', 'analyzing', 'interview', 'optimizing', 'results'];

type StepState = 'future' | 'active' | 'completed';

function getStepState(stepIndex: number, currentPhase: WorkflowPhase): StepState {
  const currentIndex = PHASE_ORDER.indexOf(currentPhase);
  const step = STEPS[stepIndex];

  if (!step) {
    return 'future';
  }

  const stepPhaseIndices = step.phases.map((value) => PHASE_ORDER.indexOf(value));
  const stepMinIndex = Math.min(...stepPhaseIndices);
  const stepMaxIndex = Math.max(...stepPhaseIndices);

  if (currentIndex < stepMinIndex) {
    return 'future';
  }

  if (currentIndex > stepMaxIndex) {
    return 'completed';
  }

  return 'active';
}

function connectorFill(stepIndex: number, phase: WorkflowPhase): string {
  const thisState = getStepState(stepIndex, phase);
  const nextState = getStepState(stepIndex + 1, phase);

  if (thisState === 'completed' && (nextState === 'completed' || nextState === 'active')) {
    return '100%';
  }

  if (thisState === 'active') {
    return '40%';
  }

  return '0%';
}

export function StepIndicator({ phase }: StepIndicatorProps) {
  return (
    <div className="flex items-center gap-1.5" role="progressbar" aria-label="Workflow progress">
      {STEPS.map((step, index) => {
        const state = getStepState(index, phase);
        const isLast = index === STEPS.length - 1;

        return (
          <div key={step.id} className="flex items-center gap-1.5">
            <m.div
              className="px-2.5 py-1 rounded-full border inline-flex items-center gap-1.5"
              style={{
                opacity: state === 'future' ? 0.45 : 1,
                backgroundColor:
                  state === 'active'
                    ? 'rgba(45, 212, 191, 0.16)'
                    : state === 'completed'
                    ? 'rgba(61, 214, 140, 0.12)'
                    : 'rgba(255, 255, 255, 0.04)',
                borderColor:
                  state === 'active'
                    ? 'rgba(45, 212, 191, 0.5)'
                    : state === 'completed'
                    ? 'rgba(61, 214, 140, 0.35)'
                    : 'var(--border-subtle)',
              }}
              layout
              aria-disabled={state === 'future'}
            >
              <AnimatePresence mode="wait" initial={false}>
                {state === 'completed' ? (
                  <m.span
                    key="complete"
                    initial={{ scale: 0.8, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 0.8, opacity: 0 }}
                    style={{ fontSize: '10px', color: 'var(--success)', fontWeight: 700 }}
                  >
                    ?
                  </m.span>
                ) : (
                  <m.span
                    key="index"
                    initial={{ scale: 0.8, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 0.8, opacity: 0 }}
                    style={{
                      fontSize: '10px',
                      fontWeight: 700,
                      color: state === 'active' ? 'var(--teal)' : 'var(--text-tertiary)',
                    }}
                  >
                    {index + 1}
                  </m.span>
                )}
              </AnimatePresence>

              <span
                style={{
                  fontSize: '10.5px',
                  fontWeight: state === 'active' ? 700 : 600,
                  color:
                    state === 'active'
                      ? 'var(--text-primary)'
                      : state === 'completed'
                      ? 'var(--success)'
                      : 'var(--text-tertiary)',
                }}
              >
                {step.label}
              </span>
            </m.div>

            {!isLast && (
              <div
                className="relative h-[2px] w-5 rounded-full overflow-hidden"
                style={{ backgroundColor: 'var(--border-subtle)' }}
              >
                <m.div
                  className="absolute left-0 top-0 h-full rounded-full"
                  style={{ backgroundColor: 'var(--teal)' }}
                  animate={{ width: connectorFill(index, phase) }}
                  transition={{ duration: 0.3, ease: 'easeOut' }}
                />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
