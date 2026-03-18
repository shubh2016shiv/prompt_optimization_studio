/**
 * ModelSelector Component
 * 
 * Dropdown for selecting the target LLM model.
 */

import { Badge } from '@/components/ui';
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from '@/components/ui';
import { useConfigurationStore, useCurrentProvider, useIsReasoningModel } from '@/store';

/**
 * Model selection dropdown with reasoning model indicator.
 */
export function ModelSelector() {
  const modelId = useConfigurationStore((state) => state.modelId);
  const setModelId = useConfigurationStore((state) => state.setModelId);
  const provider = useCurrentProvider();
  const isReasoning = useIsReasoningModel();

  return (
    <div className="space-y-3">
      <Select value={modelId} onValueChange={setModelId}>
        <SelectTrigger>
          <SelectValue placeholder="Select a model" />
        </SelectTrigger>
        <SelectContent>
          {provider?.models.map((model) => (
            <SelectItem key={model.id} value={model.id}>
              {model.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* Reasoning model indicator */}
      {isReasoning && (
        <div 
          className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg"
          style={{
            backgroundColor: 'var(--warning-soft)',
            border: '1px solid var(--warning)30',
          }}
        >
          <span>⚡</span>
          <span className="text-[11.5px] font-semibold" style={{ color: 'var(--warning)' }}>
            Reasoning model — CoT auto-suppressed
          </span>
        </div>
      )}
    </div>
  );
}
