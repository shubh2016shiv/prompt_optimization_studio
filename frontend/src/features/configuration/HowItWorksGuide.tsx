/**
 * HowItWorksGuide Component
 *
 * Persistent onboarding card for the 4-step flow.
 */

const STEPS = [
  {
    number: '1',
    title: 'Analyse Gaps',
    description: 'Audit prompt coverage across Task, Context, Role, Tone, and Execution.',
  },
  {
    number: '2',
    title: 'Interview',
    description: 'Answer targeted questions to close structural gaps before generation.',
  },
  {
    number: '3',
    title: 'Optimise',
    description: 'Generate three production-ready prompt variants with safeguards.',
  },
  {
    number: '4',
    title: 'Refine in Chat',
    description: 'Iterate conversationally with full workflow context loaded.',
  },
];

export function HowItWorksGuide() {
  return (
    <div className="space-y-2.5">
      {STEPS.map((step) => (
        <div key={step.number} className="flex items-start gap-2.5">
          <div
            className="mt-0.5 h-5 w-5 rounded-full flex items-center justify-center"
            style={{
              fontSize: '10px',
              fontWeight: 700,
              color: 'var(--teal)',
              backgroundColor: 'var(--teal-soft)',
              border: '1px solid rgba(45, 212, 191, 0.35)',
            }}
          >
            {step.number}
          </div>
          <div className="min-w-0">
            <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>
              {step.title}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', lineHeight: 1.45 }}>
              {step.description}
            </div>
          </div>
        </div>
      ))}

      <p style={{ fontSize: '11px', color: 'var(--teal)' }}>
        See project documentation for full framework details.
      </p>
    </div>
  );
}
