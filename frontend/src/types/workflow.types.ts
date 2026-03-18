/**
 * Workflow Type Definitions
 * 
 * Types for the application workflow state machine.
 */

/** Workflow phase states */
export type WorkflowPhase = 
  | 'idle'
  | 'analyzing'
  | 'interview'
  | 'optimizing'
  | 'results';

/** Error state for workflow operations */
export interface WorkflowError {
  /** Error message to display */
  message: string;
  /** HTTP status code (if applicable) */
  statusCode?: number;
}

/**
 * Valid phase transitions for the workflow state machine.
 * 
 * State transitions:
 * - idle → analyzing (user clicks "Analyse Gaps")
 * - idle → optimizing (user clicks "Skip → Optimise")
 * - analyzing → interview (gap analysis succeeds)
 * - analyzing → idle (gap analysis fails)
 * - interview → optimizing (user clicks "Optimise with Context" or "Skip Answers")
 * - optimizing → results (optimization succeeds)
 * - optimizing → interview (optimization fails, user can try again)
 * - results → idle (user clicks "Reset")
 * - results → optimizing (user clicks "Re-Optimise")
 */
export const VALID_PHASE_TRANSITIONS: Record<WorkflowPhase, WorkflowPhase[]> = {
  idle: ['analyzing', 'optimizing'],
  analyzing: ['interview', 'idle'],
  interview: ['optimizing'],
  optimizing: ['results', 'interview'],
  results: ['idle', 'optimizing'],
} as const;

/**
 * Check if a phase transition is valid.
 */
export function isValidTransition(from: WorkflowPhase, to: WorkflowPhase): boolean {
  return VALID_PHASE_TRANSITIONS[from].includes(to);
}
