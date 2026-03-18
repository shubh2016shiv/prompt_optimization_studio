/**
 * Button Component
 * 
 * A versatile button with multiple variants, sizes, and states.
 * Includes subtle animations for premium feel.
 */

import { forwardRef, type ButtonHTMLAttributes } from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const buttonVariants = cva(
  // Base styles
  `inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg 
   font-semibold transition-all duration-150 ease-out
   focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2
   disabled:pointer-events-none disabled:opacity-50
   active:scale-[0.98]`,
  {
    variants: {
      variant: {
        primary: `
          bg-gradient-to-r from-[var(--accent)] to-[var(--purple)]
          text-white shadow-md
          hover:shadow-lg hover:shadow-[var(--accent-glow)]
          hover:scale-[1.02]
        `,
        secondary: `
          bg-[var(--surface-raised)] text-[var(--text-primary)]
          border border-[var(--border)]
          hover:bg-[var(--surface-overlay)] hover:border-[var(--border-elevated)]
        `,
        ghost: `
          text-[var(--text-secondary)]
          hover:text-[var(--text-primary)] hover:bg-[var(--surface-raised)]
        `,
        danger: `
          bg-[var(--danger-soft)] text-[var(--danger)]
          border border-[var(--danger)]/30
          hover:bg-[var(--danger)]/20 hover:border-[var(--danger)]/50
        `,
        success: `
          bg-gradient-to-r from-[var(--teal)] to-[var(--cyan)]
          text-[var(--background)] font-bold
          hover:shadow-lg hover:shadow-[var(--teal-soft)]
          hover:scale-[1.02]
        `,
      },
      size: {
        sm: 'h-8 px-3 text-xs',
        md: 'h-10 px-4 text-sm',
        lg: 'h-12 px-6 text-base',
        icon: 'h-9 w-9',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  }
);

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  /** Render as a different element using Radix Slot */
  asChild?: boolean;
}

/**
 * Button component with multiple variants and smooth animations.
 * 
 * @example
 * ```tsx
 * <Button variant="primary" size="lg">
 *   Analyse Gaps
 * </Button>
 * ```
 */
const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button';
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);

Button.displayName = 'Button';

export { Button, buttonVariants };
