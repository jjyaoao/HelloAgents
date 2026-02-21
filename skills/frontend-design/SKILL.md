---
name: frontend-design
description: Transform UI style requirements into production-ready frontend code with systematic design tokens, accessibility compliance, and creative execution. Use when building websites, web applications, React/Vue components, dashboards, landing pages, or any web UI requiring both design consistency and aesthetic quality.
version: 2.0.0
license: MIT
---

# Frontend Design Skill — Systematic & Creative Web Development

**Skill Location**: `{project_path}/skills/frontend-design/`

This skill transforms vague UI style requirements into executable, production-grade frontend code through a systematic design token approach while maintaining creative excellence. It ensures visual consistency, accessibility compliance, and maintainability across all deliverables.

---

## When to Use This Skill (Trigger Patterns)

**MUST apply this skill when:**

- User requests any website, web application, or web component development
- User mentions design styles: "modern", "premium", "minimalist", "dark mode", "SaaS-style"
- Building dashboards, landing pages, admin panels, or any web UI
- User asks to "make it look better" or "improve the design"
- Creating component libraries or design systems
- User specifies frameworks: React, Vue, Svelte, Next.js, Nuxt, etc.
- Converting designs/mockups to code
- User mentions: Tailwind CSS, shadcn/ui, Material-UI, Chakra UI, etc.

**Trigger phrases:**
- "build a website/app/component"
- "create a dashboard/landing page"
- "design a UI for..."
- "make it modern/clean/premium"
- "style this with..."
- "convert this design to code"

**DO NOT use for:**
- Backend API development
- Pure logic/algorithm implementation
- Non-visual code tasks

---

## Skill Architecture

This skill provides:

