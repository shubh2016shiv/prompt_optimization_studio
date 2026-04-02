/**
 * InterviewPhase Component
 *
 * Two-zone layout:
 * - Left zone:  TCRTE coverage rings dashboard + complexity/techniques info
 * - Right zone: Scrollable gap question cards
 *
 * The ProgressRing visualization gives users an immediate intuition of
 * which dimensions are strong (green), weak (amber), or missing (red).
 */

import { m, AnimatePresence } from 'framer-motion';
import { useState } from 'react';
import { Badge } from '@/components/ui';
import { ProgressRing } from '@/components/ui';
import { AnimatedProgressBar } from '@/components/feedback';
import { useWorkflowStore } from '@/store';
import { QuestionCard } from '../components';

// Dimension configuration
const TCRTE_RING_CONFIG = [
  { id: 'task',      label: 'Task',      color: 'var(--accent)'  },
  { id: 'context',   label: 'Context',   color: 'var(--cyan)'    },
  { id: 'role',      label: 'Role',      color: 'var(--purple)'  },
  { id: 'tone',      label: 'Tone',      color: 'var(--pink)'    },
  { id: 'execution', label: 'Execution', color: 'var(--orange)'  },
] as const;

const COMPLEXITY_STYLES = {
  simple:  { color: 'var(--success)', bg: 'var(--success-soft)', icon: '◦' },
  medium:  { color: 'var(--warning)', bg: 'var(--warning-soft)', icon: '◈' },
  complex: { color: 'var(--danger)',  bg: 'var(--danger-soft)',  icon: '◉' },
} as const;

function scoreColor(score: number) {
  if (score >= 70) return 'var(--success)';
  if (score >= 35) return 'var(--warning)';
  return 'var(--danger)';
}

// ─── Overall score ring (larger) ──────────────────────────────
function OverallScoreRing({ score }: { score: number }) {
  const color = scoreColor(score);
  return (
    <div className="flex flex-col items-center gap-1">
      <ProgressRing score={score} color={color} size={72} strokeWidth={5} delay={0} />
      <span style={{ fontSize: '9px', fontWeight: 700, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
        Overall
      </span>
    </div>
  );
}

// ─── Left panel — coverage dashboard ──────────────────────────
function CoverageDashboard() {
  const gapData = useWorkflowStore((state) => state.gapData)!;
  const complexityStyle = COMPLEXITY_STYLES[gapData.complexity];

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div>
        <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-tertiary)', letterSpacing: '0.8px', textTransform: 'uppercase', marginBottom: 4 }}>
          TCRTE Coverage
        </div>
        <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
          Prompt completeness audit
        </div>
      </div>

      {/* Rings row */}
      <div className="flex items-end gap-3 flex-wrap">
        <OverallScoreRing score={gapData.overall_score} />
        <div
          style={{ width: 1, height: 40, backgroundColor: 'var(--border)', flexShrink: 0 }}
        />
        {TCRTE_RING_CONFIG.map((dim, i) => {
          const score = gapData.tcrte[dim.id];
          const color = scoreColor(score.score);
          return (
            <ProgressRing
              key={dim.id}
              score={score.score}
              color={color}
              size={44}
              strokeWidth={3.5}
              sublabel={dim.label}
              delay={i * 0.08 + 0.1}
            />
          );
        })}
      </div>

      {/* Dimension detail bars */}
      <div className="space-y-2.5">
        {TCRTE_RING_CONFIG.map((dim) => {
          const score = gapData.tcrte[dim.id];
          const color = scoreColor(score.score);
          return (
            <m.div
              key={dim.id}
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.25 }}
            >
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-1.5">
                  <span style={{ fontSize: '10px', fontWeight: 700, color }}
                    className="uppercase tracking-wide">
                    {score.status}
                  </span>
                  <span style={{ fontSize: '11px', color: 'var(--text-primary)', fontWeight: 600 }}>
                    {dim.label}
                  </span>
                </div>
                <span style={{ fontSize: '10px', fontWeight: 700, fontFamily: 'var(--font-mono)', color }}>
                  {score.score}%
                </span>
              </div>
              <AnimatedProgressBar value={score.score} color={dim.color} height={4} />
              {score.note && (
                <p style={{ fontSize: '10px', color: 'var(--text-tertiary)', marginTop: 2 }}>
                  {score.note}
                </p>
              )}
            </m.div>
          );
        })}
      </div>

      {/* Complexity */}
      <div
        className="flex items-start gap-2 p-3 rounded-xl"
        style={{ backgroundColor: complexityStyle.bg, border: `1px solid ${complexityStyle.color}28` }}
      >
        <span style={{ fontSize: 14, flexShrink: 0, marginTop: 1 }}>{complexityStyle.icon}</span>
        <div>
          <div style={{ fontSize: '11px', fontWeight: 700, color: complexityStyle.color, textTransform: 'uppercase', letterSpacing: '0.4px' }}>
            {gapData.complexity} complexity
          </div>
          <div style={{ fontSize: '10.5px', color: 'var(--text-secondary)', marginTop: 2, lineHeight: 1.4 }}>
            {gapData.complexity_reason}
          </div>
        </div>
      </div>

      {/* Recommended techniques */}
      {gapData.recommended_techniques.length > 0 && (
        <div>
          <div style={{ fontSize: '9.5px', fontWeight: 700, color: 'var(--text-tertiary)', letterSpacing: '0.8px', textTransform: 'uppercase', marginBottom: 6 }}>
            Recommended Techniques
          </div>
          <div className="flex flex-wrap gap-1.5">
            {gapData.recommended_techniques.map((t) => (
              <Badge key={t} variant="cyan" size="sm">{t}</Badge>
            ))}
          </div>
        </div>
      )}

      {/* Auto-enrichments — collapsible */}
      {gapData.auto_enrichments.length > 0 && (
        <AutoEnrichmentsAccordion enrichments={gapData.auto_enrichments} />
      )}
    </div>
  );
}

