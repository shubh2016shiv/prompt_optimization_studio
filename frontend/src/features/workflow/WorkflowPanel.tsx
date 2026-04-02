/**
 * WorkflowPanel Component
 *
 * The middle panel — pure phase content with a sticky glass footer.
 * Task type and framework selectors are now in the ConfigurationPanel accordion.
 * Action buttons are now in the WorkflowFooter at the bottom.
 */

import { AnimatePresence } from 'framer-motion';
import { useWorkflowStore } from '@/store';
import { IdleState, AnalyzingState, InterviewPhase, OptimizingState, ResultsPhase } from './phases';
import { WorkflowFooter } from './WorkflowFooter';

export function WorkflowPanel() {
  const phase = useWorkflowStore((state) => state.phase);

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Phase-specific content — fills all available space */}
      <div className="flex-1 overflow-hidden">
        <AnimatePresence mode="wait">
          {phase === 'idle'       && <IdleState       key="idle"       />}
          {phase === 'analyzing'  && <AnalyzingState  key="analyzing"  />}
          {phase === 'interview'  && <InterviewPhase  key="interview"  />}
          {phase === 'optimizing' && <OptimizingState key="optimizing" />}
          {phase === 'results'    && <ResultsPhase    key="results"    />}
        </AnimatePresence>
      </div>

      {/* Sticky glass footer with contextual actions */}
      <WorkflowFooter />
    </div>
  );
}
