/**
 * Design Tokens — Complete CSS Custom Properties System
 * 
 * This file provides a comprehensive design token system for consistent UI development.
 * It includes semantic color slots, typography scales, spacing, radius, shadows, and motion.
 * 
 * Usage:
 * 1. Import this file in your globals.css: @import './tokens.css';
 * 2. Reference tokens using var(--token-name)
 * 3. Override in [data-theme="dark"] for dark mode
 * 
 * Location: {project_path}/skills/frontend-design/examples/css/tokens.css
 */

/* ============================================
   COLOR SYSTEM - Semantic Tokens
   ============================================ */

:root {
  /* Background & Surfaces */
  --background: oklch(99% 0 0);                    /* Main page background */
  --surface: oklch(100% 0 0);                      /* Card/panel background */
  --surface-subtle: oklch(98% 0.005 250);          /* Subtle surface variant */
  --surface-hover: oklch(97% 0.01 250);            /* Hover state for surfaces */
  
  /* Text Colors */
  --text: oklch(20% 0.01 250);                     /* Primary text */
  --text-secondary: oklch(45% 0.015 250);          /* Secondary text */
  --text-muted: oklch(60% 0.01 250);               /* Muted/helper text */
  --text-inverse: oklch(98% 0 0);                  /* Text on dark backgrounds */
  
  /* Borders */
  --border: oklch(90% 0.005 250);                  /* Standard borders */
  --border-subtle: oklch(95% 0.003 250);           /* Subtle dividers */
  --border-strong: oklch(75% 0.01 250);            /* Emphasized borders */
  
  /* Primary Brand */
  --primary: oklch(55% 0.18 250);                  /* Primary brand color */
  --primary-hover: oklch(50% 0.20 250);            /* Primary hover state */
  --primary-active: oklch(45% 0.22 250);           /* Primary active/pressed */
  --primary-subtle: oklch(95% 0.03 250);           /* Primary tint background */
  --primary-muted: oklch(85% 0.08 250);            /* Primary muted variant */
  --primary-foreground: oklch(98% 0.01 250);       /* Text on primary */
  
  /* Secondary */
  --secondary: oklch(65% 0.08 280);                /* Secondary accent */
  --secondary-hover: oklch(60% 0.10 280);          /* Secondary hover */
  --secondary-active: oklch(55% 0.12 280);         /* Secondary active */
  --secondary-subtle: oklch(95% 0.02 280);         /* Secondary tint */
  --secondary-foreground: oklch(98% 0.01 280);     /* Text on secondary */
  
  /* Accent */
  --accent: oklch(70% 0.15 160);                   /* Accent highlights */
  --accent-hover: oklch(65% 0.17 160);             /* Accent hover */
  --accent-foreground: oklch(10% 0.01 160);        /* Text on accent */
  
  /* Semantic Colors */
  --success: oklch(65% 0.15 145);                  /* Success states */
  --success-subtle: oklch(95% 0.03 145);           /* Success background */
  --success-foreground: oklch(98% 0.01 145);       /* Text on success */
  
  --warning: oklch(75% 0.15 85);                   /* Warning states */
  --warning-subtle: oklch(95% 0.05 85);            /* Warning background */
  --warning-foreground: oklch(15% 0.02 85);        /* Text on warning */
  
  --danger: oklch(60% 0.20 25);                    /* Error/danger states */
  --danger-subtle: oklch(95% 0.04 25);             /* Error background */
  --danger-foreground: oklch(98% 0.01 25);         /* Text on danger */
  
  --info: oklch(65% 0.12 230);                     /* Info states */
  --info-subtle: oklch(95% 0.02 230);              /* Info background */
  --info-foreground: oklch(98% 0.01 230);          /* Text on info */
  
  /* Overlays & Scrim */
  --overlay: oklch(0% 0 0 / 0.5);                  /* Modal overlay */
  --scrim: oklch(0% 0 0 / 0.3);                    /* Backdrop scrim */
}

