/**
 * Chat Service
 * 
 * Handles API calls for the AI chat assistant.
 */

import { postRequest } from './apiClient';
import type { ChatRequest, ChatResponse } from '@/types';

/**
 * Send a message to the chat assistant.
 * 
 * @param request - Chat request payload
 * @returns Chat response with assistant message
 */
export async function sendChatMessage(
  request: ChatRequest
): Promise<ChatResponse> {
  return postRequest<ChatResponse, ChatRequest>(
    '/chat',
    request
  );
}
