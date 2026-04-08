/**
 * ChatMessage Component
 * 
 * A single chat message with markdown/code rendering.
 */

import { m } from 'framer-motion';
import { CopyButton } from '@/components/feedback';
import type { ChatMessage as ChatMessageType } from '@/types';

interface ChatMessageProps {
  /** The message data */
  message: ChatMessageType;
}

/**
 * Parse markdown-style code blocks and bold text.
 */
function parseMessageContent(text: string): React.ReactNode[] {
  const parts = text.split(/(```[\s\S]*?```)/g);

  return parts.map((part, index) => {
    // Handle code blocks
    if (part.startsWith('```')) {
      const lines = part.split('\n');
      const langLine = lines[0]?.replace('```', '').trim();
      const body = lines.slice(1).join('\n').replace(/```$/, '');

      return (
        <div key={index} className="my-2 relative">
          {langLine && (
            <div className="text-[9.5px] font-bold uppercase tracking-[0.5px] text-[var(--text-tertiary)] mb-1">
              {langLine}
            </div>
          )}
          <pre 
            className="p-3 rounded-lg overflow-x-auto text-[10.5px] font-mono leading-relaxed whitespace-pre-wrap break-words"
            style={{
              backgroundColor: 'var(--background)',
              border: '1px solid var(--border)',
              color: 'var(--cyan)',
            }}
          >
            {body}
          </pre>
          <div className="absolute top-0 right-1.5" style={{ top: langLine ? '26px' : '6px' }}>
            <CopyButton text={body} />
          </div>
        </div>
      );
    }

    // Handle bold text
    const boldParts = part.split(/(\*\*[^*]+\*\*)/g).map((bp, j) => {
      if (bp.startsWith('**')) {
        return (
          <strong key={j} className="font-bold text-[var(--text-primary)]">
            {bp.replace(/\*\*/g, '')}
          </strong>
        );
      }
      return <span key={j} className="whitespace-pre-wrap">{bp}</span>;
    });

    return <span key={index}>{boldParts}</span>;
  });
}

/**
 * Single chat message bubble.
 */
export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const bubbleStyle = isUser
    ? {
        background: 'linear-gradient(135deg, var(--accent-soft), var(--purple-soft))',
        border: '1px solid var(--accent)30',
        color: 'var(--text-primary)',
        maxWidth: '88%',
      }
    : {
        backgroundColor: 'var(--surface)',
        border: '1px solid var(--border)',
        color: 'var(--text-primary)',
        maxWidth: '96%',
      };

  return (
    <m.div
      className={`flex flex-col gap-1 ${isUser ? 'items-end' : 'items-start'}`}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
    >
      {/* Sender label */}
      <div 
        className={`text-[9.5px] font-bold tracking-[0.6px] text-[var(--text-tertiary)] ${isUser ? 'pr-0.5' : 'pl-0.5'}`}
      >
        {isUser ? 'YOU' : '✦ APOST AI'}
      </div>

      {/* Message bubble */}
      <div
        className={`p-3 leading-relaxed overflow-y-auto ${isUser ? 'text-[12.5px] rounded-[11px_11px_3px_11px]' : 'text-[12px] rounded-[11px_11px_11px_3px]'}`}
        style={{
          ...bubbleStyle,
          maxHeight: 'min(38vh, 24rem)',
          overflowWrap: 'anywhere',
        }}
      >
        {isUser ? (
          <span className="whitespace-pre-wrap break-words">{message.content}</span>
        ) : (
          parseMessageContent(message.content)
        )}
      </div>

      {/* Timestamp */}
      {message.timestamp && (
        <div className="text-[9.5px] text-[var(--text-tertiary)]">
          {message.timestamp}
        </div>
      )}
    </m.div>
  );
}
