/**
 * VariantCard Component
 * 
 * A card displaying an optimized prompt variant with tabs for different views.
 */

import { useState } from 'react';
import { m } from 'framer-motion';
import { Button, Badge } from '@/components/ui';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui';
import { CopyButton } from '@/components/feedback';
import type { PromptVariant } from '@/types';

interface VariantCardProps {
  /** The variant data */
  variant: PromptVariant;
  /** Variant index (0, 1, 2) */
  index: number;
  /** Callback when refine button is clicked */
  onRefine: (variant: PromptVariant) => void;
}

const VARIANT_COLORS = [
  { color: 'var(--accent)', soft: 'var(--accent-soft)' },
  { color: 'var(--success)', soft: 'var(--success-soft)' },
  { color: 'var(--purple)', soft: 'var(--purple-soft)' },
];

/**
 * Mini TCRTE score bar display.
 */
function TCRTEMiniScores({ scores }: { scores: PromptVariant['tcrte_scores'] }) {
  const dimensions = [
    { key: 'task', label: 'T', color: 'var(--accent)' },
    { key: 'context', label: 'C', color: 'var(--cyan)' },
    { key: 'role', label: 'R', color: 'var(--purple)' },
    { key: 'tone', label: 'T', color: 'var(--pink)' },
    { key: 'execution', label: 'E', color: 'var(--orange)' },
  ] as const;

  return (
    <div className="flex gap-1.5 flex-wrap mt-2">
      {dimensions.map((dim) => {
        const score = scores[dim.key];
        const color = score >= 70 ? 'var(--success)' : score >= 40 ? 'var(--warning)' : 'var(--danger)';

        return (
          <div key={dim.key} className="flex flex-col items-center gap-1 min-w-[44px]">
            <div 
              className="w-11 h-1 rounded-full overflow-hidden"
              style={{ backgroundColor: 'var(--border)' }}
            >
              <div 
                className="h-full rounded-full transition-all duration-500"
                style={{ width: `${score}%`, backgroundColor: color }}
              />
            </div>
            <span 
              className="text-[9.5px] font-bold"
              style={{ color }}
            >
              {dim.label}{score}
            </span>
          </div>
        );
      })}
    </div>
  );
}

/**
 * Card for a single optimized variant.
 */
