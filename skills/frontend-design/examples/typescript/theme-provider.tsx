/**
 * Theme Provider — Theme Management System
 * 
 * This file provides a complete theme management system with:
 * - Light/dark/system theme support
 * - Theme persistence (localStorage)
 * - System preference detection
 * - Type-safe theme context
 * 
 * Location: {project_path}/skills/frontend-design/examples/typescript/theme-provider.tsx
 * 
 * Usage:
 * ```tsx
 * import { ThemeProvider, useTheme } from './theme-provider';
 * 
 * function App() {
 *   return (
 *     <ThemeProvider defaultTheme="system">
 *       <YourApp />
 *     </ThemeProvider>
 *   );
 * }
 * 
 * function ThemeToggle() {
 *   const { theme, setTheme } = useTheme();
 *   return <button onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}>Toggle</button>;
 * }
 * ```
 */

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { Theme } from './design-tokens';

// ============================================
// Types
// ============================================

interface ThemeProviderProps {
  children: ReactNode;
  defaultTheme?: Theme;
  storageKey?: string;
}

interface ThemeContextType {
  theme: Theme;
  effectiveTheme: 'light' | 'dark'; // Resolved theme (system → light/dark)
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
}

// ============================================
// Context
// ============================================

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

// ============================================
// Provider Component
// ============================================

export function ThemeProvider({
  children,
  defaultTheme = 'system',
  storageKey = 'ui-theme',
}: ThemeProviderProps) {
  const [theme, setThemeState] = useState<Theme>(() => {
    // Load theme from localStorage if available
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem(storageKey);
      if (stored && ['light', 'dark', 'system'].includes(stored)) {
        return stored as Theme;
      }
    }
    return defaultTheme;
  });

  const [effectiveTheme, setEffectiveTheme] = useState<'light' | 'dark'>(() => {
    if (theme === 'system') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    return theme;
  });

  // Update effective theme when theme or system preference changes
  useEffect(() => {
    const root = window.document.documentElement;

    // Remove previous theme classes
    root.classList.remove('light', 'dark');

    if (theme === 'system') {
      const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches
        ? 'dark'
        : 'light';
      root.classList.add(systemTheme);
      root.setAttribute('data-theme', systemTheme);
      setEffectiveTheme(systemTheme);
    } else {
      root.classList.add(theme);
      root.setAttribute('data-theme', theme);
      setEffectiveTheme(theme);
    }
  }, [theme]);

  // Listen for system theme changes when in system mode
  useEffect(() => {
    if (theme !== 'system') return;

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    
    const handleChange = (e: MediaQueryListEvent) => {
      const systemTheme = e.matches ? 'dark' : 'light';
      const root = window.document.documentElement;
      root.classList.remove('light', 'dark');
      root.classList.add(systemTheme);
      root.setAttribute('data-theme', systemTheme);
      setEffectiveTheme(systemTheme);
    };

    // Modern browsers
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    }
    // Legacy browsers
    else if (mediaQuery.addListener) {
      mediaQuery.addListener(handleChange);
      return () => mediaQuery.removeListener(handleChange);
    }
  }, [theme]);

  const setTheme = (newTheme: Theme) => {
    localStorage.setItem(storageKey, newTheme);
    setThemeState(newTheme);
  };

  const toggleTheme = () => {
    setTheme(effectiveTheme === 'light' ? 'dark' : 'light');
  };

  const value: ThemeContextType = {
    theme,
    effectiveTheme,
    setTheme,
    toggleTheme,
  };

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

// ============================================
// Hook
// ============================================

export function useTheme(): ThemeContextType {
  const context = useContext(ThemeContext);
  
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  
  return context;
}

// ============================================
// Theme Toggle Component
// ============================================

interface ThemeToggleProps {
  className?: string;
  iconSize?: number;
}