// ─── Auto-enrichments collapsible ──────────────────────────────
function AutoEnrichmentsAccordion({ enrichments }: { enrichments: string[] }) {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <button
        onClick={() => setOpen((p) => !p)}
        className="w-full flex items-center justify-between px-3 py-2 rounded-lg transition-colors hover:bg-[var(--surface-raised)]"
        style={{ backgroundColor: 'var(--teal-soft)', border: '1px solid rgba(45,212,191,0.20)' }}
      >
        <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--teal)', letterSpacing: '0.5px', textTransform: 'uppercase' }}>
          Auto-Enrichments ({enrichments.length})
        </span>
        <m.span
          animate={{ rotate: open ? 180 : 0 }}
          transition={{ duration: 0.18 }}
          style={{ fontSize: '9px', color: 'var(--teal)' }}
        >
          ▾
        </m.span>
      </button>
      <AnimatePresence>
        {open && (
          <m.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            style={{ overflow: 'hidden' }}
          >
            <div className="pt-2 space-y-1">
              {enrichments.map((e, i) => (
                <div key={i} className="flex gap-2" style={{ fontSize: '11px', color: 'var(--teal)' }}>
                  <span style={{ flexShrink: 0 }}>⟳</span>
                  {e}
                </div>
              ))}
            </div>
          </m.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ─── Main InterviewPhase ───────────────────────────────────────
export function InterviewPhase() {
  const gapData = useWorkflowStore((state) => state.gapData);
  const answers = useWorkflowStore((state) => state.answers);
  const setAnswer = useWorkflowStore((state) => state.setAnswer);

  if (!gapData) return null;

  return (
    <m.div
      className="h-full overflow-hidden flex"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.25 }}
    >
      {/* Left zone — coverage dashboard */}
      <div
        className="shrink-0 overflow-y-auto p-4"
        style={{
          width: 280,
          borderRight: '1px solid var(--border)',
          backgroundColor: 'var(--surface)',
        }}
      >
        <CoverageDashboard />
      </div>

      {/* Right zone — questions */}
      <div className="flex-1 overflow-y-auto p-4">
        {gapData.questions.length > 0 ? (
          <>
            <div
              style={{
                fontSize: '10px',
                fontWeight: 700,
                color: 'var(--text-tertiary)',
                letterSpacing: '0.8px',
                textTransform: 'uppercase',
                marginBottom: 12,
              }}
            >
              Gap-Filling Questions ({gapData.questions.length}) — answer to improve coverage
            </div>
            <div className="space-y-3">
              {gapData.questions.map((question) => (
                <QuestionCard
                  key={question.id}
                  question={question}
                  answer={answers[question.question] || ''}
                  onAnswerChange={(answer) => setAnswer(question.question, answer)}
                />
              ))}
            </div>
          </>
        ) : (
          <m.div
            className="h-full flex items-center justify-center"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <div
              className="p-6 rounded-xl text-center"
              style={{ backgroundColor: 'var(--success-soft)', border: '1px solid rgba(61,214,140,0.25)' }}
            >
              <div style={{ fontSize: 36, marginBottom: 12 }}>✓</div>
              <div style={{ fontSize: 'var(--text-md)', fontWeight: 700, color: 'var(--success)' }}>
                Well-formed prompt!
              </div>
              <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', marginTop: 6 }}>
                No critical gaps detected. Click{' '}
                <strong style={{ color: 'var(--teal)' }}>Optimise</strong>{' '}
                below to generate the 3 production-grade variants.
              </p>
            </div>
          </m.div>
        )}
      </div>
    </m.div>
  );
}
