/**
 * InterviewPhase Component
 * 
 * The gap interview phase showing coverage scores and questions.
 */

import { m } from 'framer-motion';
import { Badge } from '@/components/ui';
import { useWorkflowStore } from '@/store';
import { CoverageMeter, QuestionCard } from '../components';

const COMPLEXITY_STYLES = {
  simple: { color: 'var(--success)', bg: 'var(--success-soft)' },
  medium: { color: 'var(--warning)', bg: 'var(--warning-soft)' },
  complex: { color: 'var(--danger)', bg: 'var(--danger-soft)' },
} as const;

/**
 * Interview phase with coverage meter and question cards.
 */
export function InterviewPhase() {
  const gapData = useWorkflowStore((state) => state.gapData);
  const answers = useWorkflowStore((state) => state.answers);
  const setAnswer = useWorkflowStore((state) => state.setAnswer);

  if (!gapData) return null;

  const complexityStyle = COMPLEXITY_STYLES[gapData.complexity];

  return (
    <m.div
      className="h-full overflow-y-auto"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.25 }}
    >
      <div className="p-4 space-y-4">
        {/* Coverage meter */}
        <CoverageMeter 
          tcrte={gapData.tcrte} 
          overallScore={gapData.overall_score} 
        />

        {/* Complexity and techniques */}
        <div className="flex flex-wrap gap-2">
          {/* Complexity badge */}
          <div 
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg"
            style={{
              backgroundColor: complexityStyle.bg,
              border: `1px solid ${complexityStyle.color}30`,
            }}
          >
            <span 
              className="text-[11px] font-bold uppercase tracking-[0.5px]"
              style={{ color: complexityStyle.color }}
            >
              Complexity: {gapData.complexity}
            </span>
            <span className="text-[10.5px] text-[var(--text-tertiary)]">
              {gapData.complexity_reason}
            </span>
          </div>

          {/* Recommended techniques */}
          {gapData.recommended_techniques.map((technique) => (
            <Badge key={technique} variant="cyan" size="md">
              {technique}
            </Badge>
          ))}
        </div>

        {/* Auto-enrichments */}
        {gapData.auto_enrichments.length > 0 && (
          <div 
            className="p-3 rounded-lg"
            style={{
              backgroundColor: 'var(--teal-soft)',
              border: '1px solid var(--teal)30',
            }}
          >
            <div className="text-[9.5px] font-bold uppercase tracking-[0.8px] text-[var(--teal)] mb-2">
              Auto-Enrichments Applied
            </div>
            {gapData.auto_enrichments.map((enrichment, i) => (
              <div key={i} className="flex gap-2 text-[11.5px] text-[var(--teal)] mb-1">
                <span>⟳</span>
                {enrichment}
              </div>
            ))}
          </div>
        )}

        {/* Questions */}
        {gapData.questions.length > 0 ? (
          <div>
            <div className="text-[10px] font-bold uppercase tracking-[0.8px] text-[var(--text-tertiary)] mb-3">
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
          </div>
        ) : (
          <div 
            className="p-4 rounded-lg"
            style={{
              backgroundColor: 'var(--success-soft)',
              border: '1px solid var(--success)30',
            }}
          >
            <div className="text-[13px] font-semibold text-[var(--success)]">
              ✓ Your prompt is well-formed! No critical gaps detected.
            </div>
            <p className="text-[11.5px] text-[var(--text-secondary)] mt-1">
              Click "Optimise with Context" to generate the 3 production-grade variants.
            </p>
          </div>
        )}
      </div>
    </m.div>
  );
}
