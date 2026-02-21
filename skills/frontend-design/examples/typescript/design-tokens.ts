/**
 * Design Tokens — Type-Safe Token Definitions
 * 
 * This file provides TypeScript interfaces and types for the design token system.
 * Use these to ensure type safety when working with design tokens programmatically.
 * 
 * Location: {project_path}/skills/frontend-design/examples/typescript/design-tokens.ts
 */

// ============================================
// Color Tokens
// ============================================

export interface ColorTokens {
  // Background & Surfaces
  background: string;
  surface: string;
  surfaceSubtle: string;
  surfaceHover: string;
  
  // Text
  text: string;
  textSecondary: string;
  textMuted: string;
  textInverse: string;
  
  // Borders
  border: string;
  borderSubtle: string;
  borderStrong: string;
  
  // Primary
  primary: string;
  primaryHover: string;
  primaryActive: string;
  primarySubtle: string;
  primaryMuted: string;
  primaryForeground: string;
  
  // Secondary
  secondary: string;
  secondaryHover: string;
  secondaryActive: string;
  secondarySubtle: string;
  secondaryForeground: string;
  
  // Accent
  accent: string;
  accentHover: string;
  accentForeground: string;
  
  // Semantic Colors
  success: string;
  successSubtle: string;
  successForeground: string;
  
  warning: string;
  warningSubtle: string;
  warningForeground: string;
  
  danger: string;
  dangerSubtle: string;
  dangerForeground: string;
  
  info: string;
  infoSubtle: string;
  infoForeground: string;
  
  // Overlays
  overlay: string;
  scrim: string;
}

// ============================================
// Typography Tokens
// ============================================

export interface TypographyToken {
  fontSize: string;
  lineHeight: string;
  fontWeight: number;
  letterSpacing?: string;
}

export interface TypographyTokens {
  display: TypographyToken;
  h1: TypographyToken;
  h2: TypographyToken;
  h3: TypographyToken;
  h4: TypographyToken;
  body: TypographyToken;
  bodySmall: TypographyToken;
  caption: TypographyToken;
  mono: TypographyToken;
}

// Font families
export interface FontFamilies {
  sans: string;
  serif: string;
  mono: string;
}

// ============================================
// Spacing Tokens
// ============================================

export interface SpacingTokens {
  0: string;
  px: string;
  0.5: string;
  1: string;
  1.5: string;
  2: string;
  2.5: string;
  3: string;
  4: string;
  5: string;
  6: string;
  7: string;
  8: string;
  9: string;
  10: string;
  12: string;
  14: string;
  16: string;
  20: string;
  24: string;
  28: string;
  32: string;
  36: string;
  40: string;
  48: string;
  56: string;
  64: string;
}

// ============================================
// Radius Tokens
// ============================================

export interface RadiusTokens {
  none: string;
  xs: string;
  sm: string;
  md: string;
  lg: string;
  xl: string;
  '2xl': string;
  '3xl': string;
  full: string;
}

// ============================================
// Shadow Tokens
// ============================================

export interface ShadowTokens {
  xs: string;
  sm: string;
  md: string;
  lg: string;
  xl: string;
  '2xl': string;
  primary: string;
  secondary: string;
}

// ============================================
// Motion Tokens
// ============================================

export interface MotionTokens {
  // Durations
  instant: string;
  fast: string;
  base: string;
  slow: string;
  slower: string;
  
  // Easings
  easeIn: string;
  easeOut: string;
  easeInOut: string;
  easeBounce: string;
  
  // Common transitions
  transitionColors: string;
  transitionTransform: string;
  transitionOpacity: string;
  transitionAll: string;
}

// ============================================
// Component Size Tokens
// ============================================

export interface ComponentSizeTokens {
  button: {
    sm: string;
    md: string;
    lg: string;
  };
  input: {
    sm: string;
    md: string;
    lg: string;
  };
  icon: {
    xs: string;
    sm: string;
    md: string;
    lg: string;
    xl: string;
    '2xl': string;
  };
  avatar: {
    xs: string;
    sm: string;
    md: string;
    lg: string;
    xl: string;
    '2xl': string;
  };
}

// ============================================
// Z-Index Tokens
// ============================================

