/**
 * FrameworkSelector Component
 *
 * Chips for selecting the optimization framework.
 */

import { m } from 'framer-motion';
import { cn } from '@/lib/utils';
import { useWorkflowStore } from '@/store';
import { FRAMEWORKS } from '@/constants';
import { PanelHeader } from '@/components/layout';
import type { FrameworkId } from '@/types';

interface FrameworkSelectorProps {
  compact?: boolean;
}

export function FrameworkSelector({ compact = false }: FrameworkSelectorProps) {
  const selectedFramework = useWorkflowStore((state) => state.framework);
  const setFramework = useWorkflowStore((state) => state.setFramework);

  const selectedFrameworkInfo = FRAMEWORKS.find((framework) => framework.id === selectedFramework);

  return (
    <div className="min-w-0">
      {!compact && <PanelHeader icon="F" title="Optimisation Framework" />}

      <div className="flex flex-wrap gap-1.5 mb-2 min-w-0">
        {FRAMEWORKS.map((framework) => {
          const isSelected = selectedFramework === framework.id;

          return (
            <m.button
              key={framework.id}
              onClick={() => setFramework(framework.id as FrameworkId)}
              className={cn(
                `px-2.5 py-1.5 rounded-md max-w-full
                 text-[11.5px] font-semibold leading-tight
                 border transition-colors duration-150
                 focus:outline-none focus:ring-2 focus:ring-[var(--accent)]
                 break-words`,
                isSelected
                  ? 'border-[1.5px] border-[var(--purple)] bg-[var(--purple-soft)] text-[var(--purple)]'
                  : 'border-[var(--border)] bg-transparent text-[var(--text-secondary)] hover:bg-[var(--surface-raised)]'
              )}
              whileTap={{ scale: 0.97 }}
              whileHover={{ scale: 1.02 }}
              transition={{ type: 'spring', stiffness: 400, damping: 25 }}
            >
              <span className="mr-1">{framework.icon}</span>
              {framework.label}
            </m.button>
          );
        })}
      </div>

      {selectedFramework !== 'auto' && selectedFrameworkInfo && (
        <p className="text-[var(--text-secondary)] pl-0.5 break-words" style={{ fontSize: 'var(--text-sm)' }}>
          {'->'} {selectedFrameworkInfo.description}
        </p>
      )}
    </div>
  );
}
