/**
 * ModelSelector Component
 *
 * Dropdown for selecting the target LLM model.
 */

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui';
import { useConfigurationStore, useCurrentProvider, useIsReasoningModel } from '@/store';

export function ModelSelector() {
  const modelId = useConfigurationStore((state: any) => state.modelId);
  const setModelId = useConfigurationStore((state: any) => state.setModelId);
  const provider = useCurrentProvider();
  const isReasoning = useIsReasoningModel();

  return (
    <div className="space-y-3 min-w-0">
      <Select value={modelId} onValueChange={setModelId}>
        <SelectTrigger>
          <SelectValue placeholder="Select a model" />
        </SelectTrigger>
        <SelectContent>
          {provider?.models.map((model: any) => (
            <SelectItem key={model.id} value={model.id}>
              {model.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {isReasoning && (
        <div
          className="flex items-start gap-2 px-2.5 py-1.5 rounded-lg min-w-0"
          style={{
            backgroundColor: 'var(--warning-soft)',
            border: '1px solid var(--warning)30',
          }}
        >
          <span>!</span>
          <span className="text-[11.5px] font-semibold break-words" style={{ color: 'var(--warning)' }}>
            Reasoning model - CoT auto-suppressed
          </span>
        </div>
      )}
    </div>
  );
}
