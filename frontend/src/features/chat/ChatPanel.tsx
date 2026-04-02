/**
 * ChatPanel Component
 *
 * Collapsible AI chat panel. Starts collapsed by default.
 * When collapsed: premium icon rail with message count badge.
 * When expanded: full chat interface with context-loaded badge.
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

  // ── Collapsed state ──────────────────────────────────────────
  if (!isExpanded) {
    return (
      <button
        onClick={toggleExpanded}
        className="w-full h-full flex flex-col items-center justify-center gap-3 cursor-pointer transition-colors hover:bg-[var(--surface-raised)] focus:outline-none"
        style={{ borderLeft: '1px solid var(--border)' }}
        title="Open AI Refiner"
        aria-label="Open AI Refiner chat"
      >
        {/* Icon */}
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: 10,
            background: 'linear-gradient(135deg, var(--pink), var(--purple))',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 14,
            boxShadow: phase === 'results' ? '0 0 14px rgba(240,98,146,0.35)' : 'none',
          }}
        >
          ✦
        </div>

        {/* Label */}
        <span
          style={{
            fontSize: '9px',
            fontWeight: 700,
            letterSpacing: '0.8px',
            textTransform: 'uppercase',
            color: 'var(--text-tertiary)',
            writingMode: 'vertical-rl',
            textOrientation: 'mixed',
          }}
        >
          AI Chat
        </span>

        {/* Badge */}
        {hasMessages && (
          <AnimatePresence>
            <m.span
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              className="px-1.5 py-0.5 rounded-full font-bold"
              style={{
                fontSize: '9px',
                backgroundColor: 'var(--pink)',
                color: 'white',
                minWidth: 18,
                textAlign: 'center',
              }}
            >
              {exchangeCount}
            </m.span>
          </AnimatePresence>
        )}

        {/* "Results ready" glow dot */}
        {phase === 'results' && !hasMessages && (
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              backgroundColor: 'var(--pink)',
              animation: 'ctaPulse 1.5s ease-in-out infinite',
            }}
          />
        )}
      </button>
    );
  }

  // ── Expanded state ───────────────────────────────────────────
  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div
        className="px-3 flex items-center justify-between shrink-0"
        style={{ height: 52, borderBottom: '1px solid var(--border)' }}
      >
        <div className="flex items-center gap-2.5">
          <div
            style={{
              width: 28,
              height: 28,
              borderRadius: 9,
              background: 'linear-gradient(135deg, var(--pink), var(--purple))',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 13,
              boxShadow: '0 0 10px rgba(240,98,146,0.25)',
            }}
          >
            ✦
          </div>
          <div>
            <div style={{ fontSize: '12.5px', fontWeight: 700, color: 'var(--text-primary)' }}>
              APOST Refiner
            </div>
            <div style={{ fontSize: '10px', color: 'var(--text-tertiary)' }}>
              {phase === 'results' && exchangeCount === 0
                ? '3 variants loaded · full memory'
                : exchangeCount > 0
                ? `${exchangeCount} exchange${exchangeCount !== 1 ? 's' : ''} · full memory`
                : 'Seeded on optimisation'
              }
            </div>
          </div>
        </div>

        {/* Context loaded badge */}
        {phase === 'results' && (
          <m.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            className="px-2 py-0.5 rounded-full font-bold"
            style={{
              fontSize: '9px',
              color: 'var(--success)',
              backgroundColor: 'var(--success-soft)',
              border: '1px solid rgba(61,214,140,0.25)',
              flexShrink: 0,
            }}
          >
            ✓ Context
          </m.div>
        )}

        <div className="flex gap-1 ml-1">
          {hasMessages && (
            <Button variant="ghost" size="sm" onClick={clearMessages} className="text-[10px] font-semibold">
              Clear
            </Button>
          )}
          <Button variant="ghost" size="sm" onClick={toggleExpanded} className="text-[12px]">
            →
          </Button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
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
                    backgroundColor: 'var(--surface)',
                    border: '1px solid var(--border)',
                    borderRadius: '11px 11px 11px 3px',
                  }}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 10 }}
                >
                  <Spinner size={12} color="var(--pink)" />
                  <span style={{ fontSize: '11.5px', color: 'var(--text-secondary)' }}>
                    Thinking…
                  </span>
                </m.div>
              )}
            </AnimatePresence>

            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Quick actions */}
      {phase === 'results' && hasMessages && <QuickActions />}

      {/* Input */}
      <ChatInput />
    </div>
  );
}
