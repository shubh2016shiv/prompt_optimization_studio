/**
 * Gap Analysis Hook
 * 
 * Manages the gap analysis API call with loading/error states.
 * Integrates with the workflow and configuration stores.
 */

import { useCallback } from 'react';
import { analyzePromptGaps, ApiError } from '@/services';
import { 
  useConfigurationStore,
  useCurrentModel,
  useSerializedInputVariables,
  useWorkflowStore,
} from '@/store';

/**
 * Hook for triggering gap analysis.
 * 
 * Returns a function to start analysis and manages state transitions.
 * 
 * Usage:
 * ```tsx
 * const { analyzeGaps, isAnalyzing } = useGapAnalysis();
 * 
 * const handleClick = () => {
 *   analyzeGaps();
 * };
 * ```
 */
export function useGapAnalysis() {
  const rawPrompt = useConfigurationStore((state) => state.rawPrompt);
  const serializedInputVariables = useSerializedInputVariables();
  const providerId = useConfigurationStore((state) => state.providerId);
  const apiKey = useConfigurationStore((state) => state.apiKey);
  const model = useCurrentModel();
  
  const taskType = useWorkflowStore((state) => state.taskType);
  const phase = useWorkflowStore((state) => state.phase);
  const startAnalysis = useWorkflowStore((state) => state.startAnalysis);
  const handleAnalysisSuccess = useWorkflowStore((state) => state.handleAnalysisSuccess);
  const handleAnalysisError = useWorkflowStore((state) => state.handleAnalysisError);

  const isAnalyzing = phase === 'analyzing';

  const analyzeGaps = useCallback(async () => {
    if (!rawPrompt.trim()) {
      handleAnalysisError({ message: 'Please enter a prompt to analyze.' });
      return;
    }

    if (!apiKey.trim()) {
      handleAnalysisError({ message: 'Please enter your API key.' });
      return;
    }

    if (!model) {
      handleAnalysisError({ message: 'Please select a model.' });
      return;
    }

    startAnalysis();

    try {
      const response = await analyzePromptGaps({
        raw_prompt: rawPrompt,
        input_variables: serializedInputVariables,
        task_type: taskType,
        provider: providerId,
        model_id: model.id,
        model_label: model.label,
        is_reasoning_model: model.reasoning,
        api_key: apiKey,
      });

      handleAnalysisSuccess(response);
    } catch (error) {
      const message = error instanceof ApiError 
        ? error.message 
        : 'Failed to analyze prompt. Please try again.';
      
      const statusCode = error instanceof ApiError ? error.statusCode : undefined;
      
      handleAnalysisError({ message, statusCode });
    }
  }, [
    rawPrompt,
    serializedInputVariables,
    taskType,
    providerId,
    model,
    apiKey,
    startAnalysis,
    handleAnalysisSuccess,
    handleAnalysisError,
  ]);

  return {
    analyzeGaps,
    isAnalyzing,
  };
}
