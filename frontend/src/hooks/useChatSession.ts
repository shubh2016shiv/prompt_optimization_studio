/**
 * Chat Session Hook
 * 
 * Manages the chat session including sending messages and building context.
 * Integrates with the chat, workflow, and configuration stores.
 */

import { useCallback } from 'react';
import { sendChatMessage, ApiError } from '@/services';
import { 
  useConfigurationStore,
  useCurrentModel,
  useWorkflowStore,
  useChatStore,
  getLimitedMessageHistory,
} from '@/store';
import type { ChatContext, ChatMessage } from '@/types';

/**
 * Hook for managing the chat session.
 * 
 * Provides functions to send messages and access chat state.
 * 
 * Usage:
 * ```tsx
 * const { sendMessage, messages, isLoading, inputText, setInputText } = useChatSession();
 * 
 * const handleSend = async () => {
 *   await sendMessage(inputText);
 * };
 * ```
 */
export function useChatSession() {
  // Configuration state
  const rawPrompt = useConfigurationStore((state) => state.rawPrompt);
  const inputVariables = useConfigurationStore((state) => state.inputVariables);
  const providerId = useConfigurationStore((state) => state.providerId);
  const apiKey = useConfigurationStore((state) => state.apiKey);
  const model = useCurrentModel();

  // Workflow state
  const taskType = useWorkflowStore((state) => state.taskType);
  const framework = useWorkflowStore((state) => state.framework);
  const gapData = useWorkflowStore((state) => state.gapData);
  const answers = useWorkflowStore((state) => state.answers);
  const result = useWorkflowStore((state) => state.result);

  // Chat state
  const messages = useChatStore((state) => state.messages);
  const inputText = useChatStore((state) => state.inputText);
  const isLoading = useChatStore((state) => state.isLoading);
  const setInputText = useChatStore((state) => state.setInputText);
  const setIsLoading = useChatStore((state) => state.setIsLoading);
  const addMessage = useChatStore((state) => state.addMessage);

  /**
   * Build the chat context from current state.
   */
  const buildContext = useCallback((): ChatContext | null => {
    if (!result) {
      return null;
    }

    return {
      raw_prompt: rawPrompt,
      variables: inputVariables || undefined,
      framework,
      task_type: taskType,
      provider: providerId,
      model,
      is_reasoning: model?.reasoning ?? false,
      gap_data: gapData,
      answers: Object.keys(answers).length > 0 ? answers : undefined,
      result,
    };
  }, [rawPrompt, inputVariables, framework, taskType, providerId, model, gapData, answers, result]);

  /**
   * Send a message to the chat assistant.
   */
  const sendMessage = useCallback(async (text: string) => {
    const trimmedText = text.trim();
    
    if (!trimmedText || isLoading) {
      return;
    }

    if (!apiKey.trim()) {
      addMessage({
        role: 'assistant',
        content: '⚠ Please enter your API key to use the chat.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      });
      return;
    }

    // Add user message
    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const userMessage: ChatMessage = {
      role: 'user',
      content: trimmedText,
      timestamp,
    };
    addMessage(userMessage);
    setInputText('');
    setIsLoading(true);

    try {
      // Build message history for API
      const allMessages = [...messages, userMessage];
      const limitedHistory = getLimitedMessageHistory(allMessages);
      
      // Strip timestamps for API
      const historyForApi = limitedHistory.map(({ role, content }) => ({ role, content }));

      const response = await sendChatMessage({
        message: trimmedText,
        history: historyForApi.slice(0, -1), // Exclude the message we just added
        context: buildContext(),
        api_key: apiKey,
      });

      const assistantMessage: ChatMessage = {
        ...response.message,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      addMessage(assistantMessage);
    } catch (error) {
      const errorMessage = error instanceof ApiError 
        ? error.message 
        : 'Failed to send message. Please try again.';
      
      addMessage({
        role: 'assistant',
        content: `⚠ ${errorMessage}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      });
    } finally {
      setIsLoading(false);
    }
  }, [messages, apiKey, isLoading, addMessage, setInputText, setIsLoading, buildContext]);

  /**
   * Send a quick action message.
   */
  const sendQuickAction = useCallback((label: string) => {
    sendMessage(label);
  }, [sendMessage]);

  return {
    messages,
    inputText,
    setInputText,
    isLoading,
    sendMessage,
    sendQuickAction,
  };
}
