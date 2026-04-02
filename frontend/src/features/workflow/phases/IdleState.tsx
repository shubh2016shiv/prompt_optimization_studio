/**
 * IdleState Component
 *
 * Full-panel hero shown when no analysis has been run.
 * Features an animated orbital logo, rich 3-step flow, and feature callouts.
 */

import { m } from 'framer-motion';

const FLOW_STEPS = [
  {
    icon: '🔍',
    label: 'Analyse',
    sublabel: 'TCRTE gap audit across 5 dimensions',
    color: 'var(--teal)',
    colorSoft: 'var(--teal-soft)',
    colorGlow: 'var(--teal-glow)',
    number: '01',
  },
  {
    icon: '💬',
    label: 'Interview',
    sublabel: 'Answer targeted questions to fill gaps',
    color: 'var(--accent)',
    colorSoft: 'var(--accent-soft)',
    colorGlow: 'var(--accent-glow)',
    number: '02',
  },
  {
    icon: '⬡',
    label: 'Optimise',
    sublabel: '3 production-grade variants generated',
    color: 'var(--purple)',
    colorSoft: 'var(--purple-soft)',
    colorGlow: 'rgba(181, 123, 238, 0.28)',
    number: '03',
  },
  {
    icon: '✦',
    label: 'Refine',
    sublabel: 'Iterate conversationally with AI chat',
    color: 'var(--pink)',
    colorSoft: 'var(--pink-soft)',
    colorGlow: 'rgba(240, 98, 146, 0.25)',
    number: '04',
  },
];

const FEATURE_PILLS = [
  { label: 'TCRTE', color: 'var(--cyan)' },
  { label: '9 Frameworks', color: 'var(--purple)' },
  { label: '3 Variants', color: 'var(--success)' },
  { label: 'CoRe + RAL', color: 'var(--orange)' },
  { label: 'AI Chat', color: 'var(--pink)' },
  { label: 'Auto-Select', color: 'var(--teal)' },
];

export function IdleState() {
  return (
    <m.div
      className="flex flex-col items-center justify-center h-full gap-10 text-center px-8 overflow-y-auto py-8"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.3 }}
    >
      {/* Hero logo with orbital rings */}
      <div className="relative flex items-center justify-center hero-float" style={{ width: 96, height: 96 }}>
        {/* Outer orbit ring */}
        <div
          className="absolute orbit-ring"
          style={{
            width: 96,
            height: 96,
            borderRadius: '50%',
            border: '1px dashed rgba(45,212,191,0.25)',
          }}
        >
          {/* Orbital dot */}
          <div
            style={{
              position: 'absolute',
              top: -4,
              left: '50%',
              transform: 'translateX(-50%)',
              width: 8,
              height: 8,
              borderRadius: '50%',
              backgroundColor: 'var(--teal)',
              boxShadow: '0 0 8px var(--teal-glow)',
            }}
          />
        </div>

        {/* Inner orbit ring */}
        <div
          className="absolute orbit-ring-reverse"
          style={{
            width: 72,
            height: 72,
            borderRadius: '50%',
            border: '1px dashed rgba(108,138,255,0.20)',
          }}
        >
          <div
            style={{
              position: 'absolute',
              bottom: -4,
              left: '50%',
              transform: 'translateX(-50%)',
              width: 6,
              height: 6,
              borderRadius: '50%',
              backgroundColor: 'var(--accent)',
              boxShadow: '0 0 8px var(--accent-glow)',
            }}
          />
        </div>

        {/* Centre logo */}
        <div
          style={{
            width: 48,
            height: 48,
            borderRadius: 14,
            background: 'linear-gradient(135deg, var(--primary-action), var(--accent))',
            boxShadow: '0 0 24px rgba(45,212,191,0.35), 0 4px 16px rgba(0,0,0,0.4)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 22,
          }}
        >
          ⬡
        </div>
      </div>

      {/* Headline */}
      <div className="space-y-2" style={{ maxWidth: 520 }}>
        <h2
          className="font-extrabold tracking-tight"
          style={{ fontSize: 'var(--text-xl)', color: 'var(--text-primary)', letterSpacing: '-0.3px' }}
        >
          Engineering-grade prompt optimisation
        </h2>
        <p style={{ fontSize: 'var(--text-base)', color: 'var(--text-secondary)', lineHeight: 1.7 }}>
          Paste your prompt in the left panel, then click{' '}
          <strong style={{ color: 'var(--teal)' }}>Analyse Gaps</strong>{' '}
          below. APOST audits it against 5 structural dimensions and generates 3 production-ready variants.
        </p>
      </div>

      {/* 4-step flow */}
      <div className="flex items-start gap-2 flex-wrap justify-center" style={{ maxWidth: 640 }}>
        {FLOW_STEPS.map((step, index) => (
          <div key={step.label} className="flex items-start gap-2">
            {/* Step card */}
            <m.div
              className="flex flex-col items-center gap-2 px-4 py-3 rounded-xl"
              style={{
                backgroundColor: step.colorSoft,
                border: `1px solid ${step.colorGlow}`,
                minWidth: 120,
              }}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, delay: index * 0.07 }}
            >
              <div className="flex items-center justify-between w-full">
                <span style={{ fontSize: 18 }}>{step.icon}</span>
                <span
                  style={{
                    fontSize: '9px',
                    fontWeight: 800,
                    fontFamily: 'var(--font-mono)',
                    color: step.color,
                    opacity: 0.6,
                    letterSpacing: '0.5px',
                  }}
                >
                  {step.number}
                </span>
              </div>
              <div className="text-left w-full">
                <div style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: step.color }}>
                  {step.label}
                </div>
                <div style={{ fontSize: '10px', color: 'var(--text-tertiary)', lineHeight: 1.4, marginTop: 2 }}>
                  {step.sublabel}
                </div>
              </div>
            </m.div>

            {/* Arrow connector */}
            {index < FLOW_STEPS.length - 1 && (
              <span
                style={{ fontSize: '10px', color: 'var(--text-tertiary)', marginTop: 18, flexShrink: 0 }}
              >
                →
              </span>
            )}
          </div>
        ))}
      </div>

      {/* Feature pills */}
      <div className="flex flex-wrap gap-2 justify-center" style={{ maxWidth: 480 }}>
        {FEATURE_PILLS.map((pill) => (
          <span
            key={pill.label}
            className="px-2.5 py-1 rounded-full font-semibold"
            style={{
              fontSize: '10.5px',
              color: pill.color,
              backgroundColor: `${pill.color}14`,
              border: `1px solid ${pill.color}28`,
            }}
          >
            {pill.label}
          </span>
        ))}
      </div>
    </m.div>
  );
}
