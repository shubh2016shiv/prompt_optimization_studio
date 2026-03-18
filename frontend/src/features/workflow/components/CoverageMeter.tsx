/**
 * CoverageMeter Component
 * 
 * Visual display of TCRTE coverage scores with animated bars.
 */

import { m, useMotionValue, animate } from 'framer-motion';
import { useEffect, useState } from 'react';
import { Badge } from '@/components/ui';
import { AnimatedProgressBar } from '@/components/feedback';
import { TCRTE_DIMENSIONS } from '@/constants';
import type { TCRTEScores } from '@/types';

interface CoverageMeterProps {
  /** TCRTE dimension scores */
  tcrte: TCRTEScores;
  /** Overall score (0-100) */
  overallScore: number;
}

const STATUS_COLORS = {
  good: { color: 'var(--success)', bg: 'var(--success-soft)' },
  weak: { color: 'var(--warning)', bg: 'var(--warning-soft)' },
  missing: { color: 'var(--danger)', bg: 'var(--danger-soft)' },
} as const;

const DIMENSION_COLORS: Record<string, string> = {
  task: 'var(--accent)',
  context: 'var(--cyan)',
  role: 'var(--purple)',
  tone: 'var(--pink)',
  execution: 'var(--orange)',
};

/**
 * Animated counter component for the overall score.
 */
function AnimatedCounter({ value }: { value: number }) {
  const [displayValue, setDisplayValue] = useState(0);
  const motionValue = useMotionValue(0);

  useEffect(() => {
    const controls = animate(motionValue, value, {
      duration: 0.8,
      ease: [0.25, 0.1, 0.25, 1],
      onUpdate: (latest) => setDisplayValue(Math.round(latest)),
    });

    return () => controls.stop();
  }, [value, motionValue]);

  const color = value >= 70 ? 'var(--success)' : value >= 40 ? 'var(--warning)' : 'var(--danger)';

  return (
    <div className="text-center">
      <div 
        className="text-3xl font-extrabold leading-none"
        style={{ color }}
      >
        {displayValue}
      </div>
      <div className="text-[10px] font-semibold text-[var(--text-tertiary)]">
        /100
      </div>
    </div>
  );
}

/**
 * TCRTE coverage meter with animated progress bars.
 */
export function CoverageMeter({ tcrte, overallScore }: CoverageMeterProps) {
  return (
    <div 
      className="p-4 rounded-xl"
      style={{
        backgroundColor: 'var(--surface)',
        border: '1px solid var(--border)',
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="text-[10px] font-bold uppercase tracking-[0.8px] text-[var(--text-tertiary)] mb-0.5">
            TCRTE Coverage
          </div>
          <div className="text-[11px] text-[var(--text-secondary)]">
            Prompt completeness audit
          </div>
        </div>
        <AnimatedCounter value={overallScore} />
      </div>

      {/* Dimension bars */}
      <div className="space-y-3">
        {TCRTE_DIMENSIONS.map((dimension) => {
          const score = tcrte[dimension.id];
          const statusStyle = STATUS_COLORS[score.status];
          const barColor = DIMENSION_COLORS[dimension.id] || 'var(--accent)';

          return (
            <m.div
              key={dimension.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3 }}
            >
              {/* Dimension header */}
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <Badge
                    variant={score.status === 'good' ? 'success' : score.status === 'weak' ? 'warning' : 'danger'}
                    size="sm"
                  >
                    {score.status.toUpperCase()}
                  </Badge>
                  <span className="text-[12px] font-semibold text-[var(--text-primary)]">
                    {dimension.label}
                  </span>
                  <span className="text-[10.5px] text-[var(--text-tertiary)]">
                    {dimension.description}
                  </span>
                </div>
                <span 
                  className="text-[11px] font-bold font-mono"
                  style={{ color: statusStyle.color }}
                >
                  {score.score}%
                </span>
              </div>

              {/* Progress bar */}
              <AnimatedProgressBar
                value={score.score}
                color={barColor}
                height={5}
              />

              {/* Note */}
              {score.note && (
                <p className="text-[10.5px] text-[var(--text-tertiary)] mt-1 pl-0.5">
                  {score.note}
                </p>
              )}
            </m.div>
          );
        })}
      </div>
    </div>
  );
}
