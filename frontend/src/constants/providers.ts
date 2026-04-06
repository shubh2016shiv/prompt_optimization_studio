/**
 * Static configuration data for LLM providers, frameworks, task types, and TCRTE dimensions.
 * 
 * These constants mirror the backend definitions for consistency.
 */

import type { 
  ProvidersMap, 
  Framework, 
  TaskType, 
  TCRTEDimension,
  QuickAction,
} from '@/types';

/** LLM Providers with their available models */
export const PROVIDERS: ProvidersMap = {
  anthropic: {
    label: 'Anthropic',
    icon: '◆',
    color: 'var(--accent)',
    colorSoft: 'var(--accent-soft)',
    keyPlaceholder: 'sk-ant-api03-…',
    keyHint: 'Anthropic API key',
    models: [
      { id: 'claude-opus-4-6', label: 'Claude Opus 4.6', reasoning: false },
      { id: 'claude-sonnet-4-6', label: 'Claude Sonnet 4.6', reasoning: false },
      { id: 'claude-haiku-4-5-20251001', label: 'Claude Haiku 4.5', reasoning: false },
      { id: 'claude-sonnet-4-5', label: 'Claude Sonnet 4.5 (Ext. Thinking)', reasoning: true },
    ],
    defaultEndpoint: 'https://api.anthropic.com/v1/messages',
  },
  openai: {
    label: 'OpenAI',
    icon: '⬡',
    color: 'var(--success)',
    colorSoft: 'var(--success-soft)',
    keyPlaceholder: 'sk-proj-…',
    keyHint: 'OpenAI API key',
    models: [
      { id: 'gpt-4o', label: 'GPT-4o', reasoning: false },
      { id: 'gpt-4.1', label: 'GPT-4.1', reasoning: false },
      { id: 'o3', label: 'o3 (Reasoning)', reasoning: true },
      { id: 'o4-mini', label: 'o4-mini (Reasoning)', reasoning: true },
    ],
    defaultEndpoint: 'https://api.openai.com/v1/chat/completions',
  },
  google: {
    label: 'Google',
    icon: '✦',
    color: 'var(--warning)',
    colorSoft: 'var(--warning-soft)',
    keyPlaceholder: 'AIza…',
    keyHint: 'Google AI Studio key',
    models: [
      { id: 'gemini-2.5-pro', label: 'Gemini 2.5 Pro', reasoning: false },
      { id: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash', reasoning: false },
      { id: 'gemini-2.0-flash-thinking', label: 'Gemini 2.0 Flash Thinking', reasoning: true },
    ],
    defaultEndpoint: 'https://generativelanguage.googleapis.com/v1beta/models',
  },
};

/** Optimization frameworks */
export const FRAMEWORKS: Framework[] = [
  { id: 'auto', label: 'Auto-Select', icon: '✦', description: 'AI picks the best framework for your model & task' },
  { id: 'kernel', label: 'KERNEL', icon: '⬡', description: 'Keep · Explicit · Narrow · Known · Enforce · Logical' },
  { id: 'xml_structured', label: 'XML Structured', icon: '⟨/⟩', description: 'Anthropic XML semantic bounding — best for Claude' },
  { id: 'progressive', label: 'Progressive Disclosure', icon: '◈', description: 'Agent Skills layered context injection' },
  { id: 'cot_ensemble', label: 'CoT Ensemble', icon: '⊕', description: 'Medprompt-style multi-path reasoning' },
  { id: 'textgrad', label: 'TextGrad', icon: '∇', description: 'Iterative textual backpropagation + constraint hardening' },
  { id: 'reasoning_aware', label: 'Reasoning-Aware', icon: '◎', description: 'For o-series / extended-thinking — no forced CoT' },
  { id: 'tcrte', label: 'TCRTE', icon: '⊞', description: 'Task · Context · Role · Tone · Execution — full coverage' },
  { id: 'create', label: 'CREATE', icon: '⟳', description: 'Context · Role · Instruction · Steps · Execution' },
  { id: 'overshoot_undershoot', label: 'Overshoot/Undershoot', icon: '⇌', description: 'Dual failure-mode prevention — calibrate guard intensity for scope & depth' },
  { id: 'core_attention', label: 'CoRe Attention', icon: '⤨', description: 'Context Repetition — restructure to mitigate lost-in-the-middle context decay' },
  { id: 'ral_writer', label: 'RAL-Writer', icon: '◫', description: 'Retrieve-and-Restate — isolate and structurally enforce complex constraints' },
];

/** Task types */
export const TASK_TYPES: TaskType[] = [
  { id: 'planning', label: 'Planning', icon: '📋' },
  { id: 'reasoning', label: 'Reasoning', icon: '🧠' },
  { id: 'coding', label: 'Coding', icon: '💻' },
  { id: 'routing', label: 'Routing', icon: '🔀' },
  { id: 'analysis', label: 'Analysis', icon: '📊' },
  { id: 'extraction', label: 'Extraction', icon: '🔍' },
  { id: 'creative', label: 'Creative', icon: '✍️' },
  { id: 'qa', label: 'Q&A / RAG', icon: '💬' },
];

/** TCRTE dimensions with associated colors */
export const TCRTE_DIMENSIONS: TCRTEDimension[] = [
  { id: 'task', label: 'Task', icon: 'T', description: 'Core objective & action', color: 'var(--accent)' },
  { id: 'context', label: 'Context', icon: 'C', description: 'Background & grounding data', color: 'var(--cyan)' },
  { id: 'role', label: 'Role', icon: 'R', description: 'Model persona & expertise', color: 'var(--purple)' },
  { id: 'tone', label: 'Tone', icon: 'T', description: 'Style & communication register', color: 'var(--pink)' },
  { id: 'execution', label: 'Execution', icon: 'E', description: 'Format, length & constraints', color: 'var(--orange)' },
];

/** Quick actions for the chat interface */
export const QUICK_ACTIONS: QuickAction[] = [
  { icon: '✂', label: 'Make V1 more concise' },
  { icon: '🛡', label: 'Add anti-hallucination guards to V2' },
  { icon: '◎', label: 'Convert V3 to reasoning-aware' },
  { icon: '⊕', label: 'Merge best parts of all 3 variants' },
  { icon: '📎', label: 'Add few-shot examples to V2' },
  { icon: '🔒', label: 'Harden output format constraints' },
  { icon: '⚠', label: 'What are the biggest risks here?' },
  { icon: '⟨/⟩', label: 'Rewrite V1 with XML structural bounding' },
  { icon: '⊞', label: 'Apply full TCRTE coverage to V3' },
  { icon: '⟳', label: 'Apply Context Repetition for multi-hop' },
];

/** Default provider ID */
export const DEFAULT_PROVIDER_ID = 'anthropic' as const;

/** Default model ID */
export const DEFAULT_MODEL_ID = 'claude-sonnet-4-6';

/** Default task type ID */
export const DEFAULT_TASK_TYPE_ID = 'reasoning';

/** Default framework ID */
export const DEFAULT_FRAMEWORK_ID = 'auto';