/* Dark Mode Color Adjustments */
[data-theme="dark"] {
  /* Background & Surfaces */
  --background: oklch(15% 0.01 250);
  --surface: oklch(20% 0.015 250);
  --surface-subtle: oklch(25% 0.02 250);
  --surface-hover: oklch(30% 0.025 250);
  
  /* Text Colors */
  --text: oklch(95% 0.01 250);
  --text-secondary: oklch(70% 0.015 250);
  --text-muted: oklch(55% 0.01 250);
  --text-inverse: oklch(15% 0 0);
  
  /* Borders */
  --border: oklch(35% 0.01 250);
  --border-subtle: oklch(25% 0.005 250);
  --border-strong: oklch(50% 0.015 250);
  
  /* Primary Brand (adjusted for dark) */
  --primary: oklch(65% 0.18 250);
  --primary-hover: oklch(70% 0.20 250);
  --primary-active: oklch(75% 0.22 250);
  --primary-subtle: oklch(25% 0.08 250);
  --primary-muted: oklch(35% 0.12 250);
  --primary-foreground: oklch(10% 0.01 250);
  
  /* Secondary */
  --secondary: oklch(70% 0.08 280);
  --secondary-hover: oklch(75% 0.10 280);
  --secondary-active: oklch(80% 0.12 280);
  --secondary-subtle: oklch(25% 0.04 280);
  --secondary-foreground: oklch(10% 0.01 280);
  
  /* Accent */
  --accent: oklch(75% 0.15 160);
  --accent-hover: oklch(80% 0.17 160);
  --accent-foreground: oklch(10% 0.01 160);
  
  /* Semantic Colors (adjusted) */
  --success: oklch(70% 0.15 145);
  --success-subtle: oklch(22% 0.06 145);
  
  --warning: oklch(80% 0.15 85);
  --warning-subtle: oklch(25% 0.08 85);
  
  --danger: oklch(65% 0.20 25);
  --danger-subtle: oklch(22% 0.08 25);
  
  --info: oklch(70% 0.12 230);
  --info-subtle: oklch(22% 0.05 230);
  
  /* Overlays */
  --overlay: oklch(0% 0 0 / 0.7);
  --scrim: oklch(0% 0 0 / 0.5);
}


/* ============================================
   TYPOGRAPHY SCALE
   ============================================ */

:root {
  /* Font Families */
  --font-sans: 'Inter', system-ui, -apple-system, sans-serif;
  --font-serif: 'Merriweather', Georgia, serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
  
  /* Font Sizes - Using clamp() for fluid typography */
  --font-size-xs: clamp(0.75rem, 0.7rem + 0.15vw, 0.875rem);      /* 12-14px */
  --font-size-sm: clamp(0.875rem, 0.8rem + 0.2vw, 1rem);          /* 14-16px */
  --font-size-base: clamp(1rem, 0.95rem + 0.25vw, 1.125rem);      /* 16-18px */
  --font-size-lg: clamp(1.125rem, 1.05rem + 0.3vw, 1.25rem);      /* 18-20px */
  --font-size-xl: clamp(1.25rem, 1.15rem + 0.4vw, 1.5rem);        /* 20-24px */
  --font-size-2xl: clamp(1.5rem, 1.35rem + 0.6vw, 2rem);          /* 24-32px */
  --font-size-3xl: clamp(1.875rem, 1.65rem + 0.9vw, 2.5rem);      /* 30-40px */
  --font-size-4xl: clamp(2.25rem, 1.95rem + 1.2vw, 3.5rem);       /* 36-56px */
  --font-size-5xl: clamp(3rem, 2.5rem + 2vw, 4.5rem);             /* 48-72px */
  
  /* Line Heights */
  --line-height-none: 1;
  --line-height-tight: 1.25;
  --line-height-snug: 1.375;
  --line-height-normal: 1.5;
  --line-height-relaxed: 1.625;
  --line-height-loose: 2;
  
  /* Font Weights */
  --font-weight-light: 300;
  --font-weight-normal: 400;
  --font-weight-medium: 500;
  --font-weight-semibold: 600;
  --font-weight-bold: 700;
  --font-weight-extrabold: 800;
  
  /* Letter Spacing */
  --letter-spacing-tighter: -0.05em;
  --letter-spacing-tight: -0.025em;
  --letter-spacing-normal: 0;
  --letter-spacing-wide: 0.025em;
  --letter-spacing-wider: 0.05em;
  --letter-spacing-widest: 0.1em;
}