1. **SKILL.md** (this file): Core methodology and guidelines
2. **examples/css/**: Production-ready CSS examples
   - `tokens.css` - Design token system
   - `components.css` - Reusable component styles
   - `utilities.css` - Utility classes
3. **examples/typescript/**: TypeScript implementation examples
   - `design-tokens.ts` - Type-safe token definitions
   - `theme-provider.tsx` - Theme management
   - `sample-components.tsx` - Component examples
4. **templates/**: Quick-start templates
   - `tailwind-config.js` - Tailwind configuration
   - `globals.css` - Global styles template

---

## Core Principles (Non-Negotiable)

### 1. **Dual-Mode Thinking: System + Creativity**

**Systematic Foundation:**
- Design tokens first, UI components second
- No arbitrary hardcoded values (colors, spacing, shadows, radius)
- Consistent scales for typography, spacing, radius, elevation
- Complete state coverage (default/hover/active/focus/disabled + loading/empty/error)
- Accessibility as a constraint, not an afterthought

**Creative Execution:**
- AVOID generic "AI slop" aesthetics (Inter/Roboto fonts, purple gradients, cookie-cutter layouts)
- Choose BOLD aesthetic direction: brutalist, retro-futuristic, luxury, playful, editorial, etc.
- Make unexpected choices in typography, color, layout, and motion
- Each design should feel unique and intentionally crafted for its context

### 2. **Tokens-First Methodology**

```
Design Tokens → Component Styles → Page Layouts → Interactive States
```

**Never skip token definition.** All visual properties must derive from the token system.

### 3. **Tech Stack Flexibility**

**Default stack (if unspecified):**
- Framework: React + TypeScript
- Styling: Tailwind CSS
- Components: shadcn/ui
- Theme: CSS custom properties (light/dark modes)

**Supported alternatives:**
- Frameworks: Vue, Svelte, Angular, vanilla HTML/CSS
- Styling: CSS Modules, SCSS, Styled Components, Emotion
- Libraries: MUI, Ant Design, Chakra UI, Headless UI

### 4. **Tailwind CSS Best Practices**

**⚠️ CRITICAL: Never use Tailwind via CDN**

**MUST use build-time integration:**
```bash
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

**Why build-time is mandatory:**
- ✅ Enables tree-shaking (2-15KB vs 400KB+ bundle)
- ✅ Full design token customization
- ✅ IDE autocomplete and type safety
- ✅ Integrates with bundlers (Vite, webpack, Next.js)

**CDN only acceptable for:**
- Quick prototypes/demos
- Internal testing

---

## Implementation Workflow

### Phase 1: Design Analysis & Token Definition

**Step 1: Understand Context**
```
- Purpose: What problem does this solve? Who uses it?
- Aesthetic Direction: Choose ONE bold direction
- Technical Constraints: Framework, performance, accessibility needs
- Differentiation: What makes this memorable?
```

**Step 2: Generate Design Tokens**

Create comprehensive token system (see `examples/css/tokens.css` and `examples/typescript/design-tokens.ts`):

1. **Semantic Color Slots** (light + dark modes):
   ```
   --background, --surface, --surface-subtle
   --text, --text-secondary, --text-muted
   --border, --border-subtle
   --primary, --primary-hover, --primary-active, --primary-foreground
   --secondary, --secondary-hover, --secondary-foreground
   --accent, --success, --warning, --danger
   ```

2. **Typography Scale**:
   ```
   Display: 3.5rem/4rem (56px/64px), weight 700-800
   H1: 2.5rem/3rem (40px/48px), weight 700
   H2: 2rem/2.5rem (32px/40px), weight 600
   H3: 1.5rem/2rem (24px/32px), weight 600
   Body: 1rem/1.5rem (16px/24px), weight 400
   Small: 0.875rem/1.25rem (14px/20px), weight 400
   Caption: 0.75rem/1rem (12px/16px), weight 400
   ```

3. **Spacing Scale** (8px system):
   ```
   0.5 → 4px, 1 → 8px, 2 → 16px, 3 → 24px, 4 → 32px
   5 → 40px, 6 → 48px, 8 → 64px, 12 → 96px, 16 → 128px
   ```

4. **Radius Scale**:
   ```
   xs: 2px (badges, tags)
   sm: 4px (buttons, inputs)
   md: 6px (cards, modals)
   lg: 8px (large cards, panels)
   xl: 12px (hero sections)
   2xl: 16px (special elements)
   full: 9999px (pills, avatars)
   ```

5. **Shadow Scale**:
   ```
   sm: Subtle lift (buttons, inputs)
   md: Card elevation
   lg: Modals, dropdowns
   xl: Large modals, drawers
   ```

6. **Motion Tokens**:
   ```
   Duration: 150ms (micro), 220ms (default), 300ms (complex)
   Easing: ease-out (enter), ease-in (exit), ease-in-out (transition)
   ```

### Phase 2: Component Development

**Step 3: Build Reusable Components**

Follow this structure (see `examples/typescript/sample-components.tsx`):

```typescript
interface ComponentProps {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  state?: 'default' | 'hover' | 'active' | 'disabled' | 'loading';
}
```

**Required component states:**
- Default, Hover, Active, Focus, Disabled
- Loading (skeleton/spinner)
- Empty state (clear messaging)
- Error state (recovery instructions)

**Required component features:**
- Accessible (ARIA labels, keyboard navigation)
- Responsive (mobile-first)
- Theme-aware (light/dark mode)
- Token-based styling (no hardcoded values)

### Phase 3: Page Assembly

**Step 4: Compose Pages from Components**

```
- Use established tokens and components only
- Mobile-first responsive design
- Loading states for async content
- Empty states with clear CTAs
- Error states with recovery options
```

### Phase 4: Quality Assurance

**Step 5: Self-Review Checklist**

- [ ] All colors from semantic tokens (no random hex/rgb)
- [ ] All spacing from spacing scale
- [ ] All radius from radius scale
- [ ] Shadows justified by hierarchy
- [ ] Clear type hierarchy with comfortable line-height (1.5+)
- [ ] All interactive states implemented and tested
- [ ] Accessibility: WCAG AA contrast, keyboard navigation, ARIA, focus indicators
- [ ] Responsive: works on mobile (375px), tablet (768px), desktop (1024px+)
- [ ] Loading/empty/error states included
- [ ] Code is maintainable: DRY, clear naming, documented

---

## Design Direction Templates

### 1. Minimal Premium SaaS (Most Universal)

```
Visual Style: Minimal Premium SaaS
- Generous whitespace (1.5-2x standard padding)
- Near-white background with subtle surface contrast
- Light borders (1px, low-opacity)
- Very subtle elevation (avoid heavy shadows)
- Unified control height: 44-48px
- Medium-large radius: 6-8px
- Gentle hover states (background shift only)
- Clear but not harsh focus rings
- Low-contrast dividers
- Priority: Readability and consistency
```

**Best for:** Enterprise apps, B2B SaaS, productivity tools

### 2. Bold Editorial

```
Visual Style: Bold Editorial
- Strong typographic hierarchy (large display fonts)
- High contrast (black/white or dark/light extremes)
- Generous use of negative space
- Asymmetric layouts with intentional imbalance
- Grid-breaking elements
- Minimal color palette (1-2 accent colors max)
- Sharp, geometric shapes
- Dramatic scale differences
- Priority: Visual impact and memorability
```

**Best for:** Marketing sites, portfolios, content-heavy sites

### 3. Soft & Organic

```
Visual Style: Soft & Organic
- Rounded corners everywhere (12-24px radius)
- Soft shadows and subtle gradients
- Pastel or muted color palette
- Gentle animations (ease-in-out, 300-400ms)
- Curved elements and flowing layouts
- Generous padding (1.5-2x standard)
- Soft, blurred backgrounds
- Priority: Approachability and comfort
```

**Best for:** Consumer apps, wellness, lifestyle brands

### 4. Dark Neon (Restrained)

```
Visual Style: Dark Neon
- Dark background (#0a0a0a to #1a1a1a, NOT pure black)
- High contrast text (#ffffff or #fafafa)
- Accent colors ONLY for CTAs and key states
- Subtle glow on hover (box-shadow with accent color)
- Minimal borders (use subtle outlines)
- Optional: Subtle noise texture
- Restrained use of neon (less is more)
- Priority: Focus and sophisticated edge
```

**Best for:** Developer tools, gaming, tech products

### 5. Playful & Colorful

```
Visual Style: Playful & Colorful
- Vibrant color palette (3-5 colors)
- Rounded corners (8-16px)
- Micro-animations on hover/interaction
- Generous padding and breathing room
- Friendly, geometric illustrations
- Smooth transitions (200-250ms)
- High energy but balanced
- Priority: Delight and engagement
```

**Best for:** Consumer apps, children's products, creative tools

---

## Standard Prompting Workflow

### Master Prompt Template

```
You are a Design Systems Engineer + Senior Frontend UI Developer with expertise in creative design execution.

[TECH STACK]
- Framework: {{FRAMEWORK = React + TypeScript}}
- Styling: {{STYLING = Tailwind CSS}}
- Components: {{UI_LIB = shadcn/ui}}
- Theme: CSS variables (light/dark modes)

[DESIGN SYSTEM RULES - MANDATORY]
1. Layout: 8px spacing system; mobile-first responsive
2. Typography: Clear hierarchy (Display/H1/H2/H3/Body/Small/Caption); line-height 1.5+
3. Colors: Semantic tokens ONLY (no hardcoded values)
4. Shape: Tiered radius system; tap targets ≥ 44px
5. Elevation: Minimal shadows; borders for hierarchy
6. Motion: Subtle transitions (150-220ms); restrained animations
7. Accessibility: WCAG AA; keyboard navigation; ARIA; focus indicators

[AESTHETIC DIRECTION]
Style: {{STYLE = Minimal Premium SaaS}}
Key Differentiator: {{UNIQUE_FEATURE}}
Target Audience: {{AUDIENCE}}

[INTERACTION STATES - REQUIRED]
✓ Default, Hover, Active, Focus, Disabled
✓ Loading (skeleton), Empty (with messaging), Error (with recovery)

[OUTPUT REQUIREMENTS]
1. Design Tokens (CSS variables + TypeScript types)
2. Component implementations (copy-paste ready)
3. Page layouts with all states
4. NO hardcoded values; reference tokens only
5. Minimal but clear code comments
```

### Token Generation Prompt

```
Generate a complete Design Token system including:

1. Semantic color slots (CSS custom properties):
   - Light mode + Dark mode variants
   - Background, surface, text, border, primary, secondary, accent, semantic colors
   - Interactive states for each (hover, active)

2. Typography scale:
   - Display, H1-H6, Body, Small, Caption, Monospace
   - Include: font-size, line-height, font-weight, letter-spacing

3. Spacing scale (8px base):
   - 0.5, 1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24 (in rem)

4. Radius scale:
   - xs (2px), sm (4px), md (6px), lg (8px), xl (12px), 2xl (16px), full

5. Shadow scale:
   - sm, md, lg, xl (with color and blur values)
   - Usage guidelines for each tier

6. Motion tokens:
   - Duration: fast (150ms), base (220ms), slow (300ms)
   - Easing: ease-out, ease-in, ease-in-out

7. Component density:
   - Button heights: sm (36px), md (44px), lg (48px)
   - Input heights: sm (36px), md (40px)
   - Padding scales

Output format:
- CSS custom properties (globals.css)
- Tailwind config integration
- TypeScript type definitions
- Usage examples for each token category

DO NOT write component code yet.
```

### Component Implementation Prompt

```
Using the established Design Tokens, implement: <{{COMPONENT_NAME}} />

Requirements:
- Props: variant, size, state, className (for composition)
- States: default, hover, focus, active, disabled, loading, error
- Accessibility: keyboard navigation, ARIA labels, focus management
- Responsive: mobile-first, touch-friendly (44px+ tap targets)
- Styling: Use tokens ONLY (no hardcoded values)
- TypeScript: Full type safety with exported interfaces

Include:
1. Component implementation
2. Usage examples (3-5 variants)
3. Loading state example
4. Error state example
5. Accessibility notes

Output: Production-ready, copy-paste code with JSDoc comments.
```

### Page Development Prompt

```
Build page: {{PAGE_NAME}}

Using:
- Established Design Tokens
- Implemented Components
- {{STYLE}} aesthetic direction

Requirements:
- Responsive layout (mobile/tablet/desktop)
- All interaction states (hover/focus/active/disabled)
- Loading skeleton for async content
- Empty state with clear CTA
- Error state with recovery options
- Accessible (keyboard nav, ARIA, WCAG AA)
- No hardcoded styles (components + utility classes only)

Include:
1. Page component with mock data
2. Loading state variant
3. Empty state variant
4. Error state variant
5. Responsive behavior notes

Output: Complete, runnable page component.
```

### Review & Optimization Prompt

```
You are a Frontend Code Reviewer specializing in design systems and accessibility.

Review the implementation and check:

1. Token Compliance:
   - Any hardcoded colors, sizes, shadows, radius?
   - All values from established scales?

2. Typography:
   - Clear hierarchy?
   - Comfortable line-height (1.5+)?
   - Appropriate font sizes for each level?

3. Spacing & Layout:
   - Consistent use of spacing scale?
   - Adequate whitespace?
   - No awkward gaps or cramped sections?

4. Interactive States:
   - Hover/focus/active clearly distinct?
   - Disabled state obviously different?
   - Loading/empty/error states implemented?

5. Accessibility:
   - WCAG AA contrast met?
   - Keyboard reachable?
   - ARIA labels complete?
   - Focus indicators visible?
   - Semantic HTML?

6. Responsive Design:
   - Mobile layout functional (375px)?
   - Tablet optimized (768px)?
   - Desktop enhanced (1024px+)?
   - Touch targets ≥ 44px?

7. Maintainability:
   - DRY principles followed?
   - Clear component boundaries?
   - Consistent naming?
   - Adequate comments?

8. Creative Execution:
   - Matches intended aesthetic?
   - Avoids generic patterns?
   - Unique and memorable?

Output:
- Findings (sorted by severity: Critical, High, Medium, Low)
- Specific fixes (code patches)
- Improvement suggestions
```

---

## Common Pitfalls & Solutions

### ❌ Problem: Vague aesthetic descriptions
### ✅ Solution: Force actionable specifications

```
DON'T: "Make it modern and clean"
DO: 
- Whitespace: 1.5x standard padding (24px instead of 16px)
- Typography: Display 56px, H1 40px, Body 16px, line-height 1.6
- Colors: Neutral gray scale (50-900) + single accent color
- Shadows: Maximum 2 shadow tokens (card + modal only)
- Radius: Consistent 6px (buttons/inputs) and 8px (cards)
- Borders: 1px with --border-subtle (#e5e7eb in light mode)
- Transitions: 150ms ease-out only
```

### ❌ Problem: Each component invents its own styles
### ✅ Solution: Enforce token-only rule

```
RULE: Every visual property must map to a token.

Violations:
- ❌ bg-gray-100 (hardcoded Tailwind color)
- ❌ p-[17px] (arbitrary padding not in scale)
- ❌ rounded-[5px] (radius not in scale)
- ❌ shadow-[0_2px_8px_rgba(0,0,0,0.1)] (arbitrary shadow)

Correct:
- ✅ bg-surface (semantic token)
- ✅ p-4 (maps to spacing scale: 16px)
- ✅ rounded-md (maps to radius scale: 6px)
- ✅ shadow-sm (maps to shadow token)
```

### ❌ Problem: Missing interactive states
### ✅ Solution: State coverage checklist

```
For EVERY interactive element, implement:

Visual States:
- [ ] Default (base appearance)
- [ ] Hover (background shift, shadow, scale)
- [ ] Active (pressed state, slightly darker)
- [ ] Focus (visible ring, keyboard accessible)
- [ ] Disabled (reduced opacity, cursor not-allowed)

Data States:
- [ ] Loading (skeleton or spinner with same dimensions)
- [ ] Empty (clear message + CTA)
- [ ] Error (error message + retry option)

Test each state in isolation and in combination.
```

### ❌ Problem: Generic AI aesthetics
### ✅ Solution: Force creative differentiation

```
BANNED PATTERNS (overused in AI-generated UIs):
- ❌ Inter/Roboto/System fonts as primary choice
- ❌ Purple gradients on white backgrounds
- ❌ Card-grid-card-grid layouts only
- ❌ Generic blue (#3b82f6) as primary
- ❌ Default Tailwind color palette with no customization

REQUIRED CREATIVE CHOICES:
- ✅ Select distinctive fonts (Google Fonts, Adobe Fonts, custom)
- ✅ Build custom color palette (not Tailwind defaults)
- ✅ Design unique layouts (asymmetry, overlap, grid-breaking)
- ✅ Add personality: illustrations, icons, textures, patterns
- ✅ Create signature elements (unique buttons, cards, headers)

Ask yourself: "Would someone recognize this as uniquely designed for this purpose?"
```

### ❌ Problem: Accessibility as afterthought
### ✅ Solution: Accessibility as constraint

```
Build accessibility IN, not ON:

Color Contrast:
- Run contrast checker on all text/background pairs
- Minimum WCAG AA: 4.5:1 (normal text), 3:1 (large text)
- Use tools: WebAIM Contrast Checker, Chrome DevTools

Keyboard Navigation:
- Tab order follows visual flow
- All interactive elements keyboard reachable
- Focus indicator always visible (outline or ring)
- Escape closes modals/dropdowns

ARIA & Semantics:
- Use semantic HTML first (<button>, <nav>, <main>)
- Add ARIA only when semantic HTML insufficient
- aria-label for icon-only buttons
- aria-describedby for form errors
- aria-expanded for disclosure widgets

Test with:
- Keyboard only (no mouse)
- Screen reader (NVDA, JAWS, VoiceOver)
- Reduced motion preference (prefers-reduced-motion)
```

---

## Quick Start: Complete Example

```
You are a Design Systems Engineer + Senior Frontend UI Developer.

[STACK]
React + TypeScript + Tailwind CSS + shadcn/ui

[TASK]
Build a Team Dashboard for a project management app.

[AESTHETIC]
Style: Minimal Premium SaaS
Unique Element: Subtle animated background gradient
Audience: Product managers and software teams

[REQUIREMENTS]
1. Components needed:
   - Header with search and user menu
   - Team members grid (name, role, avatar, status)
   - Invite modal (name, email, role selector)
   - Empty state (no team members yet)
   - Loading skeleton

2. Features:
   - Search/filter team members
   - Click to view member details
   - Invite button opens modal
   - Sort by name/role/status

3. States:
   - Loading (skeleton grid)
   - Empty (with invite CTA)
   - Populated (member cards)
   - Error (failed to load)

[OUTPUT]
1. Design Tokens (globals.css + tailwind.config.ts)
2. Component implementations:
   - TeamMemberCard
   - InviteModal
   - SearchBar
   - UserMenu
3. TeamDashboard page component
4. All states (loading/empty/error)
5. Full TypeScript types
6. Accessibility notes

Rules:
- Mobile-first responsive
- No hardcoded values (use tokens)
- WCAG AA compliance
- Include hover/focus/active states
- Add subtle micro-interactions
```

---

## Examples & Templates

This skill includes production-ready examples in `examples/`:

### CSS Examples (`examples/css/`)

**`tokens.css`** — Complete design token system
- Semantic color tokens (light + dark modes)
- Typography scale with fluid sizing
- Spacing, radius, shadow, motion scales
- CSS custom properties ready to use

**`components.css`** — Component style library
- Buttons (variants, sizes, states)
- Inputs, textareas, selects
- Cards, modals, tooltips
- Navigation, headers, footers
- Loading skeletons
- All with state variants (hover/focus/active/disabled)

**`utilities.css`** — Utility class library
- Layout utilities (flex, grid, container)
- Spacing utilities (margin, padding)
- Typography utilities (sizes, weights, line-heights)
- State utilities (hover, focus, group variants)

### TypeScript Examples (`examples/typescript/`)

**`design-tokens.ts`** — Type-safe token definitions
- Token interfaces and types
- Design system configuration
- Theme type definitions
- Token validators

**`theme-provider.tsx`** — Theme management system
- Theme context provider
- Dark mode toggle
- System preference detection
- Theme persistence (localStorage)

**`sample-components.tsx`** — Production component examples
- Button component (all variants)
- Input component (with validation)
- Card component (with loading states)
- Modal component (with focus management)
- All with full TypeScript types and accessibility

### Templates (`templates/`)

**`tailwind-config.js`** — Optimized Tailwind configuration
- Custom color palette
- Typography plugin setup
- Spacing and sizing scales
- Plugin configurations

**`globals.css`** — Global styles template
- CSS reset/normalize
- Token definitions
- Base element styles
- Utility classes

---

## Output Quality Standards

Every deliverable must meet:

### Code Quality
- ✅ Production-ready (copy-paste deployable)
- ✅ TypeScript with full type safety
- ✅ ESLint/Prettier compliant
- ✅ No hardcoded magic numbers
- ✅ DRY (Don't Repeat Yourself)
- ✅ Clear, descriptive naming
- ✅ JSDoc comments for complex logic

### Design Quality
- ✅ Unique, memorable aesthetic
- ✅ Consistent token usage
- ✅ Cohesive visual language
- ✅ Thoughtful micro-interactions
- ✅ Polished details (shadows, transitions, spacing)

### Accessibility Quality
- ✅ WCAG AA minimum (AAA preferred)
- ✅ Keyboard navigable
- ✅ Screen reader friendly
- ✅ Focus management
- ✅ Semantic HTML
- ✅ ARIA when necessary

### Performance Quality
- ✅ Optimized bundle size (tree-shaking)
- ✅ Lazy loading for heavy components
- ✅ CSS-only animations when possible
- ✅ Minimal re-renders (React memo/useMemo)
- ✅ Responsive images (srcset, sizes)

---

## Verification Checklist

Before delivering code, verify:

**Tokens & System:**
- [ ] All colors from semantic tokens (no hex/rgb hardcoded)
- [ ] All spacing from spacing scale (8px system)
- [ ] All radius from radius scale (xs/sm/md/lg/xl/2xl/full)
- [ ] Shadows minimal and justified
- [ ] Typography hierarchy clear (Display/H1/H2/H3/Body/Small/Caption)
- [ ] Line-height comfortable (1.5+ for body text)

**States & Interactions:**
- [ ] Default state implemented
- [ ] Hover state (visual feedback)
- [ ] Active state (pressed appearance)
- [ ] Focus state (keyboard ring visible)
- [ ] Disabled state (reduced opacity, no pointer)
- [ ] Loading state (skeleton or spinner)
- [ ] Empty state (clear message + CTA)
- [ ] Error state (message + recovery)

**Accessibility:**
- [ ] WCAG AA contrast (4.5:1 text, 3:1 large text)
- [ ] Keyboard navigation complete
- [ ] Focus indicators always visible
- [ ] Semantic HTML used
- [ ] ARIA labels where needed
- [ ] Form labels associated
- [ ] Alt text on images

**Responsive Design:**
- [ ] Mobile layout (375px+) functional
- [ ] Tablet layout (768px+) optimized
- [ ] Desktop layout (1024px+) enhanced
- [ ] Touch targets ≥ 44px
- [ ] Text readable on all sizes
- [ ] No horizontal scroll

**Creative Execution:**
- [ ] Unique aesthetic (not generic)
- [ ] Matches stated design direction
- [ ] Memorable visual element
- [ ] Cohesive design language
- [ ] Polished details

**Code Quality:**
- [ ] TypeScript types complete
- [ ] No linter errors
- [ ] DRY principles followed
- [ ] Clear component boundaries
- [ ] Consistent naming conventions
- [ ] Adequate comments
- [ ] Production-ready (can deploy as-is)

---

## Advanced Techniques

### 1. Fluid Typography

```css
/* Responsive type scale using clamp() */
:root {
  --font-size-sm: clamp(0.875rem, 0.8rem + 0.2vw, 1rem);
  --font-size-base: clamp(1rem, 0.9rem + 0.3vw, 1.125rem);
  --font-size-lg: clamp(1.125rem, 1rem + 0.4vw, 1.25rem);
  --font-size-xl: clamp(1.25rem, 1.1rem + 0.5vw, 1.5rem);
  --font-size-2xl: clamp(1.5rem, 1.3rem + 0.7vw, 2rem);
  --font-size-3xl: clamp(1.875rem, 1.5rem + 1vw, 2.5rem);
  --font-size-4xl: clamp(2.25rem, 1.8rem + 1.5vw, 3.5rem);
}
```

### 2. Advanced Color Systems

```css
/* Color with opacity variants using oklch */
:root {
  --primary-base: oklch(60% 0.15 250);
  --primary-subtle: oklch(95% 0.02 250);
  --primary-muted: oklch(85% 0.05 250);
  --primary-emphasis: oklch(50% 0.18 250);
  --primary-foreground: oklch(98% 0.01 250);
}

