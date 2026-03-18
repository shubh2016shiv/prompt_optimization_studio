/**
 * StudioPage Component
 * 
 * The main application page that assembles all three panels.
 */

import { TooltipProvider } from '@/components/ui';
import { ThreeColumnLayout } from '@/components/layout';
import { ConfigurationPanel } from '@/features/configuration';
import { WorkflowPanel } from '@/features/workflow';
import { ChatPanel } from '@/features/chat';
import { useChatStore } from '@/store';

/**
 * Main studio page with three-column layout.
 */
export default function StudioPage() {
  const isRightPanelCollapsed = !useChatStore((state) => state.isExpanded);

  return (
    <TooltipProvider>
      <ThreeColumnLayout
        leftPanel={<ConfigurationPanel />}
        middlePanel={<WorkflowPanel />}
        rightPanel={<ChatPanel />}
        isRightPanelCollapsed={isRightPanelCollapsed}
      />
    </TooltipProvider>
  );
}
