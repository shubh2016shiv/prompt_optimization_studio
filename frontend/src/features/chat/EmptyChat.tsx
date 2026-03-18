/**
 * EmptyChat Component
 * 
 * The empty state shown when no messages are in the chat.
 */

import { m } from 'framer-motion';
import { useWorkflowStore } from '@/store';
import { useChatSession } from '@/hooks';

const STARTER_QUESTIONS = [
  'What is TCRTE and when do I use it?',
  'Explain CoRe (Context Repetition)',
  'What\'s the RAL-Writer restate technique?',
  'When should I use Claude prefilling?',
];

/**
 * Empty chat state with starter questions.
 */
export function EmptyChat() {
  const phase = useWorkflowStore((state) => state.phase);
  const { sendMessage } = useChatSession();

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-4 text-center">
      {/* Icon */}
      <div className="text-3xl opacity-20 mb-3">✦</div>

      {/* Title */}
      <h3 className="text-[12.5px] font-semibold text-[var(--text-primary)] mb-2">
        Your prompt refinement coach
      </h3>

      {/* Description */}
      <p className="text-[11.5px] text-[var(--text-secondary)] leading-relaxed mb-4 max-w-[280px]">
        {phase === 'results' ? (
          'Chat context is loading…'
        ) : (
          <>
            Run the optimiser — the full output will be posted here automatically so you can refine conversationally.
            <br /><br />
            Or ask about prompt engineering techniques right now.
          </>
        )}
      </p>

      {/* Starter questions */}
      {phase !== 'results' && (
        <div className="flex flex-col gap-1.5 w-full">
          {STARTER_QUESTIONS.map((question) => (
            <m.button
              key={question}
              onClick={() => sendMessage(question)}
              className="w-full p-2 rounded-lg text-left text-[11px] leading-relaxed transition-colors"
              style={{
                backgroundColor: 'var(--surface)',
                border: '1px solid var(--border)',
                color: 'var(--text-secondary)',
              }}
              whileHover={{ 
                backgroundColor: 'var(--surface-raised)',
                borderColor: 'var(--border-elevated)',
              }}
              whileTap={{ scale: 0.99 }}
            >
              💬 {question}
            </m.button>
          ))}
        </div>
      )}
    </div>
  );
}