/* Dark mode: adjust lightness only */
[data-theme="dark"] {
  --primary-base: oklch(70% 0.15 250);
  --primary-subtle: oklch(20% 0.02 250);
  --primary-muted: oklch(30% 0.05 250);
  --primary-emphasis: oklch(80% 0.18 250);
  --primary-foreground: oklch(10% 0.01 250);
}
```

### 3. Skeleton Loading Patterns

```tsx
// Animated skeleton with shimmer effect
const Skeleton = ({ className }: { className?: string }) => (
  <div
    className={cn(
      "animate-pulse rounded-md bg-surface-subtle",
      "relative overflow-hidden",
      "before:absolute before:inset-0",
      "before:-translate-x-full before:animate-shimmer",
      "before:bg-gradient-to-r before:from-transparent before:via-white/10 before:to-transparent",
      className
    )}
  />
);

// Usage in components
<Card>
  <Skeleton className="h-4 w-3/4 mb-2" />
  <Skeleton className="h-4 w-1/2 mb-4" />
  <Skeleton className="h-32 w-full" />
</Card>
```

### 4. Advanced Motion

```css
/* Page transitions */
@keyframes fade-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Staggered animations */
.stagger-item {
  animation: fade-in 0.3s ease-out backwards;
}
.stagger-item:nth-child(1) { animation-delay: 0ms; }
.stagger-item:nth-child(2) { animation-delay: 50ms; }
.stagger-item:nth-child(3) { animation-delay: 100ms; }
.stagger-item:nth-child(4) { animation-delay: 150ms; }

