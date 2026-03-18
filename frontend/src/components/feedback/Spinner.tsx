/**
 * Spinner Component
 * 
 * An animated loading spinner with configurable size and color.
 */

import { cn } from '@/lib/utils';

interface SpinnerProps {
  /** Size in pixels */
  size?: number;
  /** CSS color value */
  color?: string;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Animated spinner for loading states.
 * 
 * @example
 * ```tsx
 * <Spinner size={24} color="var(--accent)" />
 * ```
 */
export function Spinner({ 
  size = 16, 
  color = 'currentColor',
  className 
}: SpinnerProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth="2.5"
      className={cn('shrink-0', className)}
      aria-label="Loading"
    >
      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83">
        <animateTransform
          attributeName="transform"
          type="rotate"
          from="0 12 12"
          to="360 12 12"
          dur="0.85s"
          repeatCount="indefinite"
        />
      </path>
    </svg>
  );
}
