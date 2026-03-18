/**
 * PanelHeader Component
 * 
 * A consistent header for panel sections with icon, title, and optional actions.
 */

import { type ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface PanelHeaderProps {
  /** Icon to display (emoji or component) */
  icon?: ReactNode;
  /** Section title */
  title: string;
  /** Optional subtitle or description */
  subtitle?: string;
  /** Optional actions (buttons, etc.) */
  actions?: ReactNode;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Section header with consistent styling.
 * 
 * @example
 * ```tsx
 * <PanelHeader 
 *   icon="✍" 
 *   title="Prompt Input"
 *   subtitle="Enter your raw prompt"
 * />
 * ```
 */
export function PanelHeader({
  icon,
  title,
  subtitle,
  actions,
  className,
}: PanelHeaderProps) {
  return (
    <div
      className={cn(
        'flex items-center justify-between gap-3 mb-3',
        className
      )}
    >
      <div className="flex items-center gap-2">
        {icon && (
          <span className="text-[var(--text-tertiary)]">{icon}</span>
        )}
        <div>
          <h2 className="text-[10px] font-bold uppercase tracking-[1.1px] text-[var(--text-tertiary)]">
            {title}
          </h2>
          {subtitle && (
            <p className="text-[11px] text-[var(--text-tertiary)] mt-0.5">
              {subtitle}
            </p>
          )}
        </div>
      </div>
      {actions && (
        <div className="flex items-center gap-2">
          {actions}
        </div>
      )}
    </div>
  );
}

/**
 * Label for form fields with consistent styling.
 */
export function FieldLabel({
  children,
  hint,
  required,
  className,
}: {
  children: ReactNode;
  hint?: string;
  required?: boolean;
  className?: string;
}) {
  return (
    <label className={cn('block text-[11px] font-semibold text-[var(--text-secondary)] mb-1.5', className)}>
      {children}
      {required && <span className="text-[var(--danger)] ml-0.5">*</span>}
      {hint && (
        <span className="font-normal text-[var(--text-tertiary)] ml-1">({hint})</span>
      )}
    </label>
  );
}
