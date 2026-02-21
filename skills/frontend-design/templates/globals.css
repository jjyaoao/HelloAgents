/**
 * Global Styles
 * 
 * This file provides base styles, resets, and CSS custom properties
 * for the design system.
 * 
 * Location: {project_path}/skills/frontend-design/templates/globals.css
 * 
 * Import this file in your main entry point:
 * - React: import './globals.css' in index.tsx or App.tsx
 * - Next.js: import './globals.css' in pages/_app.tsx or app/layout.tsx
 */

@tailwind base;
@tailwind components;
@tailwind utilities;

/* ============================================
   BASE LAYER - CSS Custom Properties
   ============================================ */

@layer base {
  /* Root CSS Variables - Light Mode (Default) */
  :root {
    /* Background & Surfaces */
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --card: 0 0% 100%;
    --card-foreground: 222.2 84% 4.9%;
    --popover: 0 0% 100%;
    --popover-foreground: 222.2 84% 4.9%;
    
    /* Primary Brand */
    --primary: 222.2 47.4% 11.2%;
    --primary-foreground: 210 40% 98%;
    
    /* Secondary */
    --secondary: 210 40% 96.1%;
    --secondary-foreground: 222.2 47.4% 11.2%;
    
    /* Muted */
    --muted: 210 40% 96.1%;
    --muted-foreground: 215.4 16.3% 46.9%;
    
    /* Accent */
    --accent: 210 40% 96.1%;
    --accent-foreground: 222.2 47.4% 11.2%;
    
    /* Destructive/Danger */
    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 210 40% 98%;
    
    /* Borders */
    --border: 214.3 31.8% 91.4%;
    --input: 214.3 31.8% 91.4%;
    --ring: 222.2 84% 4.9%;
    
    /* Misc */
    --radius: 0.5rem;
  }

  /* Dark Mode Overrides */
  .dark {
    --background: 222.2 84% 4.9%;
    --foreground: 210 40% 98%;
    --card: 222.2 84% 4.9%;
    --card-foreground: 210 40% 98%;
    --popover: 222.2 84% 4.9%;
    --popover-foreground: 210 40% 98%;
    
    --primary: 210 40% 98%;
    --primary-foreground: 222.2 47.4% 11.2%;
    
    --secondary: 217.2 32.6% 17.5%;
    --secondary-foreground: 210 40% 98%;
    
    --muted: 217.2 32.6% 17.5%;
    --muted-foreground: 215 20.2% 65.1%;
    
    --accent: 217.2 32.6% 17.5%;
    --accent-foreground: 210 40% 98%;
    
    --destructive: 0 62.8% 30.6%;
    --destructive-foreground: 210 40% 98%;
    
    --border: 217.2 32.6% 17.5%;
    --input: 217.2 32.6% 17.5%;
    --ring: 212.7 26.8% 83.9%;
  }

  /* Base Element Styles */
  * {
    @apply border-border;
  }

  body {
    @apply bg-background text-foreground;
    font-feature-settings: "rlig" 1, "calt" 1;
  }

  /* Typography Defaults */
  h1, h2, h3, h4, h5, h6 {
    @apply font-semibold;
  }

  /* Focus Visible Styles */
  *:focus-visible {
    @apply outline-none ring-2 ring-ring ring-offset-2;
  }

  /* Smooth Scrolling */
  html {
    scroll-behavior: smooth;
  }

  /* Reduced Motion Preference */
  @media (prefers-reduced-motion: reduce) {
    html {
      scroll-behavior: auto;
    }
    
    *,
    *::before,
    *::after {
      animation-duration: 0.01ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: 0.01ms !important;
      scroll-behavior: auto !important;
    }
  }

  /* Custom Scrollbar Styles (Webkit) */
  ::-webkit-scrollbar {
    width: 10px;
    height: 10px;
  }

  ::-webkit-scrollbar-track {
    @apply bg-muted;
  }

  ::-webkit-scrollbar-thumb {
    @apply bg-muted-foreground/30 rounded-md;
  }

  ::-webkit-scrollbar-thumb:hover {
    @apply bg-muted-foreground/50;
  }

  /* Firefox Scrollbar */
  * {
    scrollbar-width: thin;
    scrollbar-color: hsl(var(--muted-foreground) / 0.3) hsl(var(--muted));
  }

  /* Selection Color */
  ::selection {
    @apply bg-primary/20 text-foreground;
  }
}

/* ============================================
   COMPONENTS LAYER - Reusable Components
   ============================================ */

