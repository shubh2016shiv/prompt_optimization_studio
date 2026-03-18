/**
 * LLM Provider and Model Type Definitions
 * 
 * These types define the structure of providers, models, frameworks,
 * task types, and TCRTE dimensions used throughout the application.
 */

/** A single LLM model configuration */
export interface Model {
  /** Unique model identifier (e.g., 'claude-sonnet-4-6') */
  id: string;
  /** Human-readable model name */
  label: string;
  /** Whether this is a reasoning model (o-series, extended thinking) */
  reasoning: boolean;
}

/** An LLM provider with its available models */
export interface Provider {
  /** Human-readable provider name */
  label: string;
  /** Icon character for the provider */
  icon: string;
  /** Accent color for the provider */
  color: string;
  /** Soft/transparent version of the accent color */
  colorSoft: string;
  /** Placeholder text for API key input */
  keyPlaceholder: string;
  /** Hint text for API key input */
  keyHint: string;
  /** Available models for this provider */
  models: Model[];
  /** Default API endpoint URL */
  defaultEndpoint: string;
}

/** Provider ID type for type safety */
export type ProviderId = 'anthropic' | 'openai' | 'google';

/** Map of provider IDs to provider configurations */
export type ProvidersMap = Record<ProviderId, Provider>;

/** An optimization framework */
export interface Framework {
  /** Unique framework identifier */
  id: string;
  /** Human-readable framework name */
  label: string;
  /** Icon character for the framework */
  icon: string;
  /** Description of what the framework does */
  description: string;
}

/** Framework ID type for type safety */
export type FrameworkId = 
  | 'auto'
  | 'kernel'
  | 'xml_structured'
  | 'progressive'
  | 'cot_ensemble'
  | 'textgrad'
  | 'reasoning_aware'
  | 'tcrte'
  | 'create';

/** A task type category */
export interface TaskType {
  /** Unique task type identifier */
  id: string;
  /** Human-readable task type name */
  label: string;
  /** Emoji icon for the task type */
  icon: string;
}

/** Task type ID type for type safety */
export type TaskTypeId = 
  | 'planning'
  | 'reasoning'
  | 'coding'
  | 'routing'
  | 'analysis'
  | 'extraction'
  | 'creative'
  | 'qa';

/** A TCRTE coverage dimension */
export interface TCRTEDimension {
  /** Dimension identifier (task, context, role, tone, execution) */
  id: TCRTEDimensionId;
  /** Human-readable dimension name */
  label: string;
  /** Single-letter icon */
  icon: string;
  /** Brief description of the dimension */
  description: string;
  /** Associated color for the dimension */
  color: string;
}

/** TCRTE dimension ID type */
export type TCRTEDimensionId = 'task' | 'context' | 'role' | 'tone' | 'execution';

/** A quick action for the chat interface */
export interface QuickAction {
  /** Icon for the quick action */
  icon: string;
  /** Action label/text */
  label: string;
}
