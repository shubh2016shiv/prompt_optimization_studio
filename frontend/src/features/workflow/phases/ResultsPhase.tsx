/**
 * ResultsPhase Component
 *
 * Tabbed variant viewer (Conservative | Structured | Advanced).
 * Each tab shows per-variant TCRTE rings, full prompts with copy, and refine CTA.
 * Optimization Report is in a collapsible banner above the tabs.
 */

import { useState } from 'react';
import { m, AnimatePresence } from 'framer-motion';
import { Badge } from '@/components/ui';
import { ProgressRing } from '@/components/ui';
import { CopyButton } from '@/components/feedback';
import { useWorkflowStore, useChatStore } from '@/store';
import type { PromptVariant } from '@/types';

// ─── Variant tab config ────────────────────────────────────────
const VARIANT_STYLES = [
  { icon: '🔵', color: 'var(--accent)',  soft: 'var(--accent-soft)',  label: 'Conservative' },
  { icon: '⬡',  color: 'var(--teal)',   soft: 'var(--teal-soft)',   label: 'Structured'   },
  { icon: '🔮', color: 'var(--purple)', soft: 'var(--purple-soft)', label: 'Advanced'     },
];

// ─── Mini TCRTE rings for per-variant header ───────────────────
const TCRTE_KEYS = [
  { key: 'task',      label: 'T', color: 'var(--accent)'  },
  { key: 'context',   label: 'C', color: 'var(--cyan)'    },
  { key: 'role',      label: 'R', color: 'var(--purple)'  },
  { key: 'tone',      label: 'T', color: 'var(--pink)'    },
  { key: 'execution', label: 'E', color: 'var(--orange)'  },
] as const;

function scoreColor(score: number) {
  if (score >= 70) return 'var(--success)';
  if (score >= 35) return 'var(--warning)';
  return 'var(--danger)';
}

// ─── Prompt code block ─────────────────────────────────────────
function PromptBlock({ text, accent }: { text: string; accent: string }) {
  return (
    <div className="relative">
      <div className="absolute top-2 right-2 z-10">
        <CopyButton text={text} />
      </div>
      <pre
        className="p-3 rounded-xl overflow-x-auto leading-relaxed whitespace-pre-wrap break-words"
        style={{
          fontSize: '11px',
          fontFamily: 'var(--font-mono)',
          backgroundColor: '#131613',
          border: `1px solid var(--border-subtle)`,
          color: accent,
          maxHeight: 280,
          overflowY: 'auto',
        }}
      >
        {text}
      </pre>
    </div>
  );
}

