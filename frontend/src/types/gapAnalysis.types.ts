/**
 * Gap Analysis Response Type Definitions
 * 
 * Types for the TCRTE coverage audit results returned by the
 * gap analysis API endpoint.
 */

import type { TCRTEDimensionId } from './provider.types';

/** Score status classification */
export type ScoreStatus = 'good' | 'weak' | 'missing';

/** Question importance level */
export type QuestionImportance = 'critical' | 'recommended' | 'optional';

/** Complexity level assessment */
export type ComplexityLevel = 'simple' | 'medium' | 'complex';

/** Score for a single TCRTE dimension */
export interface TCRTEScore {
  /** Score from 0-100 */
  score: number;
  /** Status classification based on score */
  status: ScoreStatus;
  /** Brief explanation of the score */
  note: string;
}

/** Scores for all five TCRTE dimensions */
export interface TCRTEScores {
  task: TCRTEScore;
  context: TCRTEScore;
  role: TCRTEScore;
  tone: TCRTEScore;
  execution: TCRTEScore;
}

/** A question generated to fill a TCRTE gap */
export interface GapQuestion {
  /** Unique question identifier */
  id: string;
  /** The TCRTE dimension this question addresses */
  dimension: TCRTEDimensionId;
  /** The question text */
  question: string;
  /** Example answer hint for placeholder */
  placeholder: string;
  /** Priority level of the question */
  importance: QuestionImportance;
}

/** Complete gap analysis response from the API */
export interface GapAnalysisResponse {
  /** TCRTE dimension scores */
  tcrte: TCRTEScores;
  /** Overall coverage score (0-100) */
  overall_score: number;
  /** Task complexity assessment */
  complexity: ComplexityLevel;
  /** Explanation for the complexity rating */
  complexity_reason: string;
  /** Recommended techniques based on analysis */
  recommended_techniques: string[];
  /** Questions to fill coverage gaps */
  questions: GapQuestion[];
  /** Automatic techniques that will be applied */
  auto_enrichments: string[];
}

/** Request payload for gap analysis */
export interface GapAnalysisRequest {
  raw_prompt: string;
  input_variables?: string;
  task_type: string;
  provider: string;
  model_id: string;
  model_label: string;
  is_reasoning_model: boolean;
  api_key: string;
}
