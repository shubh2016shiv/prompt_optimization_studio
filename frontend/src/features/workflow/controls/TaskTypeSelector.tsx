/**
 * TaskTypeSelector Component
 * 
 * Chips for selecting the task type (planning, reasoning, coding, etc.).
 */

import { m } from 'framer-motion';
import { cn } from '@/lib/utils';
import { useWorkflowStore } from '@/store';
import { TASK_TYPES } from '@/constants';
import { PanelHeader } from '@/components/layout';
import type { TaskTypeId } from '@/types';

/**
 * Task type selection chips.
 */
export function TaskTypeSelector() {
  const selectedTaskType = useWorkflowStore((state) => state.taskType);
  const setTaskType = useWorkflowStore((state) => state.setTaskType);

  return (
    <div>
      <PanelHeader icon="⚙" title="Task Type" />
      <div className="flex flex-wrap gap-1.5">
        {TASK_TYPES.map((taskType) => {
          const isSelected = selectedTaskType === taskType.id;

          return (
            <m.button
              key={taskType.id}
              onClick={() => setTaskType(taskType.id as TaskTypeId)}
              className={cn(
                `px-2.5 py-1.5 rounded-md
                 text-[11.5px] font-semibold
                 border transition-colors duration-150
                 focus:outline-none focus:ring-2 focus:ring-[var(--accent)]`,
                isSelected
                  ? 'border-[1.5px] border-[var(--cyan)] bg-[var(--cyan-soft)] text-[var(--cyan)]'
                  : 'border-[var(--border)] bg-transparent text-[var(--text-secondary)] hover:bg-[var(--surface-raised)]'
              )}
              whileTap={{ scale: 0.97 }}
              whileHover={{ scale: 1.02 }}
              transition={{ type: 'spring', stiffness: 400, damping: 25 }}
            >
              <span className="mr-1">{taskType.icon}</span>
              {taskType.label}
            </m.button>
          );
        })}
      </div>
    </div>
  );
}
