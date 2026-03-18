/**
 * Optimization Response Type Definitions
 * 
 * Types for the three optimized prompt variants returned by the
 * optimization API endpoint.
 */

import type { GapAnalysisResponse } from './gapAnalysis.types';

/** TCRTE scores for a variant (simplified numeric format) */
export interface VariantTCRTEScores {
  task: number;
  context: number;
  role: number;
  tone: number;
  execution: number;
}

/** A single optimized prompt variant */
export interface PromptVariant {
  /** Variant number (1, 2, or 3) */
  id: number;
  /** Variant name (Conservative, Structured, Advanced) */
  name: string;
  /** Brief description of the variant's approach */
  strategy: string;
  /** The optimized system prompt */
  system_prompt: string;
  /** The optimized user prompt template */
  user_prompt: string;
  /** Claude prefill suggestion for format locking (Advanced variant only) */
  prefill_suggestion?: string;
  /** Estimated token count */
  token_estimate: number;
  /** TCRTE coverage scores for this variant */
  tcrte_scores: VariantTCRTEScores;
  /** Key strengths of this variant */
  strengths: string[];
  /** Use cases this variant is best suited for */
  best_for: string;
  /** Anti-overshoot protections */
  overshoot_guards: string[];
  /** Anti-undershoot protections */
  undershoot_guards: string[];
}

/** Analysis summary from the optimization process */
export interface OptimizationAnalysis {
  /** Issues found in the original prompt */
  detected_issues: string[];
  /** Notes about model-specific optimizations */
  model_notes: string;
  /** The framework that was applied */
  framework_applied: string;
  /** Coverage improvement summary */
  coverage_delta: string;
}

/** Complete optimization response from the API */
export interface OptimizationResponse {
  /** Optimization analysis summary */
  analysis: OptimizationAnalysis;
  /** List of techniques applied */
  techniques_applied: string[];
  /** The three optimized variants */
  variants: PromptVariant[];
}

/** Request payload for optimization */
export interface OptimizationRequest {
  raw_prompt: string;
  input_variables?: string;
  task_type: string;
  framework: string;
  provider: string;
  model_id: string;
  model_label: string;
  is_reasoning_model: boolean;
  gap_data?: GapAnalysisResponse | null;
  answers?: Record<string, string> | null;
  api_key: string;
}