@layer components {
  /* Container */
  .container {
    @apply w-full mx-auto px-4 sm:px-6 lg:px-8;
    max-width: 1536px;
  }

  /* Button Base */
  .btn {
    @apply inline-flex items-center justify-center gap-2 rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50;
    height: 2.5rem;
    padding: 0 1rem;
  }

  .btn-sm {
    height: 2rem;
    padding: 0 0.75rem;
    font-size: 0.875rem;
  }

  .btn-lg {
    height: 3rem;
    padding: 0 1.5rem;
  }

  /* Button Variants */
  .btn-primary {
    @apply bg-primary text-primary-foreground hover:bg-primary/90;
  }

  .btn-secondary {
    @apply bg-secondary text-secondary-foreground hover:bg-secondary/80;
  }

  .btn-outline {
    @apply border border-input bg-background hover:bg-accent hover:text-accent-foreground;
  }

  .btn-ghost {
    @apply hover:bg-accent hover:text-accent-foreground;
  }

  .btn-destructive {
    @apply bg-destructive text-destructive-foreground hover:bg-destructive/90;
  }

  /* Input */
  .input {
    @apply flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50;
  }

  /* Card */
  .card {
    @apply rounded-lg border bg-card text-card-foreground shadow-sm;
  }

  .card-header {
    @apply flex flex-col space-y-1.5 p-6;
  }

  .card-title {
    @apply text-2xl font-semibold leading-none tracking-tight;
  }

  .card-description {
    @apply text-sm text-muted-foreground;
  }

  .card-content {
    @apply p-6 pt-0;
  }

  .card-footer {
    @apply flex items-center p-6 pt-0;
  }

  /* Badge */
  .badge {
    @apply inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2;
  }

  .badge-primary {
    @apply border-transparent bg-primary text-primary-foreground hover:bg-primary/80;
  }

  .badge-secondary {
    @apply border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80;
  }

  .badge-outline {
    @apply text-foreground;
  }

  /* Alert */
  .alert {
    @apply relative w-full rounded-lg border p-4;
  }

  .alert-destructive {
    @apply border-destructive/50 text-destructive dark:border-destructive [&>svg]:text-destructive;
  }
}

/* ============================================
   UTILITIES LAYER - Custom Utilities
   ============================================ */

@layer utilities {
  /* Text Balance - Prevents orphans */
  .text-balance {
    text-wrap: balance;
  }

  /* Truncate with multiple lines */
  .line-clamp-2 {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .line-clamp-3 {
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  /* Hide scrollbar but keep functionality */
  .scrollbar-hide {
    -ms-overflow-style: none;
    scrollbar-width: none;
  }

  .scrollbar-hide::-webkit-scrollbar {
    display: none;
  }

  /* Animate on scroll utilities */
  .animate-on-scroll {
    opacity: 0;
    transform: translateY(20px);
    transition: opacity 0.6s ease-out, transform 0.6s ease-out;
  }

  .animate-on-scroll.in-view {
    opacity: 1;
    transform: translateY(0);
  }

  /* Glassmorphism effect */
  .glass {
    @apply bg-background/80 backdrop-blur-md border border-border/50;
  }

  /* Gradient text */
  .gradient-text {
    @apply bg-clip-text text-transparent bg-gradient-to-r from-primary to-accent;
  }

  /* Focus ring utilities */
  .focus-ring {
    @apply focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2;
  }

  /* Aspect ratio utilities (if not using @tailwindcss/aspect-ratio) */
  .aspect-video {
    aspect-ratio: 16 / 9;
  }

  .aspect-square {
    aspect-ratio: 1 / 1;
  }

  /* Safe area insets (for mobile) */
  .safe-top {
    padding-top: env(safe-area-inset-top);
  }

  .safe-bottom {
    padding-bottom: env(safe-area-inset-bottom);
  }

  .safe-left {
    padding-left: env(safe-area-inset-left);
  }

  .safe-right {
    padding-right: env(safe-area-inset-right);
  }
}

/* ============================================
   PRINT STYLES
   ============================================ */

@media print {
  /* Hide unnecessary elements when printing */
  nav, footer, .no-print {
    display: none !important;
  }

  /* Optimize for printing */
  body {
    @apply text-black bg-white;
  }

  a {
    @apply text-black no-underline;
  }

  /* Page breaks */
  h1, h2, h3, h4, h5, h6 {
    page-break-after: avoid;
  }

  img, table, figure {
    page-break-inside: avoid;
  }
}
