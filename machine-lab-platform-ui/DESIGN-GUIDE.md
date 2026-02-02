# SiberBox Design Guide

## Brand Identity

### Logo Concept
The SiberBox logo uses a 2x2 grid of squares, representing:
- Container orchestration (multiple instances)
- Modular architecture
- Distributed systems
- Cybersecurity compartmentalization

### Color Psychology
**Dark Red (#dc2626)** chosen for:
- Security and authority
- Technical sophistication  
- Alert/defense systems
- Professional cybersecurity aesthetic

## UI Components Reference

### Button Variants

```vue
<!-- Primary Action -->
<button class="btn btn-primary">Deploy Container</button>

<!-- Secondary Action -->
<button class="btn btn-secondary">Cancel</button>

<!-- Ghost/Subtle Action -->
<button class="btn btn-ghost">More Options</button>

<!-- Icon Only -->
<button class="btn-icon btn-ghost">
  <svg>...</svg>
</button>
```

### Status Indicators

```vue
<!-- Success (Running/Healthy) -->
<span class="status status-success">running</span>

<!-- Error (Stopped/Offline) -->
<span class="status status-error">stopped</span>

<!-- Warning -->
<span class="status status-warning">warning</span>
```

### Form Elements

```vue
<div class="form-group">
  <label for="input-id">Label Text</label>
  <input 
    id="input-id"
    type="text" 
    placeholder="Enter value..."
  />
  <p class="form-hint">Helper text goes here</p>
</div>
```

### Cards

```vue
<div class="card">
  <div class="card-header">
    <h3>Card Title</h3>
  </div>
  <p>Card content...</p>
</div>
```

### Modals

```vue
<div class="modal-overlay">
  <div class="modal-content">
    <div class="modal-header">
      <h3>Modal Title</h3>
      <button class="close-btn">×</button>
    </div>
    <!-- Content -->
  </div>
</div>
```

## CSS Custom Properties

### Using Theme Variables

```css
/* Colors */
var(--color-primary)        /* #dc2626 */
var(--color-bg-card)        /* #1a1a1a */
var(--color-text-primary)   /* #f5f5f5 */

/* Spacing */
var(--space-xs)   /* 0.25rem - 4px */
var(--space-sm)   /* 0.5rem  - 8px */
var(--space-md)   /* 1rem    - 16px */
var(--space-lg)   /* 1.5rem  - 24px */
var(--space-xl)   /* 2rem    - 32px */
var(--space-2xl)  /* 3rem    - 48px */

/* Border Radius */
var(--radius-sm)  /* 0.375rem - 6px */
var(--radius-md)  /* 0.5rem   - 8px */
var(--radius-lg)  /* 0.75rem  - 12px */
var(--radius-xl)  /* 1rem     - 16px */

/* Transitions */
var(--transition-fast)    /* 150ms ease */
var(--transition-normal)  /* 250ms ease */
var(--transition-slow)    /* 350ms ease */
```

## Icon System

Using inline SVG with Feather Icons style:
- 16px for small icons (buttons)
- 18-20px for navigation
- 24px for headers
- 32-48px for empty states/illustrations

### Common Icons

```html
<!-- Add/Plus -->
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
  <line x1="12" y1="5" x2="12" y2="19"/>
  <line x1="5" y1="12" x2="19" y2="12"/>
</svg>

<!-- Close/X -->
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
  <line x1="18" y1="6" x2="6" y2="18"/>
  <line x1="6" y1="6" x2="18" y2="18"/>
</svg>

<!-- Search -->
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
  <circle cx="11" cy="11" r="8"/>
  <path d="m21 21-4.35-4.35"/>
</svg>
```

## Layout Patterns

### Dashboard Grid

```vue
<div class="dashboard">
  <!-- Header -->
  <div class="dashboard-header">
    <div>
      <h1>Page Title</h1>
      <p>Description</p>
    </div>
    <button class="btn btn-primary">Action</button>
  </div>

  <!-- Stats Grid -->
  <div class="stats-grid">
    <div class="stat-card">...</div>
    <div class="stat-card">...</div>
    <div class="stat-card">...</div>
  </div>

  <!-- Content Card -->
  <div class="card">
    <div class="card-header">
      <h3>Section Title</h3>
      <div class="search-box">...</div>
    </div>
    <div class="table-wrapper">
      <table>...</table>
    </div>
  </div>
</div>
```

### Table Structure

```vue
<div class="table-wrapper">
  <table>
    <thead>
      <tr>
        <th>Column 1</th>
        <th>Column 2</th>
        <th>Actions</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>Data 1</td>
        <td>Data 2</td>
        <td>
          <div class="action-buttons">
            <button class="btn-icon btn-ghost">...</button>
          </div>
        </td>
      </tr>
    </tbody>
  </table>
</div>
```

## Best Practices

### Do's ✅
- Use design system variables
- Keep consistent spacing
- Provide visual feedback on interactions
- Include loading/empty states
- Use semantic HTML
- Add ARIA labels for accessibility
- Implement keyboard navigation
- Use descriptive button text

### Don'ts ❌
- Don't use arbitrary colors
- Don't skip loading states
- Don't use inline styles (use CSS classes)
- Don't forget mobile responsiveness
- Don't overcomplicate layouts
- Don't use Comic Sans (obviously 😄)
- Don't ignore error states
- Don't create inconsistent spacing

## Accessibility Checklist

- [ ] All interactive elements are keyboard accessible
- [ ] Focus states are visible
- [ ] Color contrast meets WCAG AA (4.5:1)
- [ ] Forms have associated labels
- [ ] Error messages are clear and helpful
- [ ] Loading states are announced
- [ ] Modals trap focus correctly
- [ ] Images have alt text

## Performance Guidelines

### CSS
- Use CSS variables for theming
- Avoid deep nesting (max 3 levels)
- Use scoped styles in components
- Minimize use of expensive properties (shadows, blur)

### JavaScript
- Debounce search inputs
- Lazy load heavy components
- Use Vue's `v-show` for frequently toggled elements
- Implement virtual scrolling for large lists

### Assets
- Use SVG for icons (inline or sprite)
- Optimize images before upload
- Use web fonts with `display: swap`
- Lazy load images below the fold

## DefCon Demo Tips

### For Presentations
1. **Increase browser zoom** to 110-125% for visibility
2. **Use dark mode** throughout (already default)
3. **Prepare demo data** in advance
4. **Test all flows** before presenting
5. **Have backup plans** (screenshots, video)

### Talking Points
- Enterprise-grade container orchestration
- VPN-based network isolation
- Real-time resource monitoring
- Secure multi-tenant architecture
- CTF-ready deployment system

### Live Demo Flow
1. **Login** - Show authentication
2. **Dashboard** - Overview of system
3. **Deploy Container** - Show upload flow
4. **Host Management** - Demonstrate monitoring
5. **Container Details** - VPN profile management
6. **Resource Usage** - Real-time statistics

---

**Last Updated**: January 2026  
**Design System Version**: 2.0.0
