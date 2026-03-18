/**
 * OptimizingState Component
 * 
 * Loading state shown while optimization is in progress.
 */

import { m } from 'framer-motion';
import { Spinner } from '@/components/feedback';
import { SkeletonVariantCard } from '@/components/feedback';
import { useWorkflowStore, useCurrentModel } from '@/store';
import { FRAMEWORKS } from '@/constants';

/**
 * Optimizing state with spinner and skeleton preview.
 */
export function OptimizingState() {
  const framework = useWorkflowStore((state) => state.framework);
  const model = useCurrentModel();
  
  const frameworkInfo = FRAMEWORKS.find((f) => f.id === framework);

  return (
    <m.div
      className="flex flex-col items-center justify-center h-full gap-4 px-4"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.25 }}
    >
      {/* Spinner */}
      <Spinner size={36} color="var(--accent)" />
      
      {/* Status text */}
      <div className="text-center">
        <h2 className="text-sm font-semibold text-[var(--text-primary)] mb-1">
          Generating optimised variants…
        </h2>
        <p className="text-[12px] text-[var(--text-secondary)]">
          {frameworkInfo?.label} · {model?.label}
        </p>
      </div>

      {/* Skeleton preview */}
      <div className="w-full max-w-lg mt-4 space-y-4">
        <SkeletonVariantCard />
        <SkeletonVariantCard />
      </div>
    </m.div>
  );
}
