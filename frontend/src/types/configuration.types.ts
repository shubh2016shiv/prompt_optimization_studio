/**
 * Configuration-specific UI types.
 */
import type { TaskTypeId } from './provider.types';

/** Supported editor modes for input variables. */
export type InputVariablesMode = 'rows' | 'raw';

/** A single structured input variable row in the UI editor. */
export interface InputVariableRow {
  id: string;
  name: string;
  description: string;
}

/** Example prompt preset used by onboarding quick-start. */
export interface PromptExample {
  id: string;
  label: string;
  prompt: string;
  taskType: TaskTypeId;
  variables: Array<{
    name: string;
    description: string;
  }>;
}
