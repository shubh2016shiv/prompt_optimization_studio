/**
 * WorkflowFooter Component
 *
 * Sticky glass-morphic footer at the bottom of the middle panel.
 * Contains contextual action buttons (varies by phase) and a step hint.
 */

import { m, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui';
import { useWorkflowStore, useIsConfigurationValid } from '@/store';
import { useGapAnalysis, useOptimization } from '@/hooks';

const PHASE_HINTS: Record<string, string> = {
  idle:       'Step 1 of 4 — Configure your prompt and model',
  analyzing:  'Step 2 of 4 — Running TCRTE gap analysis…',
  interview:  'Step 2 of 4 — Answer the gap questions to improve coverage',
  optimizing: 'Step 3 of 4 — Generating three optimised variants…',
  results:    'Step 4 of 4 — Review results or refine in AI Chat →',
};

export function WorkflowFooter() {
  const phase = useWorkflowStore((state) => state.phase);
  const error = useWorkflowStore((state) => state.error);
  const reset = useWorkflowStore((state) => state.reset);
  const isConfigValid = useIsConfigurationValid();

  const { analyzeGaps, isAnalyzing } = useGapAnalysis();
  const { optimize, optimizeWithoutGapData, isOptimizing } = useOptimization();

  return (
    <div className="shrink-0 glass-footer" style={{ padding: '10px 16px' }}>
      {/* Error banner */}
      <AnimatePresence>
        {error && (
          <m.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 4 }}
            className="mb-2 px-3 py-2 rounded-lg text-[12px] leading-relaxed"
            style={{
              backgroundColor: 'var(--danger-soft)',
              border: '1px solid rgba(255,107,107,0.25)',
              color: 'var(--danger)',
            }}
          >
            {error.message}
          </m.div>
        )}
      </AnimatePresence>

      {/* Action row */}
      <div className="flex items-center gap-2">
        {/* Step hint */}
        <p
          className="flex-1 truncate"
          style={{ fontSize: '10.5px', color: 'var(--text-tertiary)', fontWeight: 500 }}
        >
          {PHASE_HINTS[phase] ?? ''}
        </p>

        {/* Contextual buttons */}
        <div className="flex gap-2 shrink-0">
          {phase === 'idle' && (
            <>
              <Button
                variant="secondary"
                size="sm"
                onClick={optimizeWithoutGapData}
                disabled={!isConfigValid || isOptimizing}
              >
                Skip → Optimise
              </Button>
              <Button
                variant="success"
                size="sm"
                className="cta-pulse"
                onClick={analyzeGaps}
                disabled={!isConfigValid || isAnalyzing}
              >
                🔍 Analyse Gaps
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
                Skip Answers
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={optimize}
                disabled={!isConfigValid || isOptimizing}
              >
                ⬡ Optimise
              </Button>
            </>
          )}

          {phase === 'results' && (
            <>
              <Button
                variant="secondary"
                size="sm"
                onClick={reset}
              >
                ↺ Reset
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={optimize}
                disabled={!isConfigValid || isOptimizing}
              >
                ⬡ Re-Optimise
              </Button>
            </>
          )}

          {(phase === 'analyzing' || phase === 'optimizing') && (
            <div
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg"
              style={{ backgroundColor: 'var(--surface-raised)', border: '1px solid var(--border)' }}
            >
              <div
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: 'var(--teal)', animation: 'ctaPulse 1.4s ease-in-out infinite' }}
              />
              <span style={{ fontSize: '11.5px', color: 'var(--text-secondary)', fontWeight: 600 }}>
                {phase === 'analyzing' ? 'Analysing…' : 'Optimising…'}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