/* Typography Presets */
.text-display {
  font-size: var(--font-size-5xl);
  line-height: var(--line-height-tight);
  font-weight: var(--font-weight-extrabold);
  letter-spacing: var(--letter-spacing-tighter);
}

.text-h1 {
  font-size: var(--font-size-4xl);
  line-height: var(--line-height-tight);
  font-weight: var(--font-weight-bold);
  letter-spacing: var(--letter-spacing-tight);
}

.text-h2 {
  font-size: var(--font-size-3xl);
  line-height: var(--line-height-snug);
  font-weight: var(--font-weight-bold);
}

.text-h3 {
  font-size: var(--font-size-2xl);
  line-height: var(--line-height-snug);
  font-weight: var(--font-weight-semibold);
}

.text-h4 {
  font-size: var(--font-size-xl);
  line-height: var(--line-height-normal);
  font-weight: var(--font-weight-semibold);
}

.text-body {
  font-size: var(--font-size-base);
  line-height: var(--line-height-relaxed);
  font-weight: var(--font-weight-normal);
}

.text-small {
  font-size: var(--font-size-sm);
  line-height: var(--line-height-normal);
  font-weight: var(--font-weight-normal);
}

.text-caption {
  font-size: var(--font-size-xs);
  line-height: var(--line-height-normal);
  font-weight: var(--font-weight-normal);
  letter-spacing: var(--letter-spacing-wide);
}


/* ============================================
   SPACING SCALE (8px System)
   ============================================ */

:root {
  --spacing-0: 0;
  --spacing-px: 1px;
  --spacing-0-5: 0.125rem;   /* 2px */
  --spacing-1: 0.25rem;      /* 4px */
  --spacing-1-5: 0.375rem;   /* 6px */
  --spacing-2: 0.5rem;       /* 8px */
  --spacing-2-5: 0.625rem;   /* 10px */
  --spacing-3: 0.75rem;      /* 12px */
  --spacing-4: 1rem;         /* 16px */
  --spacing-5: 1.25rem;      /* 20px */
  --spacing-6: 1.5rem;       /* 24px */
  --spacing-7: 1.75rem;      /* 28px */
  --spacing-8: 2rem;         /* 32px */
  --spacing-9: 2.25rem;      /* 36px */
  --spacing-10: 2.5rem;      /* 40px */
  --spacing-12: 3rem;        /* 48px */
  --spacing-14: 3.5rem;      /* 56px */
  --spacing-16: 4rem;        /* 64px */
  --spacing-20: 5rem;        /* 80px */
  --spacing-24: 6rem;        /* 96px */
  --spacing-28: 7rem;        /* 112px */
  --spacing-32: 8rem;        /* 128px */
  --spacing-36: 9rem;        /* 144px */
  --spacing-40: 10rem;       /* 160px */
  --spacing-48: 12rem;       /* 192px */
  --spacing-56: 14rem;       /* 224px */
  --spacing-64: 16rem;       /* 256px */
}


/* ============================================
   BORDER RADIUS SCALE
   ============================================ */

