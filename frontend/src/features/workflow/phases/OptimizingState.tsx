/**
 * OptimizingState Component
 *
 * Full-panel live phase tracker shown while optimization runs.
 * Shows the 4 execution phases (A→B→C→D) with animated connecting lines.
 */

import { m } from 'framer-motion';
import { useWorkflowStore, useCurrentModel } from '@/store';
import { FRAMEWORKS } from '@/constants';

const PIPELINE_PHASES = [
  {
    id: 'A',
    label: 'Preflight & Validation',
    sublabel: 'Checking provider keys, budgets, dataset constraints',
    color: 'var(--success)',
    delay: 0,
  },
  {
    id: 'B',
    label: 'Framework Resolution',
    sublabel: 'Auto-selecting framework, computing CoRe hops, kNN retrieval',
    color: 'var(--teal)',
    delay: 0.4,
  },
  {
    id: 'C',
    label: 'Variant Generation',
    sublabel: 'Generating Conservative · Structured · Advanced',
    color: 'var(--accent)',
    delay: 0.8,
  },
  {
    id: 'D',
    label: 'Quality Gate',
    sublabel: 'Critique-and-enhance pass, guard injection, TCRTE rescore',
    color: 'var(--purple)',
    delay: 1.4,
  },
];

export function OptimizingState() {
  const framework = useWorkflowStore((state) => state.framework);
  const model = useCurrentModel();
  const frameworkInfo = FRAMEWORKS.find((f) => f.id === framework);

  return (
    <m.div
      className="flex flex-col items-center justify-center h-full gap-10 px-8"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.25 }}
    >
      {/* Header */}
      <div className="text-center space-y-2">
        <div
          style={{
            width: 52,
            height: 52,
            borderRadius: 14,
            background: 'linear-gradient(135deg, var(--accent-soft), var(--purple-soft))',
            border: '1px solid var(--accent-glow)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 24,
            margin: '0 auto 12px',
          }}
        >
          ⬡
        </div>
        <h2
          className="font-bold"
          style={{ fontSize: 'var(--text-lg)', color: 'var(--text-primary)' }}
        >
          Generating optimised variants…
        </h2>
        {frameworkInfo && model && (
          <p style={{ fontSize: 'var(--text-base)', color: 'var(--text-secondary)' }}>
            {frameworkInfo.label} · {model.label}
          </p>
        )}
      </div>

      {/* Phase tracker */}
      <div className="w-full space-y-3" style={{ maxWidth: 480 }}>
        {PIPELINE_PHASES.map((phase, index) => (
          <m.div
            key={phase.id}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, delay: phase.delay }}
          >
            <div className="flex gap-4">
              {/* Phase letter badge + connector */}
              <div className="flex flex-col items-center gap-1" style={{ flexShrink: 0 }}>
                <m.div
                  className="w-8 h-8 rounded-full flex items-center justify-center font-bold"
                  style={{
                    fontSize: '11px',
                    fontFamily: 'var(--font-mono)',
                    backgroundColor: `${phase.color}18`,
                    border: `1.5px solid ${phase.color}50`,
                    color: phase.color,
                  }}
                  initial={{ scale: 0.6, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ duration: 0.25, delay: phase.delay }}
                >
                  {phase.id}
                </m.div>
                {index < PIPELINE_PHASES.length - 1 && (
                  <m.div
                    style={{ width: 2, flex: 1, minHeight: 12, backgroundColor: 'var(--border)' }}
                    initial={{ height: 0 }}
                    animate={{ height: '100%' }}
                    transition={{ duration: 0.3, delay: phase.delay + 0.15 }}
                  />
                )}
              </div>

              {/* Phase info */}
              <div className="pb-4">
                <div className="flex items-center gap-2 mb-0.5">
                  <span style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--text-primary)' }}>
                    {phase.label}
                  </span>
                  {/* Animated current phase indicator */}
                  {index === 2 && (
                    <span
                      className="w-1.5 h-1.5 rounded-full"
                      style={{
                        backgroundColor: phase.color,
                        animation: 'ctaPulse 1.2s ease-in-out infinite',
                      }}
                    />
                  )}
                </div>
                <p style={{ fontSize: '10.5px', color: 'var(--text-tertiary)', lineHeight: 1.5 }}>
                  {phase.sublabel}
                </p>
              </div>
            </div>
          </m.div>
        ))}
      </div>

      {/* Estimated time note */}
      <p style={{ fontSize: '10.5px', color: 'var(--text-tertiary)' }}>
        This typically takes 15–30 seconds · do not close the window
      </p>
    </m.div>
  );
}
