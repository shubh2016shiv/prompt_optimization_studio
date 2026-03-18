/**
 * AnimatedProgressBar Component
 * 
 * A progress bar with spring-animated width transitions.
 */

import { m } from 'framer-motion';
import { useAnimatedPercentage } from '@/hooks';
import { cn } from '@/lib/utils';

interface AnimatedProgressBarProps {
  /** Progress value from 0-100 */
  value: number;
  /** Bar color (CSS variable or hex) */
  color?: string;
  /** Background color */
  backgroundColor?: string;
  /** Height in pixels */
  height?: number;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Progress bar with smooth spring animation.
 * 
 * @example
 * ```tsx
 * <AnimatedProgressBar 
 *   value={75} 
 *   color="var(--success)" 
 * />
 * ```
 */
export function AnimatedProgressBar({
  value,
  color = 'var(--accent)',
  backgroundColor = 'var(--border)',
  height = 5,
  className,
}: AnimatedProgressBarProps) {
  const animatedWidth = useAnimatedPercentage(value);

  return (
    <div
      className={cn('overflow-hidden rounded-full', className)}
      style={{ 
        height: `${height}px`,
        backgroundColor,
      }}
    >
      <m.div
        className="h-full rounded-full"
        style={{
          width: animatedWidth.get() + '%',
          background: `linear-gradient(90deg, ${color}99, ${color})`,
        }}
        initial={{ width: 0 }}
        animate={{ width: `${value}%` }}
        transition={{
          type: 'spring',
          stiffness: 100,
          damping: 20,
        }}
      />
    </div>
  );
}