export interface ZIndexTokens {
  base: number;
  dropdown: number;
  sticky: number;
  fixed: number;
  modalBackdrop: number;
  modal: number;
  popover: number;
  tooltip: number;
  notification: number;
  max: number;
}

// ============================================
// Complete Design System
// ============================================

export interface DesignTokens {
  colors: ColorTokens;
  typography: TypographyTokens;
  fontFamilies: FontFamilies;
  spacing: SpacingTokens;
  radius: RadiusTokens;
  shadows: ShadowTokens;
  motion: MotionTokens;
  componentSizes: ComponentSizeTokens;
  zIndex: ZIndexTokens;
}

// ============================================
// Theme Type
// ============================================

export type Theme = 'light' | 'dark' | 'system';

export interface ThemeConfig {
  theme: Theme;
  tokens: DesignTokens;
}

// ============================================
// Token Helpers
// ============================================

/**
 * Get CSS variable name for a token
 * @param tokenPath - Dot-separated path to token (e.g., 'colors.primary')
 * @returns CSS variable name (e.g., '--primary')
 */
export function getCSSVariable(tokenPath: string): string {
  const parts = tokenPath.split('.');
  const tokenName = parts[parts.length - 1];
  
  // Convert camelCase to kebab-case
  const kebabCase = tokenName.replace(/([A-Z])/g, '-$1').toLowerCase();
  
  return `var(--${kebabCase})`;
}

/**
 * Get token value from design system
 * @param tokens - Design tokens object
 * @param path - Dot-separated path to token
 * @returns Token value or undefined
 */
export function getTokenValue(tokens: DesignTokens, path: string): string | undefined {
  const parts = path.split('.');
  let value: any = tokens;
  
  for (const part of parts) {
    if (value && typeof value === 'object' && part in value) {
      value = value[part];
    } else {
      return undefined;
    }
  }
  
  return typeof value === 'string' ? value : undefined;
}

// ============================================
// Default Light Theme Tokens
// ============================================

