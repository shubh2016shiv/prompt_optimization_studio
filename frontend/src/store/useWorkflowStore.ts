/**
 * Workflow Store
 * 
 * Manages the workflow state machine: phase, task type, framework, gap data, answers, results.
 * Uses Zustand for efficient state management with selective re-renders.
 */

import { create } from 'zustand';
import type { 
  WorkflowPhase, 
  WorkflowError,
  GapAnalysisResponse,
  OptimizationResponse,
  FrameworkId,
  TaskTypeId,
} from '@/types';
import { DEFAULT_FRAMEWORK_ID, DEFAULT_TASK_TYPE_ID } from '@/constants';

interface WorkflowState {
  /** Current phase of the workflow state machine */
  phase: WorkflowPhase;
  /** Selected task type */
  taskType: TaskTypeId;
  /** Selected optimization framework */
  framework: FrameworkId;
  /** Gap analysis results (null if not yet analyzed) */
  gapData: GapAnalysisResponse | null;
  /** User answers to gap interview questions (question text -> answer) */
  answers: Record<string, string>;
  /** Optimization results (null if not yet optimized) */
  result: OptimizationResponse | null;
  /** Current error (null if no error) */
  error: WorkflowError | null;
}

interface WorkflowActions {
  /** Set the current workflow phase */
  setPhase: (phase: WorkflowPhase) => void;
  /** Set the task type */
  setTaskType: (taskType: TaskTypeId) => void;
  /** Set the optimization framework */
  setFramework: (framework: FrameworkId) => void;
  /** Set gap analysis results */
  setGapData: (data: GapAnalysisResponse) => void;
  /** Update a single answer */
  setAnswer: (question: string, answer: string) => void;
  /** Set all answers at once */
  setAnswers: (answers: Record<string, string>) => void;
  /** Set optimization results */
  setResult: (result: OptimizationResponse) => void;
  /** Set an error */
  setError: (error: WorkflowError | null) => void;
  /** Clear the error */
  clearError: () => void;
  /** Reset to idle state (clears gap data, answers, results) */
  reset: () => void;
  /** Transition to analyzing phase */
  startAnalysis: () => void;
  /** Handle successful gap analysis */
  handleAnalysisSuccess: (data: GapAnalysisResponse) => void;
  /** Handle failed gap analysis */
  handleAnalysisError: (error: WorkflowError) => void;
  /** Transition to optimizing phase */
  startOptimization: () => void;
  /** Handle successful optimization */
  handleOptimizationSuccess: (result: OptimizationResponse) => void;
  /** Handle failed optimization */
  handleOptimizationError: (error: WorkflowError) => void;
}

type WorkflowStore = WorkflowState & WorkflowActions;

const initialState: WorkflowState = {
  phase: 'idle',
  taskType: DEFAULT_TASK_TYPE_ID as TaskTypeId,
  framework: DEFAULT_FRAMEWORK_ID as FrameworkId,
  gapData: null,
  answers: {},
  result: null,
  error: null,
};

/**
 * Zustand store for workflow state.
 * 
 * Usage:
 * ```tsx
 * const phase = useWorkflowStore(state => state.phase);
 * const startAnalysis = useWorkflowStore(state => state.startAnalysis);
 * ```
 */
export const useWorkflowStore = create<WorkflowStore>((set) => ({
  ...initialState,

  setPhase: (phase) => set({ phase, error: null }),
  
  setTaskType: (taskType) => set({ taskType }),
  
  setFramework: (framework) => set({ framework }),
  
  setGapData: (data) => set({ gapData: data }),
  
  setAnswer: (question, answer) => 
    set((state) => ({ 
      answers: { ...state.answers, [question]: answer } 
    })),
  
  setAnswers: (answers) => set({ answers }),
  
  setResult: (result) => set({ result }),
  
  setError: (error) => set({ error }),
  
  clearError: () => set({ error: null }),
  
  reset: () => set({
    phase: 'idle',
    gapData: null,
    answers: {},
    result: null,
    error: null,
  }),

  startAnalysis: () => set({ 
    phase: 'analyzing', 
    error: null,
    gapData: null,
    answers: {},
    result: null,
  }),

  handleAnalysisSuccess: (data) => set({
    phase: 'interview',
    gapData: data,
    error: null,
  }),

  handleAnalysisError: (error) => set({
    phase: 'idle',
    error,
  }),

  startOptimization: () => set({
    phase: 'optimizing',
    error: null,
    result: null,
  }),

  handleOptimizationSuccess: (result) => set({
    phase: 'results',
    result,
    error: null,
  }),

  handleOptimizationError: (error) => set((state) => ({
    phase: state.gapData ? 'interview' : 'idle',
    error,
  })),
}));

/**
 * Selector to check if we have gap data available.
 */
export function useHasGapData(): boolean {
  return useWorkflowStore((state) => state.gapData !== null);
}

/**
 * Selector to check if we have optimization results.
 */
export function useHasResults(): boolean {
  return useWorkflowStore((state) => state.result !== null);
}

/**
 * Selector to get the overall TCRTE score from gap data.
 */
export function useOverallScore(): number {
  return useWorkflowStore((state) => state.gapData?.overall_score ?? 0);
}
