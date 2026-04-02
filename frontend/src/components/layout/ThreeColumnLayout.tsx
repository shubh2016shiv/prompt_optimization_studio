/**
 * ThreeColumnLayout Component
 *
 * Main layout: left config panel, middle workflow, right chat.
 * Features a premium header with animated step indicator.
 */

import { type ReactNode } from 'react';
import { m } from 'framer-motion';
import { LAYOUT, STAGGER_CONTAINER_VARIANTS, STAGGER_ITEM_VARIANTS } from '@/constants';
import { useBackendHealth } from '@/hooks';
import { useWorkflowStore } from '@/store';
import { StepIndicator } from './StepIndicator';

interface ThreeColumnLayoutProps {
  leftPanel: ReactNode;
  middlePanel: ReactNode;
  rightPanel: ReactNode;
  isRightPanelCollapsed?: boolean;
}

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
  const phase = useWorkflowStore((state) => state.phase);

  return (
    <div className="min-h-screen flex flex-col bg-[var(--background)]">
      {/* ── Premium Header ────────────────────────────────────────── */}
      <header
        className="shrink-0 border-b border-[var(--border)] relative overflow-hidden"
        style={{ height: 52, backgroundColor: 'var(--surface)' }}
      >
        {/* Ambient gradient mesh */}
        <div className="absolute inset-0 ambient-gradient opacity-40" />

        {/* Content */}
        <div className="relative h-full px-4 flex items-center gap-4">
          {/* Logo mark + title */}
          <div className="flex items-center gap-2.5 shrink-0">
            <div
              className="w-7 h-7 rounded-lg flex items-center justify-center text-sm font-bold shrink-0"
              style={{
                background: 'linear-gradient(135deg, var(--primary-action), var(--accent))',
                boxShadow: '0 0 14px rgba(45,212,191,0.28)',
              }}
            >
              ⬡
            </div>
            <div>
              <div className="flex items-baseline gap-1.5">
                <span
                  className="font-extrabold tracking-tight"
                  style={{ fontSize: '15px', color: 'var(--text-primary)', letterSpacing: '-0.3px' }}
                >
                  APOST
                </span>
                <span
                  style={{ fontSize: '11px', color: 'var(--text-tertiary)', fontWeight: 400 }}
                >
                  Prompt Optimisation Studio
                </span>
              </div>
            </div>
          </div>

          {/* Separator */}
          <div
            className="shrink-0 self-stretch"
            style={{ width: 1, backgroundColor: 'var(--border)', margin: '10px 0' }}
          />

          {/* Step indicator — centered */}
          <div className="flex-1 flex justify-center">
            <StepIndicator phase={phase} />
          </div>

          {/* Right: backend status */}
          <div className="flex items-center gap-2 shrink-0">
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
              <span style={{ fontSize: '10px', fontWeight: 600 }}>
                {backendHealth.label}
              </span>
            </div>

            {/* Version badge */}
            <span
              className="px-2 py-0.5 rounded font-bold font-mono"
              style={{
                fontSize: '10px',
                color: 'var(--success)',
                backgroundColor: 'var(--success-soft)',
                border: '1px solid rgba(61,214,140,0.22)',
                letterSpacing: '0.5px',
              }}
            >
              v4.0
            </span>
          </div>
        </div>
      </header>

      {/* ── Main Content ──────────────────────────────────────────── */}
      <m.main
        className="flex-1 flex overflow-hidden"
        style={{ height: `calc(100vh - 52px)` }}
        variants={STAGGER_CONTAINER_VARIANTS}
        initial="hidden"
        animate="visible"
      >
        {/* Left Panel */}
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

        {/* Middle Panel */}
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

        {/* Right Panel */}
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
