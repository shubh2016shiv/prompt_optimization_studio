/**
 * Textarea Component
 * 
 * A styled multi-line text input with auto-resize capability.
 */

import { forwardRef, type TextareaHTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {}

/**
 * Textarea component with consistent styling and focus states.
 * 
 * @example
 * ```tsx
 * <Textarea 
 *   placeholder="Enter your prompt..."
 *   rows={6}
 * />
 * ```
 */
const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => {
    return (
      <textarea
        className={cn(
          `w-full min-h-[80px] px-3 py-2
           bg-[var(--surface)] 
           border border-[var(--border-subtle)] 
           rounded-lg
           text-sm text-[var(--text-primary)]
           font-mono leading-relaxed
           placeholder:text-[var(--text-tertiary)]
           transition-colors duration-150
           resize-vertical
           focus:outline-none focus:border-[#1D9E75] focus:ring-1 focus:ring-[rgba(29,158,117,0.25)]
           disabled:opacity-50 disabled:cursor-not-allowed`,
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);

Textarea.displayName = 'Textarea';

export { Textarea };