export function ThemeToggle({ className = '', iconSize = 20 }: ThemeToggleProps) {
  const { theme, effectiveTheme, setTheme } = useTheme();

  return (
    <button
      onClick={() => setTheme(effectiveTheme === 'light' ? 'dark' : 'light')}
      className={`btn btn-ghost btn-icon ${className}`}
      aria-label="Toggle theme"
      title="Toggle theme"
    >
      {effectiveTheme === 'light' ? (
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width={iconSize}
          height={iconSize}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
        </svg>
      ) : (
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width={iconSize}
          height={iconSize}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="12" cy="12" r="5" />
          <line x1="12" y1="1" x2="12" y2="3" />
          <line x1="12" y1="21" x2="12" y2="23" />
          <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
          <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
          <line x1="1" y1="12" x2="3" y2="12" />
          <line x1="21" y1="12" x2="23" y2="12" />
          <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
          <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
        </svg>
      )}
    </button>
  );
}

// ============================================
// Theme Selector Component (Dropdown)
// ============================================

interface ThemeSelectorProps {
  className?: string;
}

export function ThemeSelector({ className = '' }: ThemeSelectorProps) {
  const { theme, setTheme } = useTheme();
  const [isOpen, setIsOpen] = useState(false);

  const themes: { value: Theme; label: string; icon: JSX.Element }[] = [
    {
      value: 'light',
      label: 'Light',
      icon: (
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <circle cx="12" cy="12" r="5" />
          <line x1="12" y1="1" x2="12" y2="3" />
          <line x1="12" y1="21" x2="12" y2="23" />
          <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
          <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
          <line x1="1" y1="12" x2="3" y2="12" />
          <line x1="21" y1="12" x2="23" y2="12" />
          <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
          <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
        </svg>
      ),
    },
    {
      value: 'dark',
      label: 'Dark',
      icon: (
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
        </svg>
      ),
    },
    {
      value: 'system',
      label: 'System',
      icon: (
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <rect x="2" y="3" width="20" height="14" rx="2" />
          <line x1="8" y1="21" x2="16" y2="21" />
          <line x1="12" y1="17" x2="12" y2="21" />
        </svg>
      ),
    },
  ];

  return (
    <div className={`relative ${className}`}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="btn btn-outline flex items-center gap-2"
        aria-label="Select theme"
      >
        {themes.find((t) => t.value === theme)?.icon}
        <span>{themes.find((t) => t.value === theme)?.label}</span>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          className={`transition-transform ${isOpen ? 'rotate-180' : ''}`}
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
            aria-hidden="true"
          />
          <div className="absolute right-0 mt-2 w-48 rounded-md shadow-lg bg-surface border border-border z-50">
            <div className="py-1" role="menu">
              {themes.map((t) => (
                <button
                  key={t.value}
                  onClick={() => {
                    setTheme(t.value);
                    setIsOpen(false);
                  }}
                  className={`
                    w-full flex items-center gap-3 px-4 py-2 text-sm
                    hover:bg-surface-hover transition-colors
                    ${theme === t.value ? 'bg-surface-subtle font-medium' : ''}
                  `}
                  role="menuitem"
                >
                  {t.icon}
                  <span>{t.label}</span>
                  {theme === t.value && (
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      className="ml-auto"
                    >
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  )}
                </button>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ============================================
// Utility: Apply theme class to body
// ============================================

export function useThemeClass() {
  const { effectiveTheme } = useTheme();

  useEffect(() => {
    const root = window.document.documentElement;
    root.classList.remove('light', 'dark');
    root.classList.add(effectiveTheme);
    root.setAttribute('data-theme', effectiveTheme);
  }, [effectiveTheme]);
}

// ============================================
// Higher-Order Component for Theme
// ============================================

export function withTheme<P extends object>(
  Component: React.ComponentType<P & { theme: ThemeContextType }>
) {
  return function ThemedComponent(props: P) {
    const theme = useTheme();
    return <Component {...props} theme={theme} />;
  };
}
