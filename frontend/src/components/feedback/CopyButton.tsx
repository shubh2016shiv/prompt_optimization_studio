/**
 * CopyButton Component
 * 
 * A button that copies text to clipboard with visual feedback.
 */

import { useState, useCallback } from 'react';
import { m, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';

interface CopyButtonProps {
  /** Text to copy to clipboard */
  text: string;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Button that copies text with animated checkmark feedback.
 * 
 * @example
 * ```tsx
 * <CopyButton text={systemPrompt} />
 * ```
 */
export function CopyButton({ text, className }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  }, [text]);

  return (
    <button
      onClick={handleCopy}
      className={cn(
        `px-2 py-0.5
         bg-[var(--surface)]
         border border-[var(--border)]
         rounded-md
         text-[10px] font-semibold text-[var(--text-tertiary)]
         transition-all duration-150
         hover:border-[var(--border-elevated)] hover:text-[var(--text-secondary)]
         focus:outline-none focus:ring-2 focus:ring-[var(--accent)]`,
        className
      )}
      aria-label={copied ? 'Copied!' : 'Copy to clipboard'}
    >
      <AnimatePresence mode="wait" initial={false}>
        {copied ? (
          <m.span
            key="check"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            transition={{ duration: 0.15 }}
            className="text-[var(--success)]"
          >
            ✓
          </m.span>
        ) : (
          <m.span
            key="copy"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            transition={{ duration: 0.15 }}
          >
            Copy
          </m.span>
        )}
      </AnimatePresence>
    </button>
  );
}
