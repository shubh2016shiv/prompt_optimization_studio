/**
 * ProviderSelector Component
 * 
 * Buttons for selecting the LLM provider (Anthropic, OpenAI, Google).
 */

import { m } from 'framer-motion';
import { cn } from '@/lib/utils';
import { useConfigurationStore } from '@/store';
import { PROVIDERS } from '@/constants';
import type { ProviderId } from '@/types';

/**
 * Provider selection chips.
 */
export function ProviderSelector() {
  const selectedProviderId = useConfigurationStore((state) => state.providerId);
  const setProvider = useConfigurationStore((state) => state.setProvider);

  const providerEntries = Object.entries(PROVIDERS) as [ProviderId, typeof PROVIDERS[ProviderId]][];

  return (
    <div className="flex flex-wrap gap-1.5">
      {providerEntries.map(([id, provider]) => {
        const isSelected = selectedProviderId === id;

        return (
          <m.button
            key={id}
            onClick={() => setProvider(id)}
            className={cn(
              `px-2.5 py-1.5 rounded-md
               text-[11.5px] font-semibold
               border transition-colors duration-150
               focus:outline-none focus:ring-2 focus:ring-[var(--accent)]`,
              isSelected
                ? 'border-[1.5px]'
                : 'border-[var(--border)] bg-transparent text-[var(--text-secondary)] hover:bg-[var(--surface-raised)]'
            )}
            style={isSelected ? {
              borderColor: provider.color,
              backgroundColor: provider.colorSoft,
              color: provider.color,
            } : undefined}
            whileTap={{ scale: 0.97 }}
            whileHover={{ scale: 1.02 }}
            transition={{ type: 'spring', stiffness: 400, damping: 25 }}
          >
            <span className="mr-1.5">{provider.icon}</span>
            {provider.label}
          </m.button>
        );
      })}
    </div>
  );
}
