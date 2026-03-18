/**
 * VariableInput Component
 * 
 * Input for declaring template variables used in the prompt.
 */

import { Textarea } from '@/components/ui';
import { FieldLabel } from '@/components/layout';
import { useConfigurationStore } from '@/store';

/**
 * Input variables textarea for declaring prompt template variables.
 */
export function VariableInput() {
  const inputVariables = useConfigurationStore((state) => state.inputVariables);
  const setInputVariables = useConfigurationStore((state) => state.setInputVariables);

  return (
    <div>
      <FieldLabel hint="optional">Input Variables</FieldLabel>
      <Textarea
        value={inputVariables}
        onChange={(e) => setInputVariables(e.target.value)}
        placeholder={"{{documents}} – array of PDFs\n{{threshold}} – risk %"}
        rows={3}
        className="resize-y text-[11px]"
      />
    </div>
  );
}
