/**
 * WorkflowActions Component
 * 
 * Action buttons that change based on the current workflow phase.
 */

import { Button } from '@/components/ui';
import { useWorkflowStore, useIsConfigurationValid } from '@/store';
import { useGapAnalysis, useOptimization } from '@/hooks';

/**
 * Workflow action buttons - changes based on current phase.
 */
export function WorkflowActions() {
  const phase = useWorkflowStore((state) => state.phase);
  const error = useWorkflowStore((state) => state.error);
  const reset = useWorkflowStore((state) => state.reset);
  const isConfigValid = useIsConfigurationValid();

  const { analyzeGaps, isAnalyzing } = useGapAnalysis();
  const { optimize, optimizeWithoutGapData, isOptimizing } = useOptimization();

  return (
    <div className="space-y-2">
      {/* Error display */}
      {error && (
        <div 
          className="px-3 py-2 rounded-lg text-[12px] leading-relaxed"
          style={{
            backgroundColor: 'var(--danger-soft)',
            border: '1px solid var(--danger)30',
            color: 'var(--danger)',
          }}
        >
          {error.message}
        </div>
      )}

      {/* Action buttons - change based on phase */}
      <div className="flex gap-2">
        {phase === 'idle' && (
          <>
            <Button
              variant="success"
              size="lg"
              className="flex-[2]"
              onClick={analyzeGaps}
              disabled={!isConfigValid || isAnalyzing}
            >
              🔍 Analyse Gaps First
            </Button>
            <Button
              variant="secondary"
              size="lg"
              className="flex-1"
              onClick={optimizeWithoutGapData}
              disabled={!isConfigValid || isOptimizing}
            >
              Skip → Optimise
            </Button>
          </>
        )}

        {phase === 'interview' && (
          <>
            <Button
              variant="primary"
              size="lg"
              className="flex-[2]"
              onClick={optimize}
              disabled={!isConfigValid || isOptimizing}
            >
              ⬡ Optimise with Context
            </Button>
            <Button
              variant="secondary"
              size="lg"
              className="flex-1"
              onClick={optimizeWithoutGapData}
              disabled={!isConfigValid || isOptimizing}
            >
              Skip Answers
            </Button>
          </>
        )}

        {phase === 'results' && (
          <>
            <Button
              variant="secondary"
              size="lg"
              className="flex-1"
              onClick={reset}
            >
              ↺ Reset
            </Button>
            <Button
              variant="primary"
              size="lg"
              className="flex-[2]"
              onClick={optimize}
              disabled={!isConfigValid || isOptimizing}
            >
              ⬡ Re-Optimise
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
