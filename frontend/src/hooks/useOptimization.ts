/**
 * Optimization Hook
 * 
 * Manages the optimization API call with loading/error states.
 * Integrates with the workflow, configuration, and chat stores.
 */

import { useCallback } from 'react';
import { optimizePrompt, ApiError } from '@/services';
import { 
  useConfigurationStore,
  useCurrentModel,
  useWorkflowStore,
  useChatStore,
} from '@/store';
import type { OptimizationResponse } from '@/types';

/**
 * Build the seed message content for the chat after optimization.
 */
function buildSeedMessage(result: OptimizationResponse): string {
  const { analysis, techniques_applied, variants } = result;
  
  const techniquesStr = techniques_applied.length > 0 
    ? techniques_applied.join(', ') 
    : 'standard optimization';
  
  const issuesStr = analysis.detected_issues.slice(0, 3).join('; ') || 'None detected';

  const variantBlocks = variants.map((v) => {
    const tcrte = v.tcrte_scores;
    const tcrteStr = `T${tcrte.task} C${tcrte.context} R${tcrte.role} Tone${tcrte.tone} E${tcrte.execution}`;
    
    let block = `**Variant ${v.id} — ${v.name}** (~${v.token_estimate}t)\n`;
    block += `${v.strategy}\n\n`;
    block += `TCRTE: ${tcrteStr}\n\n`;
    block += '```SYSTEM\n' + v.system_prompt + '\n```\n';
    block += '```USER\n' + v.user_prompt + '\n```';
    
    if (v.prefill_suggestion) {
      block += '\n```PREFILL\n' + v.prefill_suggestion + '\n```';
    }
    
    return block;
  }).join('\n\n');

  return `✦ Optimization complete.

**${analysis.framework_applied}**
${analysis.coverage_delta ? `**${analysis.coverage_delta}**\n` : ''}
**Techniques applied:** ${techniquesStr}

**Issues fixed:** ${issuesStr}

---

${variantBlocks}

---
I have full context of all 3 variants + your gap answers. What would you like to refine?`;
}

/**
 * Hook for triggering prompt optimization.
 * 
 * Returns functions to start optimization (with or without gap data) and manages state transitions.
 * 
 * Usage:
 * ```tsx
 * const { optimize, optimizeWithoutGapData, isOptimizing } = useOptimization();
 * 
 * const handleOptimize = () => {
 *   optimize(); // Uses gap data and answers if available
 * };
 * ```
 */
export function useOptimization() {
  const rawPrompt = useConfigurationStore((state) => state.rawPrompt);
  const inputVariables = useConfigurationStore((state) => state.inputVariables);
  const providerId = useConfigurationStore((state) => state.providerId);
  const apiKey = useConfigurationStore((state) => state.apiKey);
  const model = useCurrentModel();
  
  const taskType = useWorkflowStore((state) => state.taskType);
  const framework = useWorkflowStore((state) => state.framework);
  const gapData = useWorkflowStore((state) => state.gapData);
  const answers = useWorkflowStore((state) => state.answers);
  const phase = useWorkflowStore((state) => state.phase);
  const startOptimization = useWorkflowStore((state) => state.startOptimization);
  const handleOptimizationSuccess = useWorkflowStore((state) => state.handleOptimizationSuccess);
  const handleOptimizationError = useWorkflowStore((state) => state.handleOptimizationError);
  
  const seedWithOptimizationResult = useChatStore((state) => state.seedWithOptimizationResult);
  const clearMessages = useChatStore((state) => state.clearMessages);

  const isOptimizing = phase === 'optimizing';

  const doOptimize = useCallback(async (useGapData: boolean) => {
    if (!rawPrompt.trim()) {
      handleOptimizationError({ message: 'Please enter a prompt to optimize.' });
      return;
    }

    if (!apiKey.trim()) {
      handleOptimizationError({ message: 'Please enter your API key.' });
      return;
    }

    if (!model) {
      handleOptimizationError({ message: 'Please select a model.' });
      return;
    }

    // Clear existing chat messages
    clearMessages();
    startOptimization();

    try {
      const response = await optimizePrompt({
        raw_prompt: rawPrompt,
        input_variables: inputVariables || undefined,
        task_type: taskType,
        framework,
        provider: providerId,
        model_id: model.id,
        model_label: model.label,
        is_reasoning_model: model.reasoning,
        gap_data: useGapData ? gapData : null,
        answers: useGapData && Object.keys(answers).length > 0 ? answers : null,
        api_key: apiKey,
      });

      handleOptimizationSuccess(response);
      
      // Seed chat with the full optimization result
      const seedContent = buildSeedMessage(response);
      seedWithOptimizationResult(seedContent);
    } catch (error) {
      const message = error instanceof ApiError 
        ? error.message 
        : 'Failed to optimize prompt. Please try again.';
      
      const statusCode = error instanceof ApiError ? error.statusCode : undefined;
      
      handleOptimizationError({ message, statusCode });
    }
  }, [
    rawPrompt,
    inputVariables,
    taskType,
    framework,
    providerId,
    model,
    apiKey,
    gapData,
    answers,
    clearMessages,
    startOptimization,
    handleOptimizationSuccess,
    handleOptimizationError,
    seedWithOptimizationResult,
  ]);

  const optimize = useCallback(() => doOptimize(true), [doOptimize]);
  const optimizeWithoutGapData = useCallback(() => doOptimize(false), [doOptimize]);

  return {
    optimize,
    optimizeWithoutGapData,
    isOptimizing,
  };
}
