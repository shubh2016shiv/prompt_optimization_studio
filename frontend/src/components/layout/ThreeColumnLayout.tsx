/**
 * ThreeColumnLayout Component
 *
 * Main layout with premium header, workflow stepper, and collapsible chat rail.
 */

import { useEffect, useMemo, useRef, useState, type MouseEvent as ReactMouseEvent, type ReactNode } from 'react';
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
  const [leftPanelWidth, setLeftPanelWidth] = useState<number>(LAYOUT.leftPanelWidth);
  const rightPanelWidth = isRightPanelCollapsed
    ? LAYOUT.rightPanelCollapsedWidth
    : LAYOUT.rightPanelWidth;

  const backendHealth = useBackendHealth();
  const phase = useWorkflowStore((state) => state.phase);

  const previousStatusRef = useRef(backendHealth.status);
  const [showOfflineToast, setShowOfflineToast] = useState(false);
  const leftResizeRef = useRef<{
    isDragging: boolean;
    startX: number;
    startWidth: number;
  }>({
    isDragging: false,
    startX: 0,
    startWidth: LAYOUT.leftPanelWidth,
  });

  const maxLeftPanelWidth = useMemo(() => {
    const available = window.innerWidth - rightPanelWidth - LAYOUT.minMiddlePanelWidth - 36;
    return Math.max(240, Math.min(560, available));
  }, [rightPanelWidth]);

  const clampLeftWidth = (next: number) => Math.min(maxLeftPanelWidth, Math.max(240, next));

  useEffect(() => {
    if (backendHealth.status === 'offline' && previousStatusRef.current !== 'offline') {
      setShowOfflineToast(true);
    }

    if (backendHealth.status !== 'offline') {
      setShowOfflineToast(false);
    }

    previousStatusRef.current = backendHealth.status;
  }, [backendHealth.status]);

  useEffect(() => {
    setLeftPanelWidth((current) => clampLeftWidth(current));
  }, [maxLeftPanelWidth]);

  const startLeftResize = (event: ReactMouseEvent<HTMLDivElement>) => {
    leftResizeRef.current = {
      isDragging: true,
      startX: event.clientX,
      startWidth: leftPanelWidth,
    };
    document.body.style.userSelect = 'none';

    const handleMouseMove = (moveEvent: MouseEvent) => {
      if (!leftResizeRef.current.isDragging) {
        return;
      }

      const delta = moveEvent.clientX - leftResizeRef.current.startX;
      const proposedWidth = leftResizeRef.current.startWidth + delta;
      setLeftPanelWidth(clampLeftWidth(proposedWidth));
    };

    const handleMouseUp = () => {
      leftResizeRef.current.isDragging = false;
      document.body.style.userSelect = '';
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
  };

  return (
    <div
      className="flex flex-col bg-[var(--surface-1)] overflow-hidden"
      style={{ height: '100dvh', minHeight: '100vh' }}
    >
      <header
        className="shrink-0 border-b relative overflow-hidden"
        style={{
          height: 52,
          backgroundColor: 'var(--surface-2)',
          borderColor: 'var(--border-subtle)',
        }}
      >
        <div className="absolute inset-0 ambient-gradient opacity-30" />

        <div className="relative h-full px-4 flex items-center gap-4">
          <div className="flex items-center gap-2.5 shrink-0">
            <div
              className="rounded-md flex items-center justify-center shrink-0"
              style={{
                width: 22,
                height: 22,
                background: 'linear-gradient(135deg, var(--teal), var(--accent))',
                boxShadow: '0 0 12px rgba(45, 212, 191, 0.28)',
                fontSize: 11,
                color: '#00130f',
                fontWeight: 800,
              }}
            >
              A
            </div>

            <div>
              <div className="flex items-center gap-2">
                <span
                  style={{
                    fontSize: '14px',
                    color: 'var(--text-primary)',
                    fontWeight: 700,
                    letterSpacing: '-0.2px',
                  }}
                >
                  APOST
                </span>
                <span
                  className="rounded-full"
                  style={{
                    width: 8,
                    height: 8,
                    backgroundColor: backendHealth.color,
                    boxShadow: `0 0 10px ${backendHealth.color}`,
                  }}
                  title={backendHealth.tooltip}
                  aria-label={backendHealth.label}
                />
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', fontWeight: 400 }}>
                Prompt Optimisation Studio
              </div>
            </div>
          </div>

          <div
            className="shrink-0 self-stretch"
            style={{ width: 1, backgroundColor: 'var(--border-subtle)', margin: '10px 0' }}
          />

          <div className="flex-1 flex justify-center">
            <StepIndicator phase={phase} />
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <span
              className="px-2 py-0.5 rounded"
              style={{
                fontSize: '9px',
                color: 'var(--text-secondary)',
                backgroundColor: 'var(--surface-3)',
                border: '1px solid var(--border-subtle)',
                fontWeight: 700,
                letterSpacing: '0.04em',
              }}
            >
              v4
            </span>
          </div>
        </div>
      </header>

      <m.main
        className="flex-1 flex overflow-hidden min-h-0"
        variants={STAGGER_CONTAINER_VARIANTS}
        initial="hidden"
        animate="visible"
      >
        <m.aside
          className="shrink-0 overflow-y-auto flex flex-col min-w-0 min-h-0"
          style={{
            width: leftPanelWidth,
            backgroundColor: 'var(--surface-2)',
            borderColor: 'var(--border-subtle)',
          }}
          variants={STAGGER_ITEM_VARIANTS}
        >
          {leftPanel}
        </m.aside>

        <div
          role="separator"
          aria-orientation="vertical"
          aria-label="Resize left configuration panel"
          onMouseDown={startLeftResize}
          className="shrink-0 cursor-col-resize transition-colors hover:bg-[rgba(45,212,191,0.18)]"
          style={{
            width: 4,
            borderRight: '1px solid var(--border-subtle)',
            borderLeft: '1px solid var(--border-subtle)',
            backgroundColor: 'rgba(255,255,255,0.02)',
          }}
        />

        <m.section
          className="flex-1 flex flex-col overflow-hidden min-w-0 min-h-0"
          style={{
            minWidth: LAYOUT.minMiddlePanelWidth,
            backgroundColor: 'var(--surface-1)',
          }}
          variants={STAGGER_ITEM_VARIANTS}
        >
          {middlePanel}
        </m.section>

        <m.aside
          className="shrink-0 border-l flex flex-col overflow-hidden min-h-0"
          style={{
            width: rightPanelWidth,
            backgroundColor: 'var(--surface-2)',
            borderColor: 'var(--border-subtle)',
            transition: 'width 280ms ease',
          }}
          variants={STAGGER_ITEM_VARIANTS}
        >
          {rightPanel}
        </m.aside>
      </m.main>

      {showOfflineToast && (
        <div className="fixed bottom-4 right-4 z-40">
          <div
            className="rounded-lg px-3 py-2.5 flex items-start gap-3"
            style={{
              backgroundColor: 'rgba(255, 107, 107, 0.12)',
              border: '1px solid rgba(255, 107, 107, 0.32)',
              boxShadow: 'var(--shadow-md)',
              maxWidth: 320,
            }}
          >
            <div
              className="mt-1 h-2 w-2 rounded-full"
              style={{ backgroundColor: 'var(--danger)' }}
            />
            <div className="min-w-0">
              <div style={{ fontSize: '12px', color: 'var(--text-primary)', fontWeight: 600 }}>
                Backend offline
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: 2 }}>
                API calls may fail until connectivity is restored.
              </div>
            </div>
            <button
              type="button"
              onClick={() => setShowOfflineToast(false)}
              className="rounded px-1"
              style={{ fontSize: '12px', color: 'var(--text-secondary)' }}
              aria-label="Dismiss backend offline notice"
              title="Dismiss"
            >
              x
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
