/**
 * ThreeColumnLayout Component
 * 
 * The main layout structure with left config panel, middle workflow, and right chat.
 * Includes the ambient gradient header and staggered panel animations.
 */

import { type ReactNode } from 'react';
import { m } from 'framer-motion';
import { LAYOUT, STAGGER_CONTAINER_VARIANTS, STAGGER_ITEM_VARIANTS } from '@/constants';

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

  return (
    <div className="min-h-screen flex flex-col bg-[var(--background)]">
      {/* Header with ambient gradient */}
      <header className="h-14 shrink-0 border-b border-[var(--border)] bg-[var(--surface)] relative overflow-hidden">
        {/* Ambient gradient mesh */}
        <div className="absolute inset-0 ambient-gradient opacity-50" />
        
        {/* Header content */}
        <div className="relative h-full px-5 flex items-center gap-3">
          {/* Logo */}
          <div 
            className="w-8 h-8 rounded-lg flex items-center justify-center text-base shrink-0"
            style={{
              background: 'linear-gradient(135deg, var(--accent), var(--purple))',
            }}
          >
            ⬡
          </div>
          
          {/* Title */}
          <div>
            <h1 className="text-[15px] font-bold tracking-tight text-[var(--text-primary)]">
              APOST — Prompt Optimisation Studio
            </h1>
            <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">
              Smart Gap Analysis · TCRTE Coverage · CoRe · RAL-Writer · Prefill · AI Refinement Chat
            </p>
          </div>

          {/* Version badges */}
          <div className="ml-auto flex gap-1.5">
            {[
              ['v4.0', 'var(--success)', 'var(--success-soft)'],
              ['TCRTE', 'var(--cyan)', 'var(--cyan-soft)'],
              ['CoRe+RAL', 'var(--orange)', 'var(--orange-soft)'],
              ['+AI Chat', 'var(--pink)', 'var(--pink-soft)'],
            ].map(([label, color, bg]) => (
              <span
                key={label}
                className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide font-mono"
                style={{
                  color: color,
                  backgroundColor: bg,
                  border: `1px solid ${color}30`,
                }}
              >
                {label}
              </span>
            ))}
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
          className="shrink-0 bg-[var(--surface)] border-r border-[var(--border)] overflow-y-auto flex flex-col"
          style={{ width: LAYOUT.leftPanelWidth }}
          variants={STAGGER_ITEM_VARIANTS}
        >
          {leftPanel}
        </m.aside>

        {/* Middle Panel - Workflow */}
        <m.section
          className="flex-1 bg-[var(--background)] flex flex-col overflow-hidden"
          style={{ minWidth: LAYOUT.minMiddlePanelWidth }}
          variants={STAGGER_ITEM_VARIANTS}
        >
          {middlePanel}
        </m.section>

        {/* Right Panel - Chat */}
        <m.aside
          className="shrink-0 bg-[var(--surface)] border-l border-[var(--border)] flex flex-col overflow-hidden"
          style={{ 
            width: rightPanelWidth,
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
