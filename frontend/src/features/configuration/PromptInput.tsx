/**
 * PromptInput Component
 *
 * Main prompt editor with onboarding examples.
 */

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Textarea } from '@/components/ui';
import { useConfigurationStore } from '@/store';
import { useWorkflowStore } from '@/store';
import type { PromptExample } from '@/types';

const EXAMPLES: PromptExample[] = [
  {
    id: 'financial-rag',
    label: 'Financial analysis RAG',
    taskType: 'analysis',
    prompt: [
      'You are a financial risk analyst.',
      'Use only provided documents to identify material risks and confidence levels.',
      'Return sections: Risk Summary, Evidence Table, Missing Data, and Recommendations.',
      'If evidence is missing, explicitly say insufficient evidence.',
    ].join('\n'),
    variables: [
      { name: 'documents', description: 'Array of filings and quarterly reports' },
      { name: 'risk_threshold', description: 'Minimum severity for reporting a risk' },
    ],
  },
  {
    id: 'coding-agent',
    label: 'Coding agent system prompt',
    taskType: 'coding',
    prompt: [
      'You are a senior software engineer helping implement feature requests.',
      'Always inspect existing code before proposing changes.',
      'Prioritize minimal, safe diffs and explain tradeoffs.',
      'Return: Plan, Patch Summary, and Validation Checklist.',
    ].join('\n'),
    variables: [
      { name: 'repository_context', description: 'Current repository and task details' },
      { name: 'acceptance_criteria', description: 'Must-pass functional requirements' },
    ],
  },
  {
    id: 'support-router',
    label: 'Customer support router',
    taskType: 'routing',
    prompt: [
      'You classify inbound support tickets into routing queues.',
      'Output strict JSON with queue, priority, rationale, and required follow-up fields.',
      'Escalate safety, billing, and outage issues immediately.',
    ].join('\n'),
    variables: [
      { name: 'ticket_text', description: 'Raw customer message' },
      { name: 'customer_tier', description: 'Plan level used for SLA priority' },
    ],
  },
  {
    id: 'qa-assistant',
    label: 'Simple Q&A assistant',
    taskType: 'qa',
    prompt: [
      'Answer user questions using only retrieved context.',
      'If answer is unknown, respond with "I do not know based on provided context."',
      'Keep answers concise and include citation IDs from source chunks.',
    ].join('\n'),
    variables: [
      { name: 'question', description: 'User question' },
      { name: 'context_chunks', description: 'Retrieved evidence snippets with ids' },
    ],
  },
];

function toExampleRows(example: PromptExample) {
  return example.variables.map((item, index) => ({
    id: `${example.id}_${index}`,
    name: item.name,
    description: item.description,
  }));
}

export function PromptInput() {
  const rawPrompt = useConfigurationStore((state) => state.rawPrompt);
  const setRawPrompt = useConfigurationStore((state) => state.setRawPrompt);
  const setInputVariableRows = useConfigurationStore((state) => state.setInputVariableRows);
  const setInputVariablesMode = useConfigurationStore((state) => state.setInputVariablesMode);
  const setInputVariablesRaw = useConfigurationStore((state) => state.setInputVariablesRaw);

  const phase = useWorkflowStore((state) => state.phase);
  const reset = useWorkflowStore((state) => state.reset);
  const error = useWorkflowStore((state) => state.error);
  const setTaskType = useWorkflowStore((state) => state.setTaskType);

  const hasPromptError = (error?.message ?? '').toLowerCase().includes('enter a prompt');

  const handleChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = event.target.value;
    setRawPrompt(newValue);

    if (phase !== 'idle') {
      reset();
    }
  };

  const applyExample = (exampleId: string) => {
    const selected = EXAMPLES.find((example) => example.id === exampleId);
    if (!selected) {
      return;
    }

    setRawPrompt(selected.prompt);
    setTaskType(selected.taskType);
    setInputVariablesMode('rows');
    setInputVariableRows(toExampleRows(selected));
    setInputVariablesRaw('');

    if (phase !== 'idle') {
      reset();
    }
  };

  return (
    <div className="space-y-2.5 min-w-0">
      <div className="flex items-center justify-between gap-2 flex-wrap min-w-0">
        <label
          className="block font-medium"
          style={{ fontSize: '12px', color: 'var(--text-primary)' }}
        >
          Your Prompt
        </label>

        <div className="w-full min-[320px]:w-[180px] min-w-0">
          <Select onValueChange={applyExample}>
            <SelectTrigger className="h-8 text-[11px]">
              <SelectValue placeholder="Load example" />
            </SelectTrigger>
            <SelectContent>
              {EXAMPLES.map((example) => (
                <SelectItem key={example.id} value={example.id}>
                  {example.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <Textarea
        value={rawPrompt}
        onChange={handleChange}
        placeholder="Paste your system prompt here..."
        rows={7}
        className="resize-y leading-relaxed"
        style={{
          fontSize: '13px',
          borderColor: hasPromptError ? 'var(--danger)' : undefined,
          boxShadow: hasPromptError ? '0 0 0 1px rgba(255,107,107,0.2)' : undefined,
        }}
      />
    </div>
  );
}
