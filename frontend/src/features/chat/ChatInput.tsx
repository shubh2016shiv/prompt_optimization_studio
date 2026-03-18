/**
 * ChatInput Component
 * 
 * The chat input area with send button.
 */

import { useRef, useCallback } from 'react';
import { Button } from '@/components/ui';
import { Spinner } from '@/components/feedback';
import { useChatSession } from '@/hooks';
import { useWorkflowStore, useHasMessages } from '@/store';

/**
 * Chat input with send button.
 */
export function ChatInput() {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { inputText, setInputText, isLoading, sendMessage } = useChatSession();
  const phase = useWorkflowStore((state) => state.phase);
  const hasMessages = useHasMessages();

  const placeholder = phase === 'results'
    ? 'Refine a variant, add guards, change tone…'
    : 'Ask about prompt engineering…';

  const handleKeyDown = useCallback((event: React.KeyboardEvent) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendMessage(inputText);
    }
  }, [inputText, sendMessage]);

  const handleSend = useCallback(() => {
    sendMessage(inputText);
  }, [inputText, sendMessage]);

  const isDisabled = isLoading || !inputText.trim();

  return (
    <div 
      className="p-3 border-t space-y-2"
      style={{ borderColor: 'var(--border)' }}
    >
      <div className="flex gap-2 items-end">
        <textarea
          ref={textareaRef}
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          rows={2}
          className="flex-1 p-2 rounded-lg text-[12.5px] leading-relaxed resize-none outline-none max-h-[100px] overflow-y-auto"
          style={{
            backgroundColor: 'var(--surface)',
            border: '1px solid var(--border)',
            color: 'var(--text-primary)',
            fontFamily: 'var(--font-sans)',
          }}
        />
        <Button
          onClick={handleSend}
          disabled={isDisabled}
          size="icon"
          className="w-9 h-9 shrink-0"
          style={{
            background: isDisabled 
              ? 'var(--border-elevated)' 
              : 'linear-gradient(135deg, var(--pink), var(--purple))',
            cursor: isDisabled ? 'not-allowed' : 'pointer',
          }}
        >
          {isLoading ? <Spinner size={13} /> : '↑'}
        </Button>
      </div>

      <div className="text-[9.5px] text-[var(--text-tertiary)] text-center">
        Enter ↵ to send · Shift+Enter new line
        {hasMessages && ` · ${useHasMessages.length} msgs in memory`}
      </div>
    </div>
  );
}
