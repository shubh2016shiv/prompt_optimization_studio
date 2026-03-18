/**
 * QuestionCard Component
 * 
 * A card for displaying and answering a gap interview question.
 */

import { m } from 'framer-motion';
import { Input } from '@/components/ui';
import { Badge } from '@/components/ui';
import { TCRTE_DIMENSIONS } from '@/constants';
import type { GapQuestion } from '@/types';

interface QuestionCardProps {
  /** The question data */
  question: GapQuestion;
  /** Current answer value */
  answer: string;
  /** Callback when answer changes */
  onAnswerChange: (answer: string) => void;
}

const IMPORTANCE_STYLES = {
  critical: { color: 'var(--danger)', bg: 'var(--danger-soft)' },
  recommended: { color: 'var(--warning)', bg: 'var(--warning-soft)' },
  optional: { color: 'var(--text-tertiary)', bg: 'var(--surface)' },
} as const;

/**
 * Card for a single gap interview question.
 */
export function QuestionCard({ question, answer, onAnswerChange }: QuestionCardProps) {
  const dimension = TCRTE_DIMENSIONS.find((d) => d.id === question.dimension);
  const importanceStyle = IMPORTANCE_STYLES[question.importance];

  return (
    <m.div
      className="p-4 rounded-xl"
      style={{
        backgroundColor: 'var(--surface)',
        border: '1px solid var(--border)',
      }}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      {/* Header badges */}
      <div className="flex items-center gap-2 mb-3">
        {/* Dimension badge */}
        <Badge
          className="text-[10px]"
          style={{
            backgroundColor: `${dimension?.color}20`,
            color: dimension?.color,
            borderColor: `${dimension?.color}30`,
          }}
        >
          {dimension?.label.toUpperCase()}
        </Badge>

        {/* Importance badge */}
        <Badge
          className="text-[10px] uppercase tracking-[0.4px]"
          style={{
            backgroundColor: importanceStyle.bg,
            color: importanceStyle.color,
            borderColor: `${importanceStyle.color}30`,
          }}
        >
          {question.importance}
        </Badge>

        {/* Question text */}
        <span className="text-[11.5px] font-semibold text-[var(--text-primary)] flex-1">
          {question.question}
        </span>
      </div>

      {/* Answer input */}
      <Input
        value={answer}
        onChange={(e) => onAnswerChange(e.target.value)}
        placeholder={question.placeholder}
        className="text-[12px]"
      />
    </m.div>
  );
}