:root {
  --radius-none: 0;
  --radius-xs: 0.125rem;     /* 2px - badges, tags */
  --radius-sm: 0.25rem;      /* 4px - buttons, small inputs */
  --radius-md: 0.375rem;     /* 6px - inputs, cards */
  --radius-lg: 0.5rem;       /* 8px - large cards */
  --radius-xl: 0.75rem;      /* 12px - modals, panels */
  --radius-2xl: 1rem;        /* 16px - hero sections */
  --radius-3xl: 1.5rem;      /* 24px - special elements */
  --radius-full: 9999px;     /* Pills, avatars, circles */
}


/* ============================================
   SHADOW SCALE
   ============================================ */

:root {
  /* Light Mode Shadows */
  --shadow-xs: 0 1px 2px 0 oklch(0% 0 0 / 0.05);
  --shadow-sm: 0 1px 3px 0 oklch(0% 0 0 / 0.1),
               0 1px 2px -1px oklch(0% 0 0 / 0.1);
  --shadow-md: 0 4px 6px -1px oklch(0% 0 0 / 0.1),
               0 2px 4px -2px oklch(0% 0 0 / 0.1);
  --shadow-lg: 0 10px 15px -3px oklch(0% 0 0 / 0.1),
               0 4px 6px -4px oklch(0% 0 0 / 0.1);
  --shadow-xl: 0 20px 25px -5px oklch(0% 0 0 / 0.1),
               0 8px 10px -6px oklch(0% 0 0 / 0.1);
  --shadow-2xl: 0 25px 50px -12px oklch(0% 0 0 / 0.25);
  
  /* Colored Shadows (for accents) */
  --shadow-primary: 0 4px 12px -2px var(--primary),
                    0 2px 6px -2px var(--primary);
  --shadow-secondary: 0 4px 12px -2px var(--secondary),
                      0 2px 6px -2px var(--secondary);
}

[data-theme="dark"] {
  /* Stronger shadows for dark mode */
  --shadow-xs: 0 1px 2px 0 oklch(0% 0 0 / 0.3);
  --shadow-sm: 0 1px 3px 0 oklch(0% 0 0 / 0.4),
               0 1px 2px -1px oklch(0% 0 0 / 0.3);
  --shadow-md: 0 4px 6px -1px oklch(0% 0 0 / 0.4),
               0 2px 4px -2px oklch(0% 0 0 / 0.3);
  --shadow-lg: 0 10px 15px -3px oklch(0% 0 0 / 0.5),
               0 4px 6px -4px oklch(0% 0 0 / 0.4);
  --shadow-xl: 0 20px 25px -5px oklch(0% 0 0 / 0.5),
               0 8px 10px -6px oklch(0% 0 0 / 0.4);
  --shadow-2xl: 0 25px 50px -12px oklch(0% 0 0 / 0.6);
}


/* ============================================
   MOTION TOKENS
   ============================================ */

:root {
  /* Duration */
  --duration-instant: 0ms;
  --duration-fast: 150ms;
  --duration-base: 220ms;
  --duration-slow: 300ms;
  --duration-slower: 400ms;
  
  /* Easing Functions */
  --ease-in: cubic-bezier(0.4, 0, 1, 1);
  --ease-out: cubic-bezier(0, 0, 0.2, 1);
  --ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);
  --ease-bounce: cubic-bezier(0.68, -0.55, 0.265, 1.55);
  
  /* Common Transitions */
  --transition-colors: color var(--duration-fast) var(--ease-out),
                       background-color var(--duration-fast) var(--ease-out),
                       border-color var(--duration-fast) var(--ease-out);
  --transition-transform: transform var(--duration-base) var(--ease-out);
  --transition-opacity: opacity var(--duration-base) var(--ease-out);
  --transition-all: all var(--duration-base) var(--ease-in-out);
}

/* Respect Reduced Motion Preference */
@media (prefers-reduced-motion: reduce) {
  :root {
    --duration-instant: 0ms;
    --duration-fast: 0ms;
    --duration-base: 0ms;
    --duration-slow: 0ms;
    --duration-slower: 0ms;
  }
  
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}


