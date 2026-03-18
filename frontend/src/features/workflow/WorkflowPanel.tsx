/**
 * WorkflowPanel Component
 * 
 * The middle panel containing workflow controls and phase-specific content.
 * Uses AnimatePresence for smooth phase transitions.
 */

import { AnimatePresence } from 'framer-motion';
import { useWorkflowStore } from '@/store';
import { TaskTypeSelector, FrameworkSelector, WorkflowActions } from './controls';
import { IdleState, AnalyzingState, InterviewPhase, OptimizingState, ResultsPhase } from './phases';

/**
 * Main workflow panel with controls and phase content.
 */
export function WorkflowPanel() {
  const phase = useWorkflowStore((state) => state.phase);

  return (
    <>
      {/* Fixed controls strip */}
      <div 
        className="shrink-0 p-4 space-y-4"
        style={{
          backgroundColor: 'var(--surface)',
          borderBottom: '1px solid var(--border)',
        }}
      >
        <TaskTypeSelector />
        <FrameworkSelector />
        <WorkflowActions />
      </div>

      {/* Phase-specific content with animated transitions */}
      <div className="flex-1 overflow-hidden">
        <AnimatePresence mode="wait">
          {phase === 'idle' && <IdleState key="idle" />}
          {phase === 'analyzing' && <AnalyzingState key="analyzing" />}
          {phase === 'interview' && <InterviewPhase key="interview" />}
          {phase === 'optimizing' && <OptimizingState key="optimizing" />}
          {phase === 'results' && <ResultsPhase key="results" />}
        </AnimatePresence>
      </div>
    </>
  );
}
