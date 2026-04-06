/**
 * TaskTypeSelector Component
 *
 * Task type chips with stronger selected state and touch targets.
 */

import { m } from 'framer-motion';
import { cn } from '@/lib/utils';
import { useWorkflowStore } from '@/store';
import { TASK_TYPES } from '@/constants';
import { PanelHeader } from '@/components/layout';
import type { TaskTypeId } from '@/types';

interface TaskTypeSelectorProps {
  compact?: boolean;
}

export function TaskTypeSelector({ compact = false }: TaskTypeSelectorProps) {
  const selectedTaskType = useWorkflowStore((state) => state.taskType);
  const setTaskType = useWorkflowStore((state) => state.setTaskType);

  return (
    <div className="space-y-1.5 min-w-0">
      {!compact && <PanelHeader icon="T" title="Task Type" />}

      <div className="flex flex-wrap gap-1.5 min-w-0">
        {TASK_TYPES.map((taskType) => {
          const isSelected = selectedTaskType === taskType.id;

          return (
            <m.button
              key={taskType.id}
              onClick={() => setTaskType(taskType.id as TaskTypeId)}
              className={cn(
                `px-2.5 py-1.5 min-h-[26px] rounded-md inline-flex items-center max-w-full
                 text-[11.5px] border transition-colors duration-150
                 focus:outline-none focus:ring-2 focus:ring-[var(--teal)] break-words`,
                isSelected
                  ? 'border-[var(--teal)] bg-[rgba(45,212,191,0.16)] text-[var(--teal)] font-semibold'
                  : 'border-[var(--border-subtle)] bg-transparent text-[var(--text-secondary)] font-medium hover:bg-[var(--surface-3)]'
              )}
              whileTap={{ scale: 0.97 }}
              whileHover={{ scale: 1.02 }}
              transition={{ type: 'spring', stiffness: 400, damping: 25 }}
            >
              <span className="mr-1">{taskType.icon}</span>
              <span>{taskType.label}</span>
              {isSelected && (
                <span
                  className="ml-1 rounded-full px-1"
                  style={{
                    fontSize: '9px',
                    lineHeight: 1.2,
                    color: 'var(--teal)',
                    backgroundColor: 'rgba(45, 212, 191, 0.2)',
                    border: '1px solid rgba(45, 212, 191, 0.32)',
                  }}
                >
                  ?
                </span>
              )}
            </m.button>
          );
        })}
      </div>

      <p style={{ fontSize: '10px', color: 'var(--text-tertiary)' }}>
        Select one primary task category.
      </p>
    </div>
  );
}
