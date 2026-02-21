/**
 * Tailwind CSS Configuration
 * 
 * This configuration integrates the design token system with Tailwind CSS.
 * It provides custom colors, spacing, typography, and more.
 * 
 * Location: {project_path}/skills/frontend-design/templates/tailwind.config.js
 * 
 * Installation:
 * 1. npm install -D tailwindcss postcss autoprefixer
 * 2. Copy this file to your project root as tailwind.config.js
 * 3. Update content paths to match your project structure
 * 4. Import globals.css in your main entry file
 */

/** @type {import('tailwindcss').Config} */
module.exports = {
  // Specify which files Tailwind should scan for class names
  content: [
    './src/**/*.{js,jsx,ts,tsx}',
    './pages/**/*.{js,jsx,ts,tsx}',
    './components/**/*.{js,jsx,ts,tsx}',
    './app/**/*.{js,jsx,ts,tsx}',
  ],

  // Enable dark mode via class strategy
  darkMode: ['class'],

  theme: {
    // Extend default theme (preserves Tailwind defaults)
    extend: {
      // Custom colors using CSS variables for theme support
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
      },

      // Border radius scale
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },

      // Custom font families
      fontFamily: {
        sans: ['var(--font-sans)', 'system-ui', 'sans-serif'],
        serif: ['var(--font-serif)', 'Georgia', 'serif'],
        mono: ['var(--font-mono)', 'monospace'],
      },

      // Typography scale using fluid sizing
      fontSize: {
        xs: ['clamp(0.75rem, 0.7rem + 0.15vw, 0.875rem)', { lineHeight: '1.4' }],
        sm: ['clamp(0.875rem, 0.8rem + 0.2vw, 1rem)', { lineHeight: '1.5' }],
        base: ['clamp(1rem, 0.95rem + 0.25vw, 1.125rem)', { lineHeight: '1.6' }],
        lg: ['clamp(1.125rem, 1.05rem + 0.3vw, 1.25rem)', { lineHeight: '1.5' }],
        xl: ['clamp(1.25rem, 1.15rem + 0.4vw, 1.5rem)', { lineHeight: '1.4' }],
        '2xl': ['clamp(1.5rem, 1.35rem + 0.6vw, 2rem)', { lineHeight: '1.3' }],
        '3xl': ['clamp(1.875rem, 1.65rem + 0.9vw, 2.5rem)', { lineHeight: '1.2' }],
        '4xl': ['clamp(2.25rem, 1.95rem + 1.2vw, 3.5rem)', { lineHeight: '1.1' }],
        '5xl': ['clamp(3rem, 2.5rem + 2vw, 4.5rem)', { lineHeight: '1' }],
      },

      // Spacing scale (8px base system)
      spacing: {
        0.5: '0.125rem',    // 2px
        1.5: '0.375rem',    // 6px
        2.5: '0.625rem',    // 10px
        3.5: '0.875rem',    // 14px
        4.5: '1.125rem',    // 18px
        5.5: '1.375rem',    // 22px
        6.5: '1.625rem',    // 26px
        7.5: '1.875rem',    // 30px
        8.5: '2.125rem',    // 34px
        9.5: '2.375rem',    // 38px
        13: '3.25rem',      // 52px
        15: '3.75rem',      // 60px
        17: '4.25rem',      // 68px
        18: '4.5rem',       // 72px
        19: '4.75rem',      // 76px
        21: '5.25rem',      // 84px
        22: '5.5rem',       // 88px
        23: '5.75rem',      // 92px
        25: '6.25rem',      // 100px
      },

      // Custom shadows
      boxShadow: {
        sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
        DEFAULT: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
        md: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
        lg: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
        xl: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
        '2xl': '0 25px 50px -12px rgb(0 0 0 / 0.25)',
        inner: 'inset 0 2px 4px 0 rgb(0 0 0 / 0.05)',
      },

      // Animation durations
      transitionDuration: {
        DEFAULT: '220ms',
        fast: '150ms',
        slow: '300ms',
      },

      // Keyframe animations
      keyframes: {
        // Fade in animation
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        // Fade out animation
        'fade-out': {
          '0%': { opacity: '1' },
          '100%': { opacity: '0' },
        },
        // Slide in from top
        'slide-in-top': {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(0)' },
        },
        // Slide in from bottom
        'slide-in-bottom': {
          '0%': { transform: 'translateY(100%)' },
          '100%': { transform: 'translateY(0)' },
        },
        // Slide in from left
        'slide-in-left': {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(0)' },
        },
        // Slide in from right
        'slide-in-right': {
          '0%': { transform: 'translateX(100%)' },
          '100%': { transform: 'translateX(0)' },
        },
        // Scale in
        'scale-in': {
          '0%': { transform: 'scale(0.95)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
        // Spin animation
        spin: {
          '0%': { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
        // Shimmer animation (for skeletons)
        shimmer: {
          '0%': { backgroundPosition: '200% 0' },
          '100%': { backgroundPosition: '-200% 0' },
        },
        // Pulse animation
        pulse: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.5' },
        },
        // Bounce animation
        bounce: {
          '0%, 100%': { transform: 'translateY(-25%)', animationTimingFunction: 'cubic-bezier(0.8,0,1,1)' },
          '50%': { transform: 'translateY(0)', animationTimingFunction: 'cubic-bezier(0,0,0.2,1)' },
        },
      },

      // Animation utilities
      animation: {
        'fade-in': 'fade-in 0.2s ease-out',
        'fade-out': 'fade-out 0.2s ease-out',
        'slide-in-top': 'slide-in-top 0.3s ease-out',
        'slide-in-bottom': 'slide-in-bottom 0.3s ease-out',
        'slide-in-left': 'slide-in-left 0.3s ease-out',
        'slide-in-right': 'slide-in-right 0.3s ease-out',
        'scale-in': 'scale-in 0.2s ease-out',
        spin: 'spin 0.6s linear infinite',
        shimmer: 'shimmer 1.5s ease-in-out infinite',
        pulse: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        bounce: 'bounce 1s infinite',
      },

      // Custom z-index scale
      zIndex: {
        dropdown: '1000',
        sticky: '1100',
        fixed: '1200',
        'modal-backdrop': '1300',
        modal: '1400',
        popover: '1500',
        tooltip: '1600',
      },
    },
  },

  // Plugins
  plugins: [
    // Typography plugin for prose styling
    require('@tailwindcss/typography'),
    
    // Forms plugin for better form styling
    require('@tailwindcss/forms'),
    
    // Custom plugin for component utilities
    function ({ addComponents, theme }) {
      addComponents({
        // Container utility
        '.container': {
          width: '100%',
          marginLeft: 'auto',
          marginRight: 'auto',
          paddingLeft: theme('spacing.4'),
          paddingRight: theme('spacing.4'),
          '@screen sm': {
            maxWidth: '640px',
          },
          '@screen md': {
            maxWidth: '768px',
          },
          '@screen lg': {
            maxWidth: '1024px',
            paddingLeft: theme('spacing.6'),
            paddingRight: theme('spacing.6'),
          },
          '@screen xl': {
            maxWidth: '1280px',
          },
          '@screen 2xl': {
            maxWidth: '1536px',
          },
        },
      });
    },
  ],
};
