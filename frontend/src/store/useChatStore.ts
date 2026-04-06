/**
 * Chat Store
 * 
 * Manages the chat panel state: messages, input, loading state, panel visibility.
 * Uses Zustand for efficient state management with selective re-renders.
 */

import { create } from 'zustand';
import type { ChatMessage } from '@/types';

interface ChatState {
  /** Chat message history */
  messages: ChatMessage[];
  /** Current input text */
  inputText: string;
  /** Whether the chat is currently loading a response */
  isLoading: boolean;
  /** Whether the chat panel is expanded (vs collapsed) */
  isExpanded: boolean;
}

interface ChatActions {
  /** Add a message to the history */
  addMessage: (message: ChatMessage) => void;
  /** Add multiple messages at once */
  addMessages: (messages: ChatMessage[]) => void;
  /** Set the input text */
  setInputText: (text: string) => void;
  /** Set loading state */
  setIsLoading: (loading: boolean) => void;
  /** Toggle panel expanded state */
  toggleExpanded: () => void;
  /** Set panel expanded state */
  setExpanded: (expanded: boolean) => void;
  /** Clear all messages */
  clearMessages: () => void;
  /** Seed the chat with an initial assistant message (after optimization) */
  seedWithOptimizationResult: (content: string) => void;
}

type ChatStore = ChatState & ChatActions;

const initialState: ChatState = {
  messages: [],
  inputText: '',
  isLoading: false,
  isExpanded: false,
};

/**
 * Zustand store for chat state.
 * 
 * Usage:
 * ```tsx
 * const messages = useChatStore(state => state.messages);
 * const addMessage = useChatStore(state => state.addMessage);
 * ```
 */
export const useChatStore = create<ChatStore>((set) => ({
  ...initialState,

  addMessage: (message) => 
    set((state) => ({ 
      messages: [...state.messages, message] 
    })),

  addMessages: (messages) =>
    set((state) => ({
      messages: [...state.messages, ...messages],
    })),

  setInputText: (text) => set({ inputText: text }),

  setIsLoading: (loading) => set({ isLoading: loading }),

  toggleExpanded: () => set((state) => ({ isExpanded: !state.isExpanded })),

  setExpanded: (expanded) => set({ isExpanded: expanded }),

  clearMessages: () => set({ messages: [], inputText: '' }),

  seedWithOptimizationResult: (content) => {
    const timestamp = new Date().toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
    
    set({
      messages: [{
        role: 'assistant',
        content,
        timestamp,
      }],
      isExpanded: true,
    });
  },
}));

/**
 * Selector to get the count of user messages (exchanges).
 */
export function useExchangeCount(): number {
  return useChatStore((state) => 
    state.messages.filter((m) => m.role === 'user').length
  );
}

/**
 * Selector to check if chat has any messages.
 */
export function useHasMessages(): boolean {
  return useChatStore((state) => state.messages.length > 0);
}

/**
 * Get messages limited to the last N for API calls.
 */
export function getLimitedMessageHistory(messages: ChatMessage[], limit: number = 28): ChatMessage[] {
  return messages.slice(-limit);
}
