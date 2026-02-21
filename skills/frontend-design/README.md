# Frontend Design Skill

A comprehensive skill for transforming UI style requirements into production-ready frontend code with systematic design tokens, accessibility compliance, and creative execution.

## 📦 Skill Location

```
{project_path}/skills/frontend-design/
```

## 📚 What's Included

### Documentation
- **SKILL.md** - Complete methodology and guidelines for frontend development
- **README.md** - This file (quick start and overview)
- **LICENSE** - MIT License

### CSS Examples (`examples/css/`)
- **tokens.css** - Complete design token system with semantic colors, typography, spacing, radius, shadows, and motion tokens
- **components.css** - Production-ready component styles (buttons, inputs, cards, modals, alerts, etc.)
- **utilities.css** - Utility classes for layout, typography, states, and responsive design

### TypeScript Examples (`examples/typescript/`)
- **design-tokens.ts** - Type-safe token definitions and utilities
- **theme-provider.tsx** - Complete theme management system (light/dark/system modes)
- **sample-components.tsx** - Production React components with full TypeScript support
- **utils.ts** - Utility functions for frontend development

### Templates (`templates/`)
- **tailwind.config.js** - Optimized Tailwind CSS configuration
- **globals.css** - Global styles and CSS custom properties

## 🚀 Quick Start

### When to Use This Skill

Use this skill when:
- Building websites, web applications, or web components
- User mentions design styles: "modern", "premium", "minimalist", "dark mode"
- Creating dashboards, landing pages, or any web UI
- User asks to "make it look better" or "improve the design"
- User specifies frameworks: React, Vue, Svelte, Next.js, etc.

### Basic Usage

1. **Read SKILL.md** first for complete methodology
2. **Choose a design direction** (Minimal SaaS, Bold Editorial, Soft & Organic, Dark Neon, Playful)
3. **Generate design tokens** using the token system
4. **Build components** using the provided examples
5. **Compose pages** from components
6. **Review & validate** against the checklist

### Installation

```bash
# Install dependencies
npm install -D tailwindcss postcss autoprefixer
npm install clsx tailwind-merge

# Initialize Tailwind
npx tailwindcss init -p

# Copy templates
cp templates/tailwind.config.js ./tailwind.config.js
cp templates/globals.css ./src/globals.css

# Import in your app
# React: import './globals.css' in main entry
# Next.js: import './globals.css' in _app.tsx or layout.tsx
```

## 🎨 Design Tokens System

All visual properties derive from semantic tokens:

### Colors
```css
--background, --surface, --text
--primary, --secondary, --accent
--success, --warning, --danger, --info
```

### Typography
```css
--font-size-{xs, sm, base, lg, xl, 2xl, 3xl, 4xl, 5xl}
--line-height-{tight, snug, normal, relaxed, loose}
--font-weight-{light, normal, medium, semibold, bold}
```

### Spacing (8px system)
```css
--spacing-{0.5, 1, 2, 3, 4, 6, 8, 10, 12, 16, 20, 24, 32, 40, 48}
```

### Radius
```css
--radius-{xs, sm, md, lg, xl, 2xl, 3xl, full}
```

## 📖 Example Usage

### React Component with Tokens

```tsx
import { Button, Card, Input } from './examples/typescript/sample-components';
import { ThemeProvider } from './examples/typescript/theme-provider';

function App() {
  return (
    <ThemeProvider defaultTheme="system">
      <Card>
        <Card.Header>
          <Card.Title>Sign Up</Card.Title>
          <Card.Description>Create your account</Card.Description>
        </Card.Header>
        <Card.Body>
          <Input
            label="Email"
            type="email"
            placeholder="you@example.com"
            required
          />
          <Input
            label="Password"
            type="password"
            placeholder="••••••••"
            required
          />
        </Card.Body>
        <Card.Footer>
          <Button variant="primary">Create Account</Button>
        </Card.Footer>
      </Card>
    </ThemeProvider>
  );
}
```

### CSS-Only Approach

```css
@import './examples/css/tokens.css';
@import './examples/css/components.css';
```

```html
<div class="card">
  <div class="card-header">
    <h3 class="card-title">Sign Up</h3>
    <p class="card-description">Create your account</p>
  </div>
  <div class="card-body">
    <div class="form-group">
      <label class="label">Email</label>
      <input type="email" class="input" placeholder="you@example.com" />
    </div>
  </div>
  <div class="card-footer">
    <button class="btn btn-primary">Create Account</button>
  </div>
</div>
```

## ✨ Features

### ✅ Systematic Design
- Token-first methodology
- Consistent spacing (8px system)
- Predictable visual hierarchy
- Maintainable codebase

### ✅ Accessibility
- WCAG AA compliance (minimum)
- Keyboard navigation
- Screen reader support
- Focus management
- Proper ARIA labels

### ✅ Responsive Design
- Mobile-first approach
- Fluid typography
- Flexible layouts
- Touch-friendly (44px+ targets)

### ✅ Dark Mode
- Built-in theme system
- CSS custom properties
- System preference detection
- Persistent user choice

### ✅ Production Ready
- TypeScript support
- Full type safety
- Optimized bundle size
- Tree-shaking enabled

## 📋 Component States

All components include:
- **Default** - Base appearance
- **Hover** - Visual feedback
- **Active** - Pressed state
- **Focus** - Keyboard indicator
- **Disabled** - Inactive state
- **Loading** - Skeleton/spinner
- **Empty** - No data state
- **Error** - Error recovery

## 🎯 Best Practices

1. **Always start with tokens** - Never skip to components
2. **Use semantic colors** - No hardcoded hex values
3. **Mobile-first** - Design for 375px, enhance upward
4. **Accessibility first** - Build it in, not on
5. **Test all states** - Default, hover, focus, disabled, loading, error
6. **DRY principles** - Reusable components over duplicated code

## 🔧 Customization

### Extend Design Tokens

```typescript
import { lightThemeTokens, mergeTokens } from './examples/typescript/design-tokens';

const customTokens = mergeTokens(lightThemeTokens, {
  colors: {
    primary: 'oklch(60% 0.20 280)', // Custom purple
    // ... other overrides
  },
});
```

### Add Custom Components

Follow the patterns in `examples/typescript/sample-components.tsx`:
1. Define TypeScript interfaces
2. Implement with token-based styling
3. Include all states
4. Add accessibility features
5. Document usage

## 📚 Documentation Structure

```
frontend-design/
├── SKILL.md                          # Complete methodology (READ THIS FIRST)
├── README.md                         # Quick start guide (this file)
├── LICENSE                           # MIT License
├── examples/
│   ├── css/
│   │   ├── tokens.css               # Design token system
│   │   ├── components.css           # Component styles
│   │   └── utilities.css            # Utility classes
│   └── typescript/
│       ├── design-tokens.ts         # Type-safe tokens
│       ├── theme-provider.tsx       # Theme management
│       ├── sample-components.tsx    # React components
│       └── utils.ts                 # Utility functions
└── templates/
    ├── tailwind.config.js           # Tailwind configuration
    └── globals.css                  # Global styles
```

## 🤝 Contributing

This skill is maintained as part of the z-ai platform. To suggest improvements:
1. Review the existing patterns
2. Propose changes that enhance consistency
3. Ensure all examples remain production-ready
4. Update documentation accordingly

## 📄 License

MIT License - see LICENSE file for details

## 🔗 Resources

- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [WCAG Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [shadcn/ui](https://ui.shadcn.com)
- [TypeScript](https://www.typescriptlang.org)

---

**Version**: 2.0.0  
**Last Updated**: December 2024  
**Maintained by**: z-ai platform team