export function VariantCard({ variant, index, onRefine }: VariantCardProps) {
  const [activeTab, setActiveTab] = useState('system');
  const colors = VARIANT_COLORS[index] || VARIANT_COLORS[0]!;

  const tabs = [
    { id: 'system', label: 'System' },
    { id: 'user', label: 'User' },
    { id: 'guards', label: 'Guards' },
    { id: 'meta', label: 'Meta' },
    ...(variant.prefill_suggestion ? [{ id: 'prefill', label: 'Prefill' }] : []),
  ];

  return (
    <m.div
      className="rounded-xl overflow-hidden mb-4"
      style={{
        backgroundColor: 'var(--surface)',
        border: '1px solid var(--border)',
      }}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.1 }}
    >
      {/* Header */}
      <div 
        className="px-4 py-2.5 flex items-center justify-between"
        style={{
          background: `linear-gradient(90deg, ${colors.soft} 0%, transparent 100%)`,
          borderBottom: '1px solid var(--border)',
        }}
      >
        <div className="flex items-center gap-2">
          <Badge
            style={{
              backgroundColor: colors.soft,
              color: colors.color,
              borderColor: `${colors.color}35`,
            }}
          >
            V{variant.id}
          </Badge>
          <span className="text-[13px] font-bold text-[var(--text-primary)]">
            {variant.name}
          </span>
          <span className="text-[10.5px] font-mono text-[var(--text-tertiary)]">
            ~{variant.token_estimate}t
          </span>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onRefine(variant)}
          className="text-[10.5px] font-bold"
          style={{ color: 'var(--pink)' }}
        >
          ✦ Refine
        </Button>
      </div>

      {/* Content */}
      <div className="px-4 py-3">
        {/* Strategy */}
        <p className="text-[11.5px] text-[var(--text-secondary)] italic mb-2">
          {variant.strategy}
        </p>

        {/* TCRTE mini scores */}
        <TCRTEMiniScores scores={variant.tcrte_scores} />

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="mt-3">
          <TabsList className="w-full">
            {tabs.map((tab) => (
              <TabsTrigger key={tab.id} value={tab.id}>
                {tab.label}
              </TabsTrigger>
            ))}
          </TabsList>

          <TabsContent value="system" className="pb-2">
            <div className="flex justify-end mb-1">
              <CopyButton text={variant.system_prompt} />
            </div>
            <pre 
              className="p-3 rounded-lg overflow-x-auto text-[11px] font-mono leading-relaxed whitespace-pre-wrap break-words"
              style={{
                backgroundColor: 'var(--background)',
                border: '1px solid var(--border)',
                color: 'var(--cyan)',
              }}
            >
              {variant.system_prompt}
            </pre>
          </TabsContent>

          <TabsContent value="user" className="pb-2">
            <div className="flex justify-end mb-1">
              <CopyButton text={variant.user_prompt} />
            </div>
            <pre 
              className="p-3 rounded-lg overflow-x-auto text-[11px] font-mono leading-relaxed whitespace-pre-wrap break-words"
              style={{
                backgroundColor: 'var(--background)',
                border: '1px solid var(--border)',
                color: 'var(--warning)',
              }}
            >
              {variant.user_prompt}
            </pre>
          </TabsContent>

          <TabsContent value="guards" className="pb-2 space-y-3">
            {/* Overshoot guards */}
            <div>
              <div className="text-[9.5px] font-bold uppercase tracking-[0.8px] text-[var(--danger)] mb-2">
                ⟲ Anti-Overshoot
              </div>
              {variant.overshoot_guards.map((guard, i) => (
                <div key={i} className="flex gap-2 text-[11.5px] text-[var(--text-secondary)] mb-1 leading-relaxed">
                  <span className="text-[var(--danger)] shrink-0">▸</span>
                  {guard}
                </div>
              ))}
            </div>
            {/* Undershoot guards */}
            <div>
              <div className="text-[9.5px] font-bold uppercase tracking-[0.8px] text-[var(--success)] mb-2">
                ⟳ Anti-Undershoot
              </div>
              {variant.undershoot_guards.map((guard, i) => (
                <div key={i} className="flex gap-2 text-[11.5px] text-[var(--text-secondary)] mb-1 leading-relaxed">
                  <span className="text-[var(--success)] shrink-0">▸</span>
                  {guard}
                </div>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="meta" className="pb-2 space-y-3">
            {/* Strengths */}
            <div>
              <div className="text-[9.5px] font-bold uppercase tracking-[0.8px] text-[var(--accent)] mb-2">
                Strengths
              </div>
              {variant.strengths.map((strength, i) => (
                <div key={i} className="flex gap-2 text-[11.5px] text-[var(--text-secondary)] mb-1 leading-relaxed">
                  <span className="text-[var(--accent)]">✦</span>
                  {strength}
                </div>
              ))}
            </div>
            {/* Best for */}
            <div 
              className="p-2 rounded-lg"
              style={{ backgroundColor: 'var(--background)' }}
            >
              <span className="text-[9.5px] font-bold uppercase tracking-[0.5px] text-[var(--purple)]">
                Best For:{' '}
              </span>
              <span className="text-[11.5px] text-[var(--text-secondary)]">
                {variant.best_for}
              </span>
            </div>
          </TabsContent>

          {variant.prefill_suggestion && (
            <TabsContent value="prefill" className="pb-2">
              <div className="text-[9.5px] font-bold uppercase tracking-[0.8px] text-[var(--teal)] mb-2">
                Claude Prefill — paste as start of assistant turn
              </div>
              <div 
                className="relative p-3 rounded-lg"
                style={{
                  backgroundColor: 'var(--background)',
                  border: '1px solid var(--teal)40',
                }}
              >
                <pre className="text-[11px] font-mono text-[var(--teal)] whitespace-pre-wrap break-words">
                  {variant.prefill_suggestion}
                </pre>
                <div className="absolute top-2 right-2">
                  <CopyButton text={variant.prefill_suggestion} />
                </div>
              </div>
              <p className="text-[10.5px] text-[var(--text-tertiary)] mt-2">
                Prefilling locks the assistant's output format by providing the first tokens. Bypasses conversational preamble.
              </p>
            </TabsContent>
          )}
        </Tabs>
      </div>
    </m.div>
  );
}
