/**
 * Design token constants for use in JavaScript/TypeScript.
 * 
 * These should stay in sync with the CSS variables in globals.css.
 * Use CSS variables directly when possible; these are for cases
 * where JS access is needed (e.g., dynamic styles, Motion animations).
 */

export const COLORS = {
  // Background layers
  background: '#0a0c14',
  surface: '#0f1219',
  surfaceRaised: '#151a24',
  surfaceOverlay: '#1a2030',

  // Borders
  border: '#1e2538',
  borderElevated: '#2a3350',

  // Text
  textPrimary: '#e2e6f0',
  textSecondary: '#8892b0',
  textTertiary: '#4a5270',

  // Accent
  accent: '#6c8aff',
  accentSoft: 'rgba(108, 138, 255, 0.12)',
  accentGlow: 'rgba(108, 138, 255, 0.28)',

  // Status
  success: '#3dd68c',
  successSoft: 'rgba(61, 214, 140, 0.12)',
  warning: '#f5a623',
  warningSoft: 'rgba(245, 166, 35, 0.12)',
  danger: '#ff6b6b',
  dangerSoft: 'rgba(255, 107, 107, 0.12)',

  // Feature colors
  purple: '#b57bee',
  purpleSoft: 'rgba(181, 123, 238, 0.12)',
  cyan: '#36cfc9',
  cyanSoft: 'rgba(54, 207, 201, 0.12)',
  pink: '#f06292',
  pinkSoft: 'rgba(240, 98, 146, 0.12)',
  orange: '#ff9f43',
  orangeSoft: 'rgba(255, 159, 67, 0.11)',
  teal: '#2dd4bf',
  tealSoft: 'rgba(45, 212, 191, 0.13)',
  tealGlow: 'rgba(45, 212, 191, 0.30)',

  // Primary action alias — single token for the main CTA colour
  primaryAction: '#2dd4bf',
  primaryActionSoft: 'rgba(45, 212, 191, 0.13)',
  primaryActionGlow: 'rgba(45, 212, 191, 0.30)',
} as const;

export const FONTS = {
  sans: "'Inter', 'IBM Plex Sans', system-ui, sans-serif",
  mono: "'JetBrains Mono', 'Fira Code', monospace",
} as const;

export const TYPE_SCALE = {
  xs:   '11px',
  sm:   '12px',
  base: '13px',
  md:   '14px',
  lg:   '16px',
  xl:   '20px',
} as const;

export const SPACING = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  '2xl': 32,
} as const;

export const RADIUS = {
  sm: 6,
  md: 8,
  lg: 12,
  xl: 16,
} as const;

export const TRANSITIONS = {
  fast: '120ms ease-out',
  normal: '200ms ease-out',
  slow: '350ms ease-out',
} as const;

/** Motion animation variants for staggered panel entrance */
export const STAGGER_CONTAINER_VARIANTS = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.08,
      delayChildren: 0.1,
    },
  },
} as const;

export const STAGGER_ITEM_VARIANTS = {
  hidden: { opacity: 0, y: 12 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.35,
      ease: [0.25, 0.1, 0.25, 1],
    },
  },
} as const;

/** Motion animation variants for phase transitions */
export const PHASE_TRANSITION_VARIANTS = {
  initial: { opacity: 0, y: 8 },
  animate: { 
    opacity: 1, 
    y: 0,
    transition: {
      duration: 0.25,
      ease: [0.25, 0.1, 0.25, 1],
    },
  },
  exit: { 
    opacity: 0, 
    y: -8,
    transition: {
      duration: 0.2,
      ease: [0.25, 0.1, 0.25, 1],
    },
  },
} as const;

/** Motion spring config for score animations */
export const SCORE_SPRING_CONFIG = {
  stiffness: 100,
  damping: 20,
  mass: 1,
} as const;

/** Layout dimensions */
export const LAYOUT = {
  leftPanelWidth: 300,
  rightPanelWidth: 340,
  rightPanelCollapsedWidth: 48,
  minMiddlePanelWidth: 480,
  headerHeight: 48,
  mobileBreakpoint: 1024,
} as const;
