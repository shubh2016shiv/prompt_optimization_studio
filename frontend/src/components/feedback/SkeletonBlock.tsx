/**
 * SkeletonBlock Component
 * 
 * Animated placeholder for loading states with shimmer effect.
 */

import { cn } from '@/lib/utils';

interface SkeletonBlockProps {
  /** Width (CSS value or number for pixels) */
  width?: string | number;
  /** Height (CSS value or number for pixels) */
  height?: string | number;
  /** Border radius variant */
  rounded?: 'sm' | 'md' | 'lg' | 'full';
  /** Additional CSS classes */
  className?: string;
}

const roundedClasses = {
  sm: 'rounded-sm',
  md: 'rounded-md',
  lg: 'rounded-lg',
  full: 'rounded-full',
};

/**
 * Skeleton placeholder with shimmer animation.
 * 
 * @example
 * ```tsx
 * <SkeletonBlock width={200} height={20} />
 * <SkeletonBlock width="100%" height={100} rounded="lg" />
 * ```
 */
export function SkeletonBlock({
  width = '100%',
  height = 16,
  rounded = 'md',
  className,
}: SkeletonBlockProps) {
  const style = {
    width: typeof width === 'number' ? `${width}px` : width,
    height: typeof height === 'number' ? `${height}px` : height,
  };

  return (
    <div
      className={cn(
        'skeleton-shimmer',
        roundedClasses[rounded],
        className
      )}
      style={style}
      aria-hidden="true"
    />
  );
}

/**
 * Pre-composed skeleton layouts for common use cases.
 */
export function SkeletonText({ lines = 3 }: { lines?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: lines }).map((_, i) => (
        <SkeletonBlock
          key={i}
          width={i === lines - 1 ? '70%' : '100%'}
          height={14}
        />
      ))}
    </div>
  );
}

export function SkeletonCard() {
  return (
    <div className="p-4 space-y-3 bg-[var(--surface)] border border-[var(--border)] rounded-lg">
      <div className="flex items-center gap-3">
        <SkeletonBlock width={40} height={40} rounded="full" />
        <div className="flex-1 space-y-2">
          <SkeletonBlock width={120} height={14} />
          <SkeletonBlock width={80} height={12} />
        </div>
      </div>
      <SkeletonText lines={2} />
    </div>
  );
}

export function SkeletonCoverageMeter() {
  return (
    <div className="p-4 bg-[var(--surface)] border border-[var(--border)] rounded-lg space-y-4">
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <SkeletonBlock width={120} height={12} />
          <SkeletonBlock width={180} height={10} />
        </div>
        <SkeletonBlock width={50} height={40} />
      </div>
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <SkeletonBlock width={60} height={18} />
              <SkeletonBlock width={80} height={14} />
            </div>
            <SkeletonBlock width={40} height={14} />
          </div>
          <SkeletonBlock width="100%" height={5} />
        </div>
      ))}
    </div>
  );
}

export function SkeletonVariantCard() {
  return (
    <div className="bg-[var(--surface)] border border-[var(--border)] rounded-lg overflow-hidden">
      <div className="px-4 py-3 border-b border-[var(--border)] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <SkeletonBlock width={30} height={20} />
          <SkeletonBlock width={100} height={16} />
        </div>
        <SkeletonBlock width={60} height={24} />
      </div>
      <div className="p-4 space-y-3">
        <SkeletonBlock width="100%" height={12} />
        <div className="flex gap-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <SkeletonBlock key={i} width={40} height={20} />
          ))}
        </div>
        <SkeletonBlock width="100%" height={150} />
      </div>
    </div>
  );
}
