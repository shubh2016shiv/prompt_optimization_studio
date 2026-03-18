/**
 * ResultsPhase Component
 * 
 * The results phase showing the optimization report and variant cards.
 */

import { m } from 'framer-motion';
import { Badge } from '@/components/ui';
import { useWorkflowStore, useChatStore } from '@/store';
import { VariantCard } from '../components';
import type { PromptVariant } from '@/types';

/**
 * Results phase with optimization report and variant cards.
 */
export function ResultsPhase() {
  const result = useWorkflowStore((state) => state.result);
  const setInputText = useChatStore((state) => state.setInputText);
  const setExpanded = useChatStore((state) => state.setExpanded);

  if (!result) return null;

  const handleRefine = (variant: PromptVariant) => {
    const message = `Refine Variant ${variant.id} "${variant.name}" (strategy: "${variant.strategy}"). Show the most impactful improvements with full revised SYSTEM + USER prompts.`;
    setInputText(message);
    setExpanded(true);
  };

  return (
    <m.div
      className="h-full overflow-y-auto"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.25 }}
    >
      <div className="p-4 space-y-4">
        {/* Analysis banner */}
        <div 
          className="p-4 rounded-xl"
          style={{
            backgroundColor: 'var(--surface)',
            border: '1px solid var(--border)',
          }}
        >
          <div className="text-[9.5px] font-bold uppercase tracking-[1px] text-[var(--text-tertiary)] mb-3">
            📊 Optimisation Report
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* Issues fixed */}
            <div>
              <div className="text-[9.5px] font-bold uppercase tracking-[0.5px] text-[var(--text-tertiary)] mb-2">
                Issues Fixed
              </div>
              {result.analysis.detected_issues.map((issue, i) => (
                <div key={i} className="flex gap-2 text-[11px] text-[var(--text-secondary)] mb-1 leading-relaxed">
                  <span className="text-[var(--warning)]">⚠</span>
                  {issue}
                </div>
              ))}
            </div>

            {/* Result summary */}
            <div>
              <div className="text-[9.5px] font-bold uppercase tracking-[0.5px] text-[var(--text-tertiary)] mb-2">
                Result
              </div>
              {result.analysis.coverage_delta && (
                <div className="text-[11px] font-semibold text-[var(--success)] mb-1.5">
                  ↑ {result.analysis.coverage_delta}
                </div>
              )}
              <div className="text-[11px] text-[var(--accent)] mb-2 leading-relaxed">
                {result.analysis.framework_applied}
              </div>
              {result.techniques_applied.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {result.techniques_applied.map((technique) => (
                    <Badge key={technique} variant="orange" size="sm">
                      {technique}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Variant cards header */}
        <div className="text-[10px] font-bold uppercase tracking-[0.8px] text-[var(--text-tertiary)]">
          3 Optimised Variants · read-only · click ✦ Refine to discuss in chat →
        </div>

        {/* Variant cards */}
        {result.variants.map((variant, index) => (
          <VariantCard
            key={variant.id}
            variant={variant}
            index={index}
            onRefine={handleRefine}
          />
        ))}
      </div>
    </m.div>
  );
}
