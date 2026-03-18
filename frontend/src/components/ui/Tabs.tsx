/**
 * Tabs Component
 * 
 * A tabbed interface built on Radix UI Tabs primitives.
 */

import * as React from 'react';
import * as TabsPrimitive from '@radix-ui/react-tabs';
import { cn } from '@/lib/utils';

const Tabs = TabsPrimitive.Root;

const TabsList = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.List
    ref={ref}
    className={cn(
      `inline-flex items-center gap-0.5
       p-1 rounded-lg
       bg-[var(--background)]`,
      className
    )}
    {...props}
  />
));
TabsList.displayName = TabsPrimitive.List.displayName;

const TabsTrigger = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Trigger
    ref={ref}
    className={cn(
      `flex-1 px-3 py-1.5
       rounded-md
       text-xs font-semibold
       text-[var(--text-tertiary)]
       transition-all duration-150
       hover:text-[var(--text-secondary)]
       focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]
       data-[state=active]:bg-[var(--surface)]
       data-[state=active]:text-[var(--text-primary)]
       data-[state=active]:shadow-sm`,
      className
    )}
    {...props}
  />
));
TabsTrigger.displayName = TabsPrimitive.Trigger.displayName;

const TabsContent = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Content
    ref={ref}
    className={cn(
      `mt-2 
       focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]`,
      className
    )}
    {...props}
  />
));
TabsContent.displayName = TabsPrimitive.Content.displayName;

export { Tabs, TabsList, TabsTrigger, TabsContent };
