/**
 * VariableInput Component
 *
 * Structured variable editor with a raw fallback mode.
 */

import { Button, Input, Textarea } from '@/components/ui';
import { useConfigurationStore, useSerializedInputVariables } from '@/store';

export function VariableInput() {
  const inputVariablesMode = useConfigurationStore((state) => state.inputVariablesMode);
  const setInputVariablesMode = useConfigurationStore((state) => state.setInputVariablesMode);
  const inputVariableRows = useConfigurationStore((state) => state.inputVariableRows);
  const addInputVariableRow = useConfigurationStore((state) => state.addInputVariableRow);
  const updateInputVariableRow = useConfigurationStore((state) => state.updateInputVariableRow);
  const removeInputVariableRow = useConfigurationStore((state) => state.removeInputVariableRow);
  const inputVariablesRaw = useConfigurationStore((state) => state.inputVariablesRaw);
  const setInputVariablesRaw = useConfigurationStore((state) => state.setInputVariablesRaw);

  const serializedInputVariables = useSerializedInputVariables();

  return (
    <div className="space-y-2.5 min-w-0">
      <div className="flex items-center justify-between gap-2">
        <div
          style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}
        >
          Define variable names and usage notes
        </div>
        <div
          className="inline-flex p-0.5 rounded-md"
          style={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)' }}
        >
          <button
            type="button"
            onClick={() => setInputVariablesMode('rows')}
            className="px-2 py-1 rounded transition-colors"
            style={{
              fontSize: '10px',
              fontWeight: 600,
              color: inputVariablesMode === 'rows' ? 'var(--teal)' : 'var(--text-secondary)',
              backgroundColor: inputVariablesMode === 'rows' ? 'var(--teal-soft)' : 'transparent',
            }}
          >
            Rows
          </button>
          <button
            type="button"
            onClick={() => setInputVariablesMode('raw')}
            className="px-2 py-1 rounded transition-colors"
            style={{
              fontSize: '10px',
              fontWeight: 600,
              color: inputVariablesMode === 'raw' ? 'var(--teal)' : 'var(--text-secondary)',
              backgroundColor: inputVariablesMode === 'raw' ? 'var(--teal-soft)' : 'transparent',
            }}
          >
            Raw
          </button>
        </div>
      </div>

      {inputVariablesMode === 'rows' ? (
        <div
          className="rounded-lg p-2.5 space-y-2"
          style={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)' }}
        >
          <div
            className="grid gap-2 px-1"
            style={{ gridTemplateColumns: '20px minmax(0, 1fr) minmax(0, 1.2fr) 24px' }}
          >
            <span />
            <span style={{ fontSize: '10px', color: 'var(--text-tertiary)', fontWeight: 600 }}>
              Variable name
            </span>
            <span style={{ fontSize: '10px', color: 'var(--text-tertiary)', fontWeight: 600 }}>
              Description
            </span>
            <span />
          </div>

          <div className="space-y-2">
            {inputVariableRows.map((row) => (
              <div
                key={row.id}
                className="grid items-center gap-2"
                style={{ gridTemplateColumns: '20px minmax(0, 1fr) minmax(0, 1.2fr) 24px' }}
              >
                <span
                  className="inline-flex items-center justify-center rounded px-1"
                  style={{
                    fontSize: '9px',
                    color: 'var(--teal)',
                    backgroundColor: 'var(--teal-soft)',
                    border: '1px solid rgba(45, 212, 191, 0.35)',
                  }}
                >
                  {'{}'}
                </span>

                <Input
                  value={row.name}
                  onChange={(event) =>
                    updateInputVariableRow(row.id, { name: event.target.value })
                  }
                  placeholder="documents"
                  className="h-8 text-[11px] font-mono"
                />

                <Input
                  value={row.description}
                  onChange={(event) =>
                    updateInputVariableRow(row.id, { description: event.target.value })
                  }
                  placeholder="array of PDFs to analyze"
                  className="h-8 text-[11px] font-normal"
                />

                <button
                  type="button"
                  onClick={() => removeInputVariableRow(row.id)}
                  className="h-6 w-6 rounded transition-colors"
                  style={{
                    color: 'var(--text-tertiary)',
                    backgroundColor: 'transparent',
                    border: '1px solid var(--border)',
                  }}
                  aria-label="Remove variable row"
                  title="Remove row"
                >
                  x
                </button>
              </div>
            ))}
          </div>

          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={addInputVariableRow}
            className="h-7 text-[10.5px]"
          >
            + Add row
          </Button>
        </div>
      ) : (
        <Textarea
          value={inputVariablesRaw}
          onChange={(event) => setInputVariablesRaw(event.target.value)}
          placeholder={'{{documents}} - array of PDFs\n{{threshold}} - risk % threshold'}
          rows={4}
          className="resize-y text-[11px]"
        />
      )}

      {serializedInputVariables && (
        <p style={{ fontSize: '10px', color: 'var(--text-tertiary)' }}>
          Serialized payload preview is active for API requests.
        </p>
      )}
    </div>
  );
}
