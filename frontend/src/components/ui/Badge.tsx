/**
 * Badge Component
 * 
 * A small label for status indicators, tags, and counts.
 */

import { type HTMLAttributes } from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  `inline-flex items-center justify-center gap-1 
   rounded-md px-2 py-0.5
   text-xs font-semibold
   border
   transition-colors duration-150`,
  {
    variants: {
      variant: {
        default: `
          bg-[var(--surface-raised)] text-[var(--text-secondary)]
          border-[var(--border)]
        `,
        accent: `
          bg-[var(--accent-soft)] text-[var(--accent)]
          border-[var(--accent)]/30
        `,
        success: `
          bg-[var(--success-soft)] text-[var(--success)]
          border-[var(--success)]/30
        `,
        warning: `
          bg-[var(--warning-soft)] text-[var(--warning)]
          border-[var(--warning)]/30
        `,
        danger: `
          bg-[var(--danger-soft)] text-[var(--danger)]
          border-[var(--danger)]/30
        `,
        purple: `
          bg-[var(--purple-soft)] text-[var(--purple)]
          border-[var(--purple)]/30
        `,
        cyan: `
          bg-[var(--cyan-soft)] text-[var(--cyan)]
          border-[var(--cyan)]/30
        `,
        pink: `
          bg-[var(--pink-soft)] text-[var(--pink)]
          border-[var(--pink)]/30
        `,
        orange: `
          bg-[var(--orange-soft)] text-[var(--orange)]
          border-[var(--orange)]/30
        `,
        teal: `
          bg-[var(--teal-soft)] text-[var(--teal)]
          border-[var(--teal)]/30
        `,
      },
      size: {
        sm: 'text-[10px] px-1.5 py-0',
        md: 'text-xs px-2 py-0.5',
        lg: 'text-sm px-2.5 py-1',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'md',
    },
  }
);

export interface BadgeProps
  extends HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

/**
 * Badge component for status indicators and labels.
 * 
 * @example
 * ```tsx
 * <Badge variant="success">GOOD</Badge>
 * <Badge variant="warning" size="sm">WEAK</Badge>
 * ```
 */
function Badge({ className, variant, size, ...props }: BadgeProps) {
  return (
    <span
      className={cn(badgeVariants({ variant, size }), className)}
      {...props}
    />
  );
}

export { Badge, badgeVariants };