export const lightThemeTokens: DesignTokens = {
  colors: {
    background: 'oklch(99% 0 0)',
    surface: 'oklch(100% 0 0)',
    surfaceSubtle: 'oklch(98% 0.005 250)',
    surfaceHover: 'oklch(97% 0.01 250)',
    
    text: 'oklch(20% 0.01 250)',
    textSecondary: 'oklch(45% 0.015 250)',
    textMuted: 'oklch(60% 0.01 250)',
    textInverse: 'oklch(98% 0 0)',
    
    border: 'oklch(90% 0.005 250)',
    borderSubtle: 'oklch(95% 0.003 250)',
    borderStrong: 'oklch(75% 0.01 250)',
    
    primary: 'oklch(55% 0.18 250)',
    primaryHover: 'oklch(50% 0.20 250)',
    primaryActive: 'oklch(45% 0.22 250)',
    primarySubtle: 'oklch(95% 0.03 250)',
    primaryMuted: 'oklch(85% 0.08 250)',
    primaryForeground: 'oklch(98% 0.01 250)',
    
    secondary: 'oklch(65% 0.08 280)',
    secondaryHover: 'oklch(60% 0.10 280)',
    secondaryActive: 'oklch(55% 0.12 280)',
    secondarySubtle: 'oklch(95% 0.02 280)',
    secondaryForeground: 'oklch(98% 0.01 280)',
    
    accent: 'oklch(70% 0.15 160)',
    accentHover: 'oklch(65% 0.17 160)',
    accentForeground: 'oklch(10% 0.01 160)',
    
    success: 'oklch(65% 0.15 145)',
    successSubtle: 'oklch(95% 0.03 145)',
    successForeground: 'oklch(98% 0.01 145)',
    
    warning: 'oklch(75% 0.15 85)',
    warningSubtle: 'oklch(95% 0.05 85)',
    warningForeground: 'oklch(15% 0.02 85)',
    
    danger: 'oklch(60% 0.20 25)',
    dangerSubtle: 'oklch(95% 0.04 25)',
    dangerForeground: 'oklch(98% 0.01 25)',
    
    info: 'oklch(65% 0.12 230)',
    infoSubtle: 'oklch(95% 0.02 230)',
    infoForeground: 'oklch(98% 0.01 230)',
    
    overlay: 'oklch(0% 0 0 / 0.5)',
    scrim: 'oklch(0% 0 0 / 0.3)',
  },
  
  typography: {
    display: {
      fontSize: 'clamp(3rem, 2.5rem + 2vw, 4.5rem)',
      lineHeight: '1.1',
      fontWeight: 800,
      letterSpacing: '-0.05em',
    },
    h1: {
      fontSize: 'clamp(2.25rem, 1.95rem + 1.2vw, 3.5rem)',
      lineHeight: '1.2',
      fontWeight: 700,
      letterSpacing: '-0.025em',
    },
    h2: {
      fontSize: 'clamp(1.875rem, 1.65rem + 0.9vw, 2.5rem)',
      lineHeight: '1.3',
      fontWeight: 700,
    },
    h3: {
      fontSize: 'clamp(1.5rem, 1.35rem + 0.6vw, 2rem)',
      lineHeight: '1.4',
      fontWeight: 600,
    },
    h4: {
      fontSize: 'clamp(1.25rem, 1.15rem + 0.4vw, 1.5rem)',
      lineHeight: '1.5',
      fontWeight: 600,
    },
    body: {
      fontSize: 'clamp(1rem, 0.95rem + 0.25vw, 1.125rem)',
      lineHeight: '1.6',
      fontWeight: 400,
    },
    bodySmall: {
      fontSize: 'clamp(0.875rem, 0.8rem + 0.2vw, 1rem)',
      lineHeight: '1.5',
      fontWeight: 400,
    },
    caption: {
      fontSize: 'clamp(0.75rem, 0.7rem + 0.15vw, 0.875rem)',
      lineHeight: '1.4',
      fontWeight: 400,
      letterSpacing: '0.025em',
    },
    mono: {
      fontSize: '0.875rem',
      lineHeight: '1.5',
      fontWeight: 400,
    },
  },
  
  fontFamilies: {
    sans: "'Inter', system-ui, -apple-system, sans-serif",
    serif: "'Merriweather', Georgia, serif",
    mono: "'JetBrains Mono', 'Fira Code', monospace",
  },
  
  spacing: {
    0: '0',
    px: '1px',
    0.5: '0.125rem',
    1: '0.25rem',
    1.5: '0.375rem',
    2: '0.5rem',
    2.5: '0.625rem',
    3: '0.75rem',
    4: '1rem',
    5: '1.25rem',
    6: '1.5rem',
    7: '1.75rem',
    8: '2rem',
    9: '2.25rem',
    10: '2.5rem',
    12: '3rem',
    14: '3.5rem',
    16: '4rem',
    20: '5rem',
    24: '6rem',
    28: '7rem',
    32: '8rem',
    36: '9rem',
    40: '10rem',
    48: '12rem',
    56: '14rem',
    64: '16rem',
  },
  
  radius: {
    none: '0',
    xs: '0.125rem',
    sm: '0.25rem',
    md: '0.375rem',
    lg: '0.5rem',
    xl: '0.75rem',
    '2xl': '1rem',
    '3xl': '1.5rem',
    full: '9999px',
  },
  
  shadows: {
    xs: '0 1px 2px 0 oklch(0% 0 0 / 0.05)',
    sm: '0 1px 3px 0 oklch(0% 0 0 / 0.1), 0 1px 2px -1px oklch(0% 0 0 / 0.1)',
    md: '0 4px 6px -1px oklch(0% 0 0 / 0.1), 0 2px 4px -2px oklch(0% 0 0 / 0.1)',
    lg: '0 10px 15px -3px oklch(0% 0 0 / 0.1), 0 4px 6px -4px oklch(0% 0 0 / 0.1)',
    xl: '0 20px 25px -5px oklch(0% 0 0 / 0.1), 0 8px 10px -6px oklch(0% 0 0 / 0.1)',
    '2xl': '0 25px 50px -12px oklch(0% 0 0 / 0.25)',
    primary: '0 4px 12px -2px oklch(55% 0.18 250), 0 2px 6px -2px oklch(55% 0.18 250)',
    secondary: '0 4px 12px -2px oklch(65% 0.08 280), 0 2px 6px -2px oklch(65% 0.08 280)',
  },
  
  motion: {
    instant: '0ms',
    fast: '150ms',
    base: '220ms',
    slow: '300ms',
    slower: '400ms',
    
    easeIn: 'cubic-bezier(0.4, 0, 1, 1)',
    easeOut: 'cubic-bezier(0, 0, 0.2, 1)',
    easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
    easeBounce: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
    
    transitionColors: 'color 150ms cubic-bezier(0, 0, 0.2, 1), background-color 150ms cubic-bezier(0, 0, 0.2, 1), border-color 150ms cubic-bezier(0, 0, 0.2, 1)',
    transitionTransform: 'transform 220ms cubic-bezier(0, 0, 0.2, 1)',
    transitionOpacity: 'opacity 220ms cubic-bezier(0, 0, 0.2, 1)',
    transitionAll: 'all 220ms cubic-bezier(0.4, 0, 0.2, 1)',
  },
  
  componentSizes: {
    button: {
      sm: '2.25rem',
      md: '2.75rem',
      lg: '3rem',
    },
    input: {
      sm: '2.25rem',
      md: '2.5rem',
      lg: '3rem',
    },
    icon: {
      xs: '0.75rem',
      sm: '1rem',
      md: '1.25rem',
      lg: '1.5rem',
      xl: '2rem',
      '2xl': '2.5rem',
    },
    avatar: {
      xs: '1.5rem',
      sm: '2rem',
      md: '2.5rem',
      lg: '3rem',
      xl: '4rem',
      '2xl': '6rem',
    },
  },
  
  zIndex: {
    base: 0,
    dropdown: 1000,
    sticky: 1100,
    fixed: 1200,
    modalBackdrop: 1300,
    modal: 1400,
    popover: 1500,
    tooltip: 1600,
    notification: 1700,
    max: 9999,
  },
};

