/**
 * ChatPanel Component
 * 
 * The right panel containing the AI chat assistant.
 * Can be collapsed to a narrow icon bar.
 */

import { useRef, useEffect } from 'react';
import { m, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui';
import { Spinner } from '@/components/feedback';
import { useChatStore, useExchangeCount, useHasMessages, useWorkflowStore } from '@/store';
import { useChatSession } from '@/hooks';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { QuickActions } from './QuickActions';
import { EmptyChat } from './EmptyChat';

/**
 * Collapsible chat panel.
 */
export function ChatPanel() {
  const isExpanded = useChatStore((state) => state.isExpanded);
  const toggleExpanded = useChatStore((state) => state.toggleExpanded);
  const clearMessages = useChatStore((state) => state.clearMessages);
  const phase = useWorkflowStore((state) => state.phase);
  
  const { messages, isLoading } = useChatSession();
  const exchangeCount = useExchangeCount();
  const hasMessages = useHasMessages();

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Collapsed state - just an icon bar
  if (!isExpanded) {
    return (
      <button
        onClick={toggleExpanded}
        className="w-full h-full flex flex-col items-center justify-center gap-2 cursor-pointer transition-colors hover:bg-[var(--surface-raised)]"
        title="Open AI Chat"
      >
        <span className="text-lg">💬</span>
        <span 
          className="text-[9px] font-bold tracking-[0.8px] uppercase"
          style={{ 
            writingMode: 'vertical-rl',
            color: 'var(--text-tertiary)',
          }}
        >
          AI Chat
        </span>
        {hasMessages && (
          <span 
            className="px-1.5 py-0.5 rounded-full text-[10px] font-bold"
            style={{
              backgroundColor: 'var(--pink)',
              color: 'white',
            }}
          >
            {exchangeCount}
          </span>
        )}
      </button>
    );
  }

  // Expanded state - full chat panel
  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div 
        className="h-14 px-3 flex items-center justify-between shrink-0"
        style={{ borderBottom: '1px solid var(--border)' }}
      >
        <div className="flex items-center gap-2.5">
          <div 
            className="w-6 h-6 rounded-md flex items-center justify-center text-sm"
            style={{ background: 'linear-gradient(135deg, var(--pink), var(--purple))' }}
          >
            ✦
          </div>
          <div>
            <div className="text-[12.5px] font-bold text-[var(--text-primary)]">
              APOST Refiner
            </div>
            <div className="text-[10px] text-[var(--text-tertiary)]">
              {exchangeCount > 0 
                ? `${exchangeCount} exchange${exchangeCount !== 1 ? 's' : ''} · full memory`
                : 'Seeded on optimisation'
              }
            </div>
          </div>
        </div>

        <div className="flex gap-1.5">
          {hasMessages && (
            <Button
              variant="ghost"
              size="sm"
              onClick={clearMessages}
              className="text-[10px] font-semibold"
            >
              Clear
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={toggleExpanded}
            className="text-[12px]"
          >
            ←
          </Button>
        </div>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {!hasMessages ? (
          <EmptyChat />
        ) : (
          <>
            {messages.map((message, index) => (
              <ChatMessage key={index} message={message} />
            ))}

            {/* Loading indicator */}
            <AnimatePresence>
              {isLoading && (
                <m.div
                  className="flex items-center gap-2 p-2 self-start"
                  style={{
                    backgroundColor: 'var(--surface)',
                    border: '1px solid var(--border)',
                    borderRadius: '11px 11px 11px 3px',
                  }}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 10 }}
                >
                  <Spinner size={12} color="var(--pink)" />
                  <span className="text-[11.5px] text-[var(--text-secondary)]">
                    Thinking…
                  </span>
                </m.div>
              )}
            </AnimatePresence>

            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Quick actions (only in results phase with messages) */}
      {phase === 'results' && hasMessages && <QuickActions />}

      {/* Input */}
      <ChatInput />
    </div>
  );
}
