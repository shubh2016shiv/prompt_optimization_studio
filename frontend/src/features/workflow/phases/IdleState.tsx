/**
 * IdleState Component
 * 
 * The initial state shown when no analysis has been run yet.
 */

import { m } from 'framer-motion';
import { Badge } from '@/components/ui';

const FEATURES = [
  'TCRTE Gap Scoring',
  'CoRe Multi-hop',
  'RAL-Writer Restate',
  'Claude Prefill',
  'TextGrad Guards',
  '3 Variants',
];

/**
 * Initial idle state with welcome message and feature badges.
 */
export function IdleState() {
  return (
    <m.div
      className="flex flex-col items-center justify-center h-full gap-4 text-center px-4"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.25 }}
    >
      {/* Logo placeholder */}
      <div className="text-5xl opacity-10">⬡</div>

      {/* Title */}
      <div>
        <h2 className="text-lg font-bold text-[var(--text-primary)] mb-1">
          Ready for intelligent optimisation
        </h2>
        <p className="text-[12.5px] text-[var(--text-secondary)] max-w-[380px] leading-relaxed">
          Click{' '}
          <strong style={{ color: 'var(--teal)' }}>🔍 Analyse Gaps First</strong>
          {' '}— the tool will audit your prompt against the TCRTE framework, score each dimension, and ask you targeted questions to fill the gaps before optimising.
        </p>
        <p className="text-[12.5px] text-[var(--text-secondary)] mt-3">
          Or click{' '}
          <strong className="text-[var(--text-secondary)]">Skip → Optimise</strong>
          {' '}to run directly.
        </p>
      </div>

      {/* Feature badges */}
      <div className="flex flex-wrap justify-center gap-1.5 mt-2">
        {FEATURES.map((feature) => (
          <Badge key={feature} variant="default" size="sm">
            {feature}
          </Badge>
        ))}
      </div>
    </m.div>
  );
}
