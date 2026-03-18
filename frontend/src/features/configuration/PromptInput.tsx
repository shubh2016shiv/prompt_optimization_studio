/**
 * PromptInput Component
 * 
 * The main textarea for entering the raw prompt to optimize.
 */

import { Textarea } from '@/components/ui';
import { FieldLabel } from '@/components/layout';
import { useConfigurationStore, useWorkflowStore } from '@/store';

/**
 * Raw prompt input textarea.
 * 
 * Resets the workflow when the prompt is edited (to invalidate stale gap data).
 */
export function PromptInput() {
  const rawPrompt = useConfigurationStore((state) => state.rawPrompt);
  const setRawPrompt = useConfigurationStore((state) => state.setRawPrompt);
  const phase = useWorkflowStore((state) => state.phase);
  const reset = useWorkflowStore((state) => state.reset);

  const handleChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = event.target.value;
    setRawPrompt(newValue);
    
    // Reset workflow if we're past the idle phase and the prompt changes
    if (phase !== 'idle') {
      reset();
    }
  };

  return (
    <div>
      <FieldLabel>Raw Prompt</FieldLabel>
      <Textarea
        value={rawPrompt}
        onChange={handleChange}
        placeholder="e.g. Analyze these financial documents and identify all risk factors…"
        rows={7}
        className="resize-y leading-relaxed text-[11.5px]"
      />
    </div>
  );
}
