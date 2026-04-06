/**
 * Input Component
 * 
 * A styled text input with focus states and optional icons.
 */

import { forwardRef, type InputHTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  /** Optional icon to show on the right side */
  rightIcon?: React.ReactNode;
}

/**
 * Input component with consistent styling and focus states.
 * 
 * @example
 * ```tsx
 * <Input 
 *   placeholder="Enter your API key" 
 *   type="password"
 *   rightIcon={<EyeIcon />}
 * />
 * ```
 */
const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, rightIcon, ...props }, ref) => {
    return (
      <div className="relative w-full">
        <input
          type={type}
          className={cn(
            `w-full h-10 px-3 py-2
             bg-[var(--surface)] 
             border border-[var(--border-subtle)] 
             rounded-lg
             text-sm text-[var(--text-primary)]
             font-mono
             placeholder:text-[var(--text-tertiary)]
             transition-colors duration-150
             focus:outline-none focus:border-[#1D9E75] focus:ring-1 focus:ring-[rgba(29,158,117,0.25)]
             disabled:opacity-50 disabled:cursor-not-allowed`,
            rightIcon && 'pr-10',
            className
          )}
          ref={ref}
          {...props}
        />
        {rightIcon && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-tertiary)]">
            {rightIcon}
          </div>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

export { Input };

