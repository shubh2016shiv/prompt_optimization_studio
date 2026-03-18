/**
 * ThreeColumnLayout Component
 * 
 * The main layout structure with left config panel, middle workflow, and right chat.
 * Includes the ambient gradient header and staggered panel animations.
 */

import { type ReactNode } from 'react';
import { m } from 'framer-motion';
import { LAYOUT, STAGGER_CONTAINER_VARIANTS, STAGGER_ITEM_VARIANTS } from '@/constants';
import { useBackendHealth } from '@/hooks';

interface ThreeColumnLayoutProps {
  /** Left panel content (configuration) */
  leftPanel: ReactNode;
  /** Middle panel content (workflow) */
  middlePanel: ReactNode;
  /** Right panel content (chat) */
  rightPanel: ReactNode;
  /** Whether the right panel is collapsed */
  isRightPanelCollapsed?: boolean;
}

/**
 * Main three-column layout with header.
 * 
 * Uses CSS Grid for responsive layout:
 * - Desktop: Three columns side by side
 * - Tablet: Stacked layout with collapsible panels
 */
export function ThreeColumnLayout({
  leftPanel,
  middlePanel,
  rightPanel,
  isRightPanelCollapsed = false,
}: ThreeColumnLayoutProps) {
  const rightPanelWidth = isRightPanelCollapsed 
    ? LAYOUT.rightPanelCollapsedWidth 
    : LAYOUT.rightPanelWidth;
  const backendHealth = useBackendHealth();

  return (
    <div className="min-h-screen flex flex-col bg-[var(--background)]">
      {/* Header with ambient gradient */}
      <header className="h-12 shrink-0 border-b border-[var(--border)] bg-[var(--surface)] relative overflow-hidden">
        {/* Ambient gradient mesh */}
        <div className="absolute inset-0 ambient-gradient opacity-40" />
        
        {/* Header content */}
        <div className="relative h-full px-4 flex items-center gap-3">
          {/* Logo */}
          <div 
            className="w-7 h-7 rounded-md flex items-center justify-center text-sm shrink-0"
            style={{
              background: 'linear-gradient(135deg, var(--primary-action), var(--accent))',
            }}
          >
            ⬡
          </div>
          
          {/* Title */}
          <h1 className="text-[var(--text-lg)] font-bold tracking-tight text-[var(--text-primary)]">
            APOST
            <span className="text-[var(--text-sm)] font-normal text-[var(--text-secondary)] ml-2 tracking-normal">
              Prompt Optimisation Studio
            </span>
          </h1>

          {/* Header status and badges */}
          <div className="ml-auto flex items-center gap-2">
            <div
              className="px-2.5 py-1 rounded-full border flex items-center gap-1.5"
              style={{
                backgroundColor: backendHealth.background,
                borderColor: `${backendHealth.color}30`,
                color: backendHealth.color,
              }}
              title={backendHealth.label}
            >
              <span
                className="w-1.5 h-1.5 rounded-full"
                style={{ backgroundColor: backendHealth.color }}
              />
              <span
                className="font-semibold"
                style={{ fontSize: 'var(--text-xs)' }}
              >
                {backendHealth.label}
              </span>
            </div>

            <div className="flex gap-1.5">
            {[
              ['v4.0', 'var(--success)', 'var(--success-soft)'],
              ['TCRTE', 'var(--cyan)', 'var(--cyan-soft)'],
              ['CoRe+RAL', 'var(--orange)', 'var(--orange-soft)'],
              ['+AI Chat', 'var(--pink)', 'var(--pink-soft)'],
            ].map(([label, color, bg]) => (
              <span
                key={label}
                className="px-2 py-0.5 rounded font-bold uppercase tracking-wide font-mono"
                style={{
                  fontSize: 'var(--text-xs)',
                  color: color,
                  backgroundColor: bg,
                  border: `1px solid ${color}28`,
                }}
              >
                {label}
              </span>
            ))}
            </div>
          </div>
        </div>
      </header>

      {/* Main content area */}
      <m.main
        className="flex-1 flex overflow-hidden"
        style={{ height: `calc(100vh - ${LAYOUT.headerHeight}px)` }}
        variants={STAGGER_CONTAINER_VARIANTS}
        initial="hidden"
        animate="visible"
      >
        {/* Left Panel - Configuration */}
        <m.aside
          className="shrink-0 border-r border-[var(--border)] overflow-y-auto flex flex-col"
          style={{ 
            width: LAYOUT.leftPanelWidth,
            backgroundColor: 'var(--surface)',
          }}
          variants={STAGGER_ITEM_VARIANTS}
        >
          {leftPanel}
        </m.aside>

        {/* Middle Panel - Workflow (slightly lighter than sides for visual separation) */}
        <m.section
          className="flex-1 flex flex-col overflow-hidden"
          style={{ 
            minWidth: LAYOUT.minMiddlePanelWidth,
            backgroundColor: 'var(--background)',
          }}
          variants={STAGGER_ITEM_VARIANTS}
        >
          {middlePanel}
        </m.section>

        {/* Right Panel - Chat */}
        <m.aside
          className="shrink-0 border-l border-[var(--border)] flex flex-col overflow-hidden"
          style={{ 
            width: rightPanelWidth,
            backgroundColor: 'var(--surface)',
            transition: 'width 0.22s ease',
          }}
          variants={STAGGER_ITEM_VARIANTS}
        >
          {rightPanel}
        </m.aside>
      </m.main>
    </div>
  );
}
