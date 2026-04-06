/**
 * WorkflowFooter Component
 *
 * Sticky footer with contextual actions and progress feedback.
 */

import { m, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui';
import { useWorkflowStore, useIsConfigurationValid } from '@/store';
import { useGapAnalysis, useOptimization } from '@/hooks';

const PHASE_HINTS: Record<string, string> = {
  idle: 'Step 1 of 4 - Configure prompt and model',
  analyzing: 'Step 2 of 4 - Running full TCRTE audit',
  interview: 'Step 2 of 4 - Answer gap questions to improve coverage',
  optimizing: 'Step 3 of 4 - Generating three prompt variants',
  results: 'Step 4 of 4 - Review output or refine in AI Chat',
};

function BusyIndicator({ label }: { label: string }) {
  return (
    <div
      className="w-[240px] rounded-lg px-3 py-1.5"
      style={{ backgroundColor: 'var(--surface-3)', border: '1px solid var(--border-subtle)' }}
    >
      <div className="flex items-center justify-between mb-1">
        <span style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: 600 }}>{label}</span>
        <span style={{ fontSize: '10px', color: 'var(--teal)' }}>in progress</span>
      </div>
      <div className="h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: 'rgba(255,255,255,0.08)' }}>
        <m.div
          className="h-full rounded-full"
          style={{ backgroundColor: 'var(--teal)' }}
          initial={{ width: '18%' }}
          animate={{ width: ['26%', '78%', '52%'] }}
          transition={{ duration: 1.2, repeat: Infinity, ease: 'easeInOut' }}
        />
      </div>
    </div>
  );
}

export function WorkflowFooter() {
  const phase = useWorkflowStore((state) => state.phase);
  const error = useWorkflowStore((state) => state.error);
  const reset = useWorkflowStore((state) => state.reset);
  const isConfigValid = useIsConfigurationValid();

  const { analyzeGaps } = useGapAnalysis();
  const { optimize, optimizeWithoutGapData, isOptimizing } = useOptimization();

  return (
    <div
      className="shrink-0"
      style={{
        padding: '10px 16px',
        backgroundColor: 'rgba(17, 17, 17, 0.92)',
        borderTop: '1px solid var(--border-subtle)',
        backdropFilter: 'blur(10px)',
      }}
    >
      <AnimatePresence>
        {error && (
          <m.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 4 }}
            className="mb-2 px-3 py-2 rounded-lg text-[12px] leading-relaxed"
            style={{
              backgroundColor: 'var(--danger-soft)',
              border: '1px solid rgba(255, 107, 107, 0.3)',
              color: 'var(--danger)',
            }}
          >
            {error.message}
          </m.div>
        )}
      </AnimatePresence>

      <div className="flex items-center gap-2">
        <p className="flex-1 truncate" style={{ fontSize: '10.5px', color: 'var(--text-tertiary)', fontWeight: 500 }}>
          {PHASE_HINTS[phase] ?? ''}
        </p>

        <div className="flex gap-2 shrink-0 items-center">
          {phase === 'idle' && (
            <>
              <span style={{ fontSize: '10px', color: 'var(--text-tertiary)', marginRight: 2 }}>
                Full audit recommended
              </span>
              <Button
                variant="secondary"
                size="sm"
                onClick={optimizeWithoutGapData}
                disabled={!isConfigValid || isOptimizing}
              >
                Quick optimise
              </Button>
              <Button
                variant="success"
                size="sm"
                className="cta-pulse"
                onClick={analyzeGaps}
                disabled={!isConfigValid}
              >
                Analyse Gaps
              </Button>
            </>
          )}

          {phase === 'interview' && (
            <>
              <Button
                variant="secondary"
                size="sm"
                onClick={optimizeWithoutGapData}
                disabled={!isConfigValid || isOptimizing}
              >
                Quick optimise
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={optimize}
                disabled={!isConfigValid || isOptimizing}
              >
                Optimise
              </Button>
            </>
          )}

          {phase === 'results' && (
            <>
              <Button variant="secondary" size="sm" onClick={reset}>
                Reset
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={optimize}
                disabled={!isConfigValid || isOptimizing}
              >
                Re-Optimise
              </Button>
            </>
          )}

          {phase === 'analyzing' && <BusyIndicator label="Analysing" />}
          {phase === 'optimizing' && <BusyIndicator label="Optimising" />}
        </div>
      </div>

      {phase === 'idle' && (
        <div style={{ fontSize: '10px', color: 'var(--text-tertiary)', marginTop: 6 }}>
          Analyse Gaps runs a full TCRTE audit first (recommended).
        </div>
      )}
    </div>
  );
}
