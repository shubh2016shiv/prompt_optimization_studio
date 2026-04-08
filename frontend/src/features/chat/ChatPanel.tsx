/**
 * ChatPanel Component
 *
 * Collapsible AI chat panel with visible collapsed rail.
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

export function ChatPanel() {
  const isExpanded = useChatStore((state) => state.isExpanded);
  const toggleExpanded = useChatStore((state) => state.toggleExpanded);
  const clearMessages = useChatStore((state) => state.clearMessages);
  const phase = useWorkflowStore((state) => state.phase);

  const { messages, isLoading } = useChatSession();
  const exchangeCount = useExchangeCount();
  const hasMessages = useHasMessages();

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  if (!isExpanded) {
    return (
      <button
        onClick={toggleExpanded}
        className="w-full h-full flex flex-col items-center justify-between py-4 cursor-pointer transition-colors hover:bg-[var(--surface-3)] focus:outline-none"
        style={{ borderLeft: '1px solid var(--border-subtle)' }}
        title="Open AI chat"
        aria-label="Open AI chat"
      >
        <div className="flex flex-col items-center gap-2">
          <div
            style={{
              width: 18,
              height: 18,
              borderRadius: 5,
              background: 'linear-gradient(135deg, var(--pink), var(--purple))',
              boxShadow: phase === 'results' ? '0 0 12px rgba(240,98,146,0.4)' : 'none',
            }}
          />
          <span
            style={{
              fontSize: '9px',
              color: 'var(--text-tertiary)',
              letterSpacing: '0.05em',
              writingMode: 'vertical-rl',
              textOrientation: 'mixed',
              fontWeight: 700,
            }}
          >
            AI Chat
          </span>
        </div>

        <div className="flex flex-col items-center gap-2">
          <span
            className="px-1 py-0.5 rounded"
            style={{
              fontSize: '8px',
              color: 'var(--pink)',
              backgroundColor: 'rgba(240, 98, 146, 0.16)',
              border: '1px solid rgba(240, 98, 146, 0.32)',
              transform: 'rotate(-90deg)',
              whiteSpace: 'nowrap',
            }}
          >
            Phase 4
          </span>

          {hasMessages ? (
            <span
              className="px-1.5 py-0.5 rounded-full"
              style={{
                fontSize: '9px',
                backgroundColor: 'var(--pink)',
                color: '#fff',
                minWidth: 18,
                textAlign: 'center',
                fontWeight: 700,
              }}
            >
              {exchangeCount}
            </span>
          ) : (
            phase === 'results' && (
              <span
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: '50%',
                  backgroundColor: 'var(--pink)',
                  animation: 'ctaPulse 1.6s ease-in-out infinite',
                }}
              />
            )
          )}
        </div>
      </button>
    );
  }

  return (
    <m.div
      className="flex-1 flex flex-col h-full min-h-0 overflow-hidden"
      initial={{ x: 24, opacity: 0.92 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.28, ease: 'easeOut' }}
      style={{ backgroundColor: 'var(--surface-2)' }}
    >
      <div
        className="px-3 flex items-center justify-between shrink-0"
        style={{ height: 52, borderBottom: '1px solid var(--border-subtle)' }}
      >
        <div className="flex items-center gap-2.5">
          <div
            style={{
              width: 20,
              height: 20,
              borderRadius: 6,
              background: 'linear-gradient(135deg, var(--pink), var(--purple))',
              boxShadow: '0 0 10px rgba(240,98,146,0.24)',
            }}
          />
          <div>
            <div style={{ fontSize: '12.5px', fontWeight: 700, color: 'var(--text-primary)' }}>
              AI Chat Refiner
            </div>
            <div style={{ fontSize: '10px', color: 'var(--text-tertiary)' }}>
              {phase === 'results' && exchangeCount === 0
                ? 'Results loaded with context'
                : exchangeCount > 0
                ? `${exchangeCount} exchange${exchangeCount !== 1 ? 's' : ''}`
                : 'Ready when optimisation finishes'}
            </div>
          </div>
        </div>

        <div className="flex gap-1">
          {hasMessages && (
            <Button variant="ghost" size="sm" onClick={clearMessages} className="text-[10px] font-semibold">
              Clear
            </Button>
          )}
          <Button variant="ghost" size="sm" onClick={toggleExpanded} className="text-[12px]">
            {'>'}
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0 p-3 space-y-3 overscroll-contain">
        {!hasMessages ? (
          <EmptyChat />
        ) : (
          <>
            {messages.map((message, index) => (
              <ChatMessage key={index} message={message} />
            ))}

            <AnimatePresence>
              {isLoading && (
                <m.div
                  className="flex items-center gap-2 p-2 self-start"
                  style={{
                    backgroundColor: 'var(--surface-3)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '10px 10px 10px 3px',
                  }}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 10 }}
                >
                  <Spinner size={12} color="var(--pink)" />
                  <span style={{ fontSize: '11.5px', color: 'var(--text-secondary)' }}>
                    Thinking...
                  </span>
                </m.div>
              )}
            </AnimatePresence>

            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {phase === 'results' && hasMessages && <QuickActions />}
      <ChatInput />
    </m.div>
  );
}
