/**
 * AnalyzingState Component
 *
 * Full-panel TCRTE scan animation shown while gap analysis runs.
 * Shows 5 skeleton dimension rows with a staggered scan-pulse effect.
 */

import { m } from 'framer-motion';

const TCRTE_DIMS = [
  { label: 'Task',      sublabel: 'Core objective clarity',      color: 'var(--accent)',  delay: 0 },
  { label: 'Context',   sublabel: 'Background and grounding',    color: 'var(--cyan)',    delay: 0.12 },
  { label: 'Role',      sublabel: 'Model persona and expertise', color: 'var(--purple)',  delay: 0.24 },
  { label: 'Tone',      sublabel: 'Style and register',          color: 'var(--pink)',    delay: 0.36 },
  { label: 'Execution', sublabel: 'Format and constraints',      color: 'var(--orange)',  delay: 0.48 },
];

export function AnalyzingState() {
  return (
    <m.div
      className="flex flex-col items-center justify-center h-full gap-8 px-8"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.25 }}
    >
      {/* Header */}
      <div className="text-center space-y-2">
        {/* Scanning icon */}
        <div
          style={{
            width: 48,
            height: 48,
            borderRadius: 14,
            background: 'linear-gradient(135deg, var(--teal-soft), var(--accent-soft))',
            border: '1px solid var(--teal-glow)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 22,
            margin: '0 auto 12px',
          }}
        >
          🔍
        </div>
        <h2
          className="font-bold"
          style={{ fontSize: 'var(--text-lg)', color: 'var(--text-primary)' }}
        >
          Running TCRTE gap analysis…
        </h2>
        <p style={{ fontSize: 'var(--text-base)', color: 'var(--text-secondary)' }}>
          Auditing your prompt across 5 structural coverage dimensions
        </p>
      </div>

      {/* Scanning progress bar */}
      <div
        className="w-full rounded-full overflow-hidden"
        style={{ maxWidth: 480, height: 3, backgroundColor: 'var(--border)' }}
      >
        <m.div
          className="h-full rounded-full"
          style={{ background: 'linear-gradient(90deg, var(--teal), var(--accent))' }}
          initial={{ width: '0%' }}
          animate={{ width: '85%' }}
          transition={{ duration: 2.5, ease: 'easeOut' }}
        />
      </div>

      {/* 5 TCRTE skeleton rows */}
      <div className="w-full space-y-3" style={{ maxWidth: 480 }}>
        {TCRTE_DIMS.map((dim) => (
          <m.div
            key={dim.label}
            className="flex items-center gap-3 p-3 rounded-xl"
            style={{
              backgroundColor: 'var(--surface)',
              border: '1px solid var(--border)',
            }}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, delay: dim.delay }}
          >
            {/* Dim color dot */}
            <div
              style={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                backgroundColor: dim.color,
                flexShrink: 0,
                opacity: 0.7,
              }}
            />

            {/* Labels */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between mb-1.5">
                <span style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--text-primary)' }}>
                  {dim.label}
                </span>
                <span style={{ fontSize: '10px', color: 'var(--text-tertiary)' }}>
                  {dim.sublabel}
                </span>
              </div>
              {/* Skeleton bar */}
              <div
                className="h-1 rounded-full overflow-hidden"
                style={{ backgroundColor: 'var(--border)' }}
              >
                <div
                  className="h-full rounded-full scan-pulse skeleton-shimmer"
                  style={{ backgroundColor: dim.color, width: '100%', opacity: 0.5 }}
                />
              </div>
            </div>

            {/* Score placeholder */}
            <div
              className="skeleton-shimmer rounded"
              style={{ width: 28, height: 16, flexShrink: 0 }}
            />
          </m.div>
        ))}
      </div>
    </m.div>
  );
}