/* Respect reduced motion */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## Tips for Excellence

1. **Always start with tokens** — Never skip to components
2. **Think mobile-first** — Design for 375px, enhance upward
3. **Validate states early** — Test each interactive state in isolation
4. **Be bold with aesthetics** — Avoid generic patterns
5. **Accessibility is non-negotiable** — Build it in from the start
6. **Use real content** — Test with actual text, images, data
7. **Review your own work** — Self-audit before delivering
8. **Document decisions** — Explain complex styling choices
9. **Keep it maintainable** — Future developers will thank you
10. **Ship production-ready code** — No "TODO" or "FIXME" in deliverables

---

## References & Resources

- **Tailwind CSS**: https://tailwindcss.com/docs
- **shadcn/ui**: https://ui.shadcn.com
- **WCAG Guidelines**: https://www.w3.org/WAI/WCAG21/quickref/
- **Color Contrast Checker**: https://webaim.org/resources/contrastchecker/
- **Type Scale**: https://typescale.com
- **Modular Scale**: https://www.modularscale.com
- **CSS Custom Properties**: https://developer.mozilla.org/en-US/docs/Web/CSS/Using_CSS_custom_properties

---

**Version**: 2.0.0  
**Last Updated**: December 2024  
**License**: MIT  
**Maintained by**: z-ai platform team