// ─── Variant content panel ─────────────────────────────────────
function VariantContent({
  variant,
  style,
  onRefine,
}: {
  variant: PromptVariant;
  style: typeof VARIANT_STYLES[number] | undefined;
  onRefine: () => void;
}) {
  const [activeTab, setActiveTab] = useState<string>('system');

  const TABS = [
    { id: 'system', label: 'System' },
    { id: 'user',   label: 'User'   },
    { id: 'guards', label: 'Guards' },
    { id: 'meta',   label: 'Meta'   },
    ...(variant.prefill_suggestion ? [{ id: 'prefill', label: 'Prefill' }] : []),
  ];

  const _style = style || VARIANT_STYLES[0]!;

  return (
    <div className="space-y-4">
      {/* TCRTE score rings */}
      <div
        className="flex items-center gap-3 p-3 rounded-xl"
        style={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)' }}
      >
        <div className="flex-1">
          <div style={{ fontSize: '9.5px', fontWeight: 700, color: 'var(--text-tertiary)', letterSpacing: '0.8px', textTransform: 'uppercase', marginBottom: 8 }}>
            TCRTE Coverage Scores
          </div>
          <div className="flex gap-3">
            {TCRTE_KEYS.map((dim, i) => {
              const score = variant.tcrte_scores[dim.key];
              return (
                <ProgressRing
                  key={dim.key}
                  score={score}
                  color={scoreColor(score)}
                  size={40}
                  strokeWidth={3}
                  sublabel={dim.label}
                  delay={i * 0.06}
                />
              );
            })}
          </div>
        </div>

        {/* Token estimate + strategy */}
        <div className="text-right shrink-0">
          <div style={{ fontSize: '9px', color: 'var(--text-tertiary)', marginBottom: 4 }}>~{variant.token_estimate}t</div>
          <button
            onClick={onRefine}
            className="px-2.5 py-1.5 rounded-lg font-bold transition-colors hover:opacity-80"
            style={{
              fontSize: '10.5px',
              backgroundColor: 'rgba(240,98,146,0.12)',
              color: 'var(--pink)',
              border: '1px solid rgba(240,98,146,0.25)',
            }}
          >
            ✦ Refine in Chat
          </button>
        </div>
      </div>

      {/* Strategy */}
      <p style={{ fontSize: '11.5px', color: 'var(--text-secondary)', fontStyle: 'italic' }}>
        {variant.strategy}
      </p>

      {/* Sub-tabs */}
      <div>
        {/* Tab list */}
        <div
          className="flex gap-0.5 p-1 rounded-lg mb-3"
          style={{ backgroundColor: 'var(--surface)' }}
        >
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className="flex-1 py-1.5 rounded-md font-semibold transition-colors"
              style={{
                fontSize: '11px',
                backgroundColor: activeTab === tab.id ? _style.soft : 'transparent',
                color: activeTab === tab.id ? _style.color : 'var(--text-secondary)',
                border: activeTab === tab.id ? `1px solid ${_style.color}28` : '1px solid transparent',
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <AnimatePresence mode="wait">
          <m.div
            key={activeTab}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.15 }}
          >
            {activeTab === 'system' && (
              <PromptBlock text={variant.system_prompt} accent="var(--cyan)" />
            )}
            {activeTab === 'user' && (
              <PromptBlock text={variant.user_prompt} accent="var(--warning)" />
            )}
            {activeTab === 'guards' && (
              <div className="space-y-3">
                <div>
                  <div style={{ fontSize: '9.5px', fontWeight: 700, color: 'var(--danger)', letterSpacing: '0.8px', textTransform: 'uppercase', marginBottom: 6 }}>⟲ Anti-Overshoot</div>
                  {variant.overshoot_guards.map((g, i) => (
                    <div key={i} className="flex gap-2 mb-1" style={{ fontSize: '11.5px', color: 'var(--text-secondary)' }}>
                      <span style={{ color: 'var(--danger)', flexShrink: 0 }}>▸</span>{g}
                    </div>
                  ))}
                </div>
                <div>
                  <div style={{ fontSize: '9.5px', fontWeight: 700, color: 'var(--success)', letterSpacing: '0.8px', textTransform: 'uppercase', marginBottom: 6 }}>⟳ Anti-Undershoot</div>
                  {variant.undershoot_guards.map((g, i) => (
                    <div key={i} className="flex gap-2 mb-1" style={{ fontSize: '11.5px', color: 'var(--text-secondary)' }}>
                      <span style={{ color: 'var(--success)', flexShrink: 0 }}>▸</span>{g}
                    </div>
                  ))}
                </div>
              </div>
            )}
            {activeTab === 'meta' && (
              <div className="space-y-3">
                <div>
                  <div style={{ fontSize: '9.5px', fontWeight: 700, color: 'var(--accent)', letterSpacing: '0.8px', textTransform: 'uppercase', marginBottom: 6 }}>Strengths</div>
                  {variant.strengths.map((s, i) => (
                    <div key={i} className="flex gap-2 mb-1" style={{ fontSize: '11.5px', color: 'var(--text-secondary)' }}>
                      <span style={{ color: 'var(--accent)' }}>✦</span>{s}
                    </div>
                  ))}
                </div>
                <div className="p-2.5 rounded-lg" style={{ backgroundColor: 'var(--background)' }}>
                  <span style={{ fontSize: '9.5px', fontWeight: 700, color: 'var(--purple)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Best For: </span>
                  <span style={{ fontSize: '11.5px', color: 'var(--text-secondary)' }}>{variant.best_for}</span>
                </div>
              </div>
            )}
            {activeTab === 'prefill' && variant.prefill_suggestion && (
              <div>
                <div style={{ fontSize: '9.5px', fontWeight: 700, color: 'var(--teal)', letterSpacing: '0.8px', textTransform: 'uppercase', marginBottom: 8 }}>
                  Claude Prefill — paste as start of assistant turn
                </div>
                <PromptBlock text={variant.prefill_suggestion} accent="var(--teal)" />
                <p style={{ fontSize: '10.5px', color: 'var(--text-tertiary)', marginTop: 8 }}>
                  Prefilling locks the assistant's output format from the first token.
                </p>
              </div>
            )}
          </m.div>
        </AnimatePresence>
      </div>
    </div>
  );
}

// ─── Optimization report banner ────────────────────────────────
function OptimizationReport() {
  const [open, setOpen] = useState(false);
  const result = useWorkflowStore((state) => state.result)!;

  return (
    <div
      className="rounded-xl overflow-hidden"
      style={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)' }}
    >
      <button
        onClick={() => setOpen((p) => !p)}
        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-[var(--surface-raised)] transition-colors"
      >
        <span style={{ fontSize: '9.5px', fontWeight: 700, color: 'var(--text-tertiary)', letterSpacing: '1px', textTransform: 'uppercase' }}>
          📊 Optimisation Report
        </span>
        {result.analysis.coverage_delta && (
          <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--success)' }}>
            ↑ {result.analysis.coverage_delta}
          </span>
        )}
        <div className="flex gap-1 ml-auto">
          {result.techniques_applied.map((t) => (
            <Badge key={t} variant="orange" size="sm">{t}</Badge>
          ))}
        </div>
        <m.span animate={{ rotate: open ? 180 : 0 }} transition={{ duration: 0.18 }} style={{ fontSize: '10px', color: 'var(--text-tertiary)' }}>
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
            <div className="px-4 pb-4 grid grid-cols-2 gap-4">
              <div>
                <div style={{ fontSize: '9.5px', fontWeight: 700, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 8 }}>Issues Fixed</div>
                {result.analysis.detected_issues.map((issue, i) => (
                  <div key={i} className="flex gap-2 mb-1" style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                    <span style={{ color: 'var(--warning)' }}>⚠</span>{issue}
                  </div>
                ))}
              </div>
              <div>
                <div style={{ fontSize: '9.5px', fontWeight: 700, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 8 }}>Framework Applied</div>
                <div style={{ fontSize: '11px', color: 'var(--accent)' }}>{result.analysis.framework_applied}</div>
              </div>
            </div>
          </m.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ─── Main ResultsPhase ─────────────────────────────────────────
export function ResultsPhase() {
  const result = useWorkflowStore((state) => state.result);
  const setInputText = useChatStore((state) => state.setInputText);
  const setExpanded = useChatStore((state) => state.setExpanded);
  const [activeVariant, setActiveVariant] = useState(0);

  if (!result) return null;

  const handleRefine = (variant: PromptVariant) => {
    const message = `Refine Variant ${variant.id} "${variant.name}" (strategy: "${variant.strategy}"). Show the most impactful improvements with full revised SYSTEM + USER prompts.`;
    setInputText(message);
    setExpanded(true);
  };

  const currentVariant = result.variants[activeVariant];
  const currentStyle = VARIANT_STYLES[activeVariant] || VARIANT_STYLES[0]!;

  return (
    <m.div
      className="h-full overflow-y-auto"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.25 }}
    >
      <div className="p-4 space-y-4">
        {/* Optimization report (collapsible) */}
        <OptimizationReport />

        {/* Top-level variant tabs */}
        <div>
          <div
            style={{
              fontSize: '9.5px',
              fontWeight: 700,
              color: 'var(--text-tertiary)',
              letterSpacing: '0.8px',
              textTransform: 'uppercase',
              marginBottom: 10,
            }}
          >
            3 Optimised Variants · select to view
          </div>

          {/* Variant selector tabs */}
          <div className="flex gap-2 mb-4">
            {result.variants.map((variant, index) => {
              const style = VARIANT_STYLES[index] || VARIANT_STYLES[0]!;
              const isActive = activeVariant === index;
              return (
                <button
                  key={variant.id}
                  onClick={() => setActiveVariant(index)}
                  className="flex-1 flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl font-semibold transition-all"
                  style={{
                    fontSize: '12px',
                    backgroundColor: isActive ? style.soft : 'var(--surface)',
                    border: `1.5px solid ${isActive ? style.color + '60' : 'var(--border)'}`,
                    color: isActive ? style.color : 'var(--text-secondary)',
                    boxShadow: isActive ? `0 0 12px ${style.color}18` : 'none',
                  }}
                >
                  <span>{style.icon}</span>
                  <span>{variant.name}</span>
                </button>
              );
            })}
          </div>

          {/* Active variant content */}
          <AnimatePresence mode="wait">
            <m.div
              key={activeVariant}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.2 }}
            >
              {currentVariant && (
                <VariantContent
                  variant={currentVariant}
                  style={currentStyle}
                  onRefine={() => handleRefine(currentVariant)}
                />
              )}
            </m.div>
          </AnimatePresence>
        </div>
      </div>
    </m.div>
  );
}
