/**
 * QuickActions Component
 * 
 * Chips for quick chat actions.
 */

import { m } from 'framer-motion';
import { QUICK_ACTIONS } from '@/constants';
import { useChatSession } from '@/hooks';

/**
 * Quick action chips for common refinement requests.
 */
export function QuickActions() {
  const { sendQuickAction } = useChatSession();

  return (
    <div 
      className="px-3 py-2 border-t"
      style={{ borderColor: 'var(--border)' }}
    >
      <div className="text-[9px] font-bold uppercase tracking-[0.6px] text-[var(--text-tertiary)] mb-2">
        Quick Actions
      </div>
      <div className="flex flex-wrap gap-1">
        {QUICK_ACTIONS.map((action) => (
          <m.button
            key={action.label}
            onClick={() => sendQuickAction(action.label)}
            className="px-2 py-1 rounded-full text-[10.5px] whitespace-nowrap transition-all duration-150"
            style={{
              backgroundColor: 'var(--surface)',
              border: '1px solid var(--border)',
              color: 'var(--text-tertiary)',
            }}
            whileHover={{ 
              borderColor: 'var(--pink)',
              color: 'var(--pink)',
              scale: 1.02,
            }}
            whileTap={{ scale: 0.98 }}
          >
            {action.icon} {action.label}
          </m.button>
        ))}
      </div>
    </div>
  );
}
