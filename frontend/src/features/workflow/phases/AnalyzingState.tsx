/**
 * AnalyzingState Component
 * 
 * Loading state shown while gap analysis is in progress.
 */

import { m } from 'framer-motion';
import { Spinner } from '@/components/feedback';
import { SkeletonCoverageMeter } from '@/components/feedback';

/**
 * Analyzing state with spinner and skeleton preview.
 */
export function AnalyzingState() {
  return (
    <m.div
      className="flex flex-col items-center justify-center h-full gap-4 px-4"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.25 }}
    >
      {/* Spinner */}
      <Spinner size={36} color="var(--teal)" />
      
      {/* Status text */}
      <div className="text-center">
        <h2 className="text-sm font-semibold text-[var(--text-primary)] mb-1">
          Running TCRTE gap analysis…
        </h2>
        <p className="text-[12px] text-[var(--text-secondary)]">
          Auditing Task · Context · Role · Tone · Execution coverage
        </p>
      </div>

      {/* Skeleton preview */}
      <div className="w-full max-w-md mt-4">
        <SkeletonCoverageMeter />
      </div>
    </m.div>
  );
}
