/**
 * Chat Type Definitions
 * 
 * Types for the AI chat assistant interface.
 */

import type { GapAnalysisResponse } from './gapAnalysis.types';
import type { OptimizationResponse } from './optimization.types';
import type { Model } from './provider.types';

/** Chat message role */
export type ChatRole = 'user' | 'assistant';

/** A single chat message */
export interface ChatMessage {
  /** Message sender role */
  role: ChatRole;
  /** Message content (may contain markdown/code) */
  content: string;
  /** Timestamp when message was created */
  timestamp?: string;
}

/** Session context passed to the chat API */
export interface ChatContext {
  /** The raw prompt being optimized */
  raw_prompt: string;
  /** Declared input variables */
  variables?: string;
  /** Selected optimization framework */
  framework: string;
  /** Selected task type */
  task_type: string;
  /** LLM provider ID */
  provider: string;
  /** Target model information */
  model: Model | null;
  /** Whether the model is a reasoning model */
  is_reasoning: boolean;
  /** Gap analysis results (if available) */
  gap_data?: GapAnalysisResponse | null;
  /** User answers to gap questions */
  answers?: Record<string, string>;
  /** Optimization results (if available) */
  result?: OptimizationResponse | null;
}

/** Request payload for chat */
export interface ChatRequest {
  message: string;
  history: ChatMessage[];
  context?: ChatContext | null;
  provider: string;
  model_id: string;
  api_key: string;
}

/** Response from the chat API */
export interface ChatResponse {
  message: ChatMessage;
}