/* ============================================
   LAYOUT & CONTAINER
   ============================================ */

:root {
  /* Container widths */
  --container-sm: 640px;
  --container-md: 768px;
  --container-lg: 1024px;
  --container-xl: 1280px;
  --container-2xl: 1536px;
  
  /* Breakpoints (for reference in JS) */
  --breakpoint-sm: 640px;
  --breakpoint-md: 768px;
  --breakpoint-lg: 1024px;
  --breakpoint-xl: 1280px;
  --breakpoint-2xl: 1536px;
  
  /* Z-index scale */
  --z-base: 0;
  --z-dropdown: 1000;
  --z-sticky: 1100;
  --z-fixed: 1200;
  --z-modal-backdrop: 1300;
  --z-modal: 1400;
  --z-popover: 1500;
  --z-tooltip: 1600;
  --z-notification: 1700;
  --z-max: 9999;
}


/* ============================================
   COMPONENT DENSITY
   ============================================ */

:root {
  /* Button heights */
  --button-height-sm: 2.25rem;    /* 36px */
  --button-height-md: 2.75rem;    /* 44px */
  --button-height-lg: 3rem;       /* 48px */
  
  /* Input heights */
  --input-height-sm: 2.25rem;     /* 36px */
  --input-height-md: 2.5rem;      /* 40px */
  --input-height-lg: 3rem;        /* 48px */
  
  /* Icon sizes */
  --icon-xs: 0.75rem;             /* 12px */
  --icon-sm: 1rem;                /* 16px */
  --icon-md: 1.25rem;             /* 20px */
  --icon-lg: 1.5rem;              /* 24px */
  --icon-xl: 2rem;                /* 32px */
  --icon-2xl: 2.5rem;             /* 40px */
  
  /* Avatar sizes */
  --avatar-xs: 1.5rem;            /* 24px */
  --avatar-sm: 2rem;              /* 32px */
  --avatar-md: 2.5rem;            /* 40px */
  --avatar-lg: 3rem;              /* 48px */
  --avatar-xl: 4rem;              /* 64px */
  --avatar-2xl: 6rem;             /* 96px */
}


/* ============================================
   FOCUS & ACCESSIBILITY
   ============================================ */

:root {
  --focus-ring-width: 2px;
  --focus-ring-offset: 2px;
  --focus-ring-color: var(--primary);
}

/* Default focus style */
:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring-color);
  outline-offset: var(--focus-ring-offset);
  border-radius: var(--radius-sm);
}

/* Remove default outline, apply custom */
*:focus {
  outline: none;
}

*:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring-color);
  outline-offset: var(--focus-ring-offset);
}


/* ============================================
   USAGE EXAMPLES
   ============================================ */

/*
Example 1: Button with tokens
.button {
  height: var(--button-height-md);
  padding-inline: var(--spacing-6);
  background-color: var(--primary);
  color: var(--primary-foreground);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  transition: var(--transition-colors);
  box-shadow: var(--shadow-sm);
}

.button:hover {
  background-color: var(--primary-hover);
}

.button:active {
  background-color: var(--primary-active);
  transform: translateY(1px);
}

Example 2: Card with tokens
.card {
  background-color: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: var(--spacing-6);
  box-shadow: var(--shadow-sm);
  transition: var(--transition-all);
}

.card:hover {
  box-shadow: var(--shadow-md);
  border-color: var(--border-strong);
}

Example 3: Typography with tokens
.heading {
  font-size: var(--font-size-3xl);
  line-height: var(--line-height-tight);
  font-weight: var(--font-weight-bold);
  color: var(--text);
  margin-bottom: var(--spacing-4);
}

.paragraph {
  font-size: var(--font-size-base);
  line-height: var(--line-height-relaxed);
  color: var(--text-secondary);
  margin-bottom: var(--spacing-6);
}
*/
