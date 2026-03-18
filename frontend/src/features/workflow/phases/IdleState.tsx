/**
 * IdleState Component
 * 
 * The initial state shown when no analysis has been run yet.
 * Shows a 3-step visual flow instead of dense paragraphs.
 */

import { m } from 'framer-motion';

const FLOW_STEPS = [
  {
    icon: '🔍',
    label: 'Analyse',
    sublabel: 'TCRTE gap audit',
    color: 'var(--primary-action)',
    colorSoft: 'var(--primary-action-soft)',
    colorGlow: 'var(--primary-action-glow)',
  },
  {
    icon: '💬',
    label: 'Interview',
    sublabel: 'Fill the gaps',
    color: 'var(--accent)',
    colorSoft: 'var(--accent-soft)',
    colorGlow: 'var(--accent-glow)',
  },
  {
    icon: '⬡',
    label: 'Optimise',
    sublabel: '3 variants generated',
    color: 'var(--purple)',
    colorSoft: 'var(--purple-soft)',
    colorGlow: 'rgba(181, 123, 238, 0.28)',
  },
];

/**
 * Initial idle state with a compact 3-step flow diagram.
 */
export function IdleState() {
  return (
    <m.div
      className="flex flex-col items-center justify-center h-full gap-8 text-center px-6"
      style={{ maxWidth: '720px', margin: '0 auto' }}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.25 }}
    >
      {/* Logo mark */}
      <div
        className="w-14 h-14 rounded-2xl flex items-center justify-center text-2xl"
        style={{
          background: 'linear-gradient(135deg, var(--primary-action-soft), var(--accent-soft))',
          border: '1px solid var(--primary-action-glow)',
          color: 'var(--primary-action)',
        }}
      >
        ⬡
      </div>

      {/* Headline */}
      <div className="space-y-2">
        <h2
          className="font-bold text-[var(--text-primary)]"
          style={{ fontSize: 'var(--text-xl)' }}
        >
          Ready to optimise your prompt
        </h2>
        <p
          className="text-[var(--text-secondary)]"
          style={{ fontSize: 'var(--text-base)', maxWidth: '420px' }}
        >
          Paste your prompt on the left, then click <strong style={{ color: 'var(--primary-action)' }}>Analyse Gaps First</strong> below.
        </p>
      </div>

      {/* 3-step flow */}
      <div className="flex items-center gap-3">
        {FLOW_STEPS.map((step, index) => (
          <div key={step.label} className="flex items-center gap-3">
            {/* Step card */}
            <m.div
              className="flex flex-col items-center gap-2 px-5 py-4 rounded-xl"
              style={{
                backgroundColor: step.colorSoft,
                border: `1px solid ${step.colorGlow}`,
                minWidth: '110px',
              }}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: index * 0.08 }}
            >
              <span className="text-2xl">{step.icon}</span>
              <div>
                <div
                  className="font-bold"
                  style={{ fontSize: 'var(--text-sm)', color: step.color }}
                >
                  {step.label}
                </div>
                <div
                  className="text-[var(--text-tertiary)]"
                  style={{ fontSize: 'var(--text-xs)' }}
                >
                  {step.sublabel}
                </div>
              </div>
            </m.div>

            {/* Arrow between steps */}
            {index < FLOW_STEPS.length - 1 && (
              <span
                className="text-[var(--text-tertiary)]"
                style={{ fontSize: 'var(--text-lg)' }}
              >
                →
              </span>
            )}
          </div>
        ))}
      </div>

      {/* Skip hint */}
      <p
        className="text-[var(--text-tertiary)]"
        style={{ fontSize: 'var(--text-sm)' }}
      >
        Or use <strong className="text-[var(--text-secondary)]">Skip → Optimise</strong> to run directly without gap analysis.
      </p>
    </m.div>
  );
}