// ============================================
// Dark Theme Tokens (Overrides only)
// ============================================

export const darkThemeColorOverrides: Partial<ColorTokens> = {
  background: 'oklch(15% 0.01 250)',
  surface: 'oklch(20% 0.015 250)',
  surfaceSubtle: 'oklch(25% 0.02 250)',
  surfaceHover: 'oklch(30% 0.025 250)',
  
  text: 'oklch(95% 0.01 250)',
  textSecondary: 'oklch(70% 0.015 250)',
  textMuted: 'oklch(55% 0.01 250)',
  textInverse: 'oklch(15% 0 0)',
  
  border: 'oklch(35% 0.01 250)',
  borderSubtle: 'oklch(25% 0.005 250)',
  borderStrong: 'oklch(50% 0.015 250)',
  
  primary: 'oklch(65% 0.18 250)',
  primaryHover: 'oklch(70% 0.20 250)',
  primaryActive: 'oklch(75% 0.22 250)',
  primarySubtle: 'oklch(25% 0.08 250)',
  primaryMuted: 'oklch(35% 0.12 250)',
  primaryForeground: 'oklch(10% 0.01 250)',
};

// ============================================
// Type Guards
// ============================================

export function isValidTheme(theme: string): theme is Theme {
  return ['light', 'dark', 'system'].includes(theme);
}

export function isColorToken(token: any): token is keyof ColorTokens {
  return typeof token === 'string' && token in lightThemeTokens.colors;
}

// ============================================
// Utility Functions
// ============================================

/**
 * Merge default tokens with custom overrides
 */
export function mergeTokens(
  base: DesignTokens,
  overrides: Partial<DesignTokens>
): DesignTokens {
  return {
    ...base,
    ...overrides,
    colors: { ...base.colors, ...(overrides.colors || {}) },
    typography: { ...base.typography, ...(overrides.typography || {}) },
    spacing: { ...base.spacing, ...(overrides.spacing || {}) },
    radius: { ...base.radius, ...(overrides.radius || {}) },
    shadows: { ...base.shadows, ...(overrides.shadows || {}) },
    motion: { ...base.motion, ...(overrides.motion || {}) },
  };
}

/**
 * Validate token value format
 */
export function validateTokenValue(value: string, type: 'color' | 'spacing' | 'radius' | 'shadow'): boolean {
  switch (type) {
    case 'color':
      return /^(oklch|rgb|hsl|#)/.test(value);
    case 'spacing':
    case 'radius':
      return /^\d+(\.\d+)?(px|rem|em|%)$/.test(value);
    case 'shadow':
      return value.includes('oklch') || value.includes('rgb') || value === 'none';
    default:
      return false;
  }
}
