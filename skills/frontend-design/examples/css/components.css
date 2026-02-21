/**
 * Component Styles — Production-Ready UI Components
 * 
 * This file provides complete component implementations using the design token system.
 * All components include full state coverage and accessibility features.
 * 
 * Location: {project_path}/skills/frontend-design/examples/css/components.css
 * 
 * Dependencies: tokens.css must be imported first
 */

/* Import design tokens */
@import './tokens.css';


/* ============================================
   BUTTONS
   ============================================ */

/* Base button styles */
.btn {
  /* Layout */
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-2);
  
  /* Sizing */
  height: var(--button-height-md);
  padding-inline: var(--spacing-6);
  
  /* Typography */
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  line-height: 1;
  text-decoration: none;
  white-space: nowrap;
  
  /* Appearance */
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  cursor: pointer;
  user-select: none;
  
  /* Transitions */
  transition: var(--transition-colors), var(--transition-transform);
  
  /* Accessibility */
  position: relative;
}

.btn:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring-color);
  outline-offset: var(--focus-ring-offset);
}

/* Primary button */
.btn-primary {
  background-color: var(--primary);
  color: var(--primary-foreground);
  box-shadow: var(--shadow-sm);
}

.btn-primary:hover:not(:disabled) {
  background-color: var(--primary-hover);
  box-shadow: var(--shadow-md);
}

.btn-primary:active:not(:disabled) {
  background-color: var(--primary-active);
  transform: translateY(1px);
  box-shadow: var(--shadow-xs);
}

/* Secondary button */
.btn-secondary {
  background-color: var(--secondary);
  color: var(--secondary-foreground);
  box-shadow: var(--shadow-sm);
}

.btn-secondary:hover:not(:disabled) {
  background-color: var(--secondary-hover);
}

.btn-secondary:active:not(:disabled) {
  background-color: var(--secondary-active);
  transform: translateY(1px);
}

/* Outline button */
.btn-outline {
  background-color: transparent;
  color: var(--text);
  border-color: var(--border);
}

.btn-outline:hover:not(:disabled) {
  background-color: var(--surface-hover);
  border-color: var(--border-strong);
}

.btn-outline:active:not(:disabled) {
  background-color: var(--surface-subtle);
}

/* Ghost button */
.btn-ghost {
  background-color: transparent;
  color: var(--text);
}

.btn-ghost:hover:not(:disabled) {
  background-color: var(--surface-hover);
}

.btn-ghost:active:not(:disabled) {
  background-color: var(--surface-subtle);
}

/* Danger button */
.btn-danger {
  background-color: var(--danger);
  color: var(--danger-foreground);
}

.btn-danger:hover:not(:disabled) {
  background-color: oklch(from var(--danger) calc(l - 0.05) c h);
}

/* Button sizes */
.btn-sm {
  height: var(--button-height-sm);
  padding-inline: var(--spacing-4);
  font-size: var(--font-size-sm);
}

.btn-lg {
  height: var(--button-height-lg);
  padding-inline: var(--spacing-8);
  font-size: var(--font-size-lg);
}

/* Icon-only button */
.btn-icon {
  padding: 0;
  width: var(--button-height-md);
}

.btn-icon.btn-sm {
  width: var(--button-height-sm);
}

.btn-icon.btn-lg {
  width: var(--button-height-lg);
}

/* Disabled state */
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  pointer-events: none;
}

/* Loading state */
.btn-loading {
  position: relative;
  color: transparent;
  pointer-events: none;
}

.btn-loading::after {
  content: '';
  position: absolute;
  width: 1rem;
  height: 1rem;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: var(--radius-full);
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}


/* ============================================
   INPUTS & FORMS
   ============================================ */

/* Input base */
.input {
  /* Layout */
  display: flex;
  width: 100%;
  height: var(--input-height-md);
  padding-inline: var(--spacing-4);
  
  /* Typography */
  font-size: var(--font-size-base);
  line-height: 1.5;
  color: var(--text);
  
  /* Appearance */
  background-color: var(--background);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  
  /* Transitions */
  transition: var(--transition-colors), border-color var(--duration-fast) var(--ease-out);
}

.input::placeholder {
  color: var(--text-muted);
}

.input:hover:not(:disabled):not(:focus) {
  border-color: var(--border-strong);
}

.input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px var(--primary-subtle);
}

.input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background-color: var(--surface-subtle);
}

/* Input with error */
.input-error {
  border-color: var(--danger);
}

.input-error:focus {
  border-color: var(--danger);
  box-shadow: 0 0 0 3px var(--danger-subtle);
}

/* Input sizes */
.input-sm {
  height: var(--input-height-sm);
  padding-inline: var(--spacing-3);
  font-size: var(--font-size-sm);
}

.input-lg {
  height: var(--input-height-lg);
  padding-inline: var(--spacing-6);
  font-size: var(--font-size-lg);
}

/* Textarea */
.textarea {
  min-height: 5rem;
  padding-block: var(--spacing-3);
  resize: vertical;
}

/* Label */
.label {
  display: block;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text);
  margin-bottom: var(--spacing-2);
}

.label-required::after {
  content: ' *';
  color: var(--danger);
}

/* Helper text */
.helper-text {
  display: block;
  font-size: var(--font-size-sm);
  color: var(--text-muted);
  margin-top: var(--spacing-1-5);
}

.helper-text-error {
  color: var(--danger);
}

/* Form group */
.form-group {
  margin-bottom: var(--spacing-6);
}

/* Select */
.select {
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 16 16'%3E%3Cpath fill='currentColor' d='M4.5 6L8 9.5L11.5 6'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right var(--spacing-3) center;
  padding-right: var(--spacing-10);
}

/* Checkbox & Radio */
.checkbox,
.radio {
  appearance: none;
  width: 1.25rem;
  height: 1.25rem;
  border: 2px solid var(--border);
  border-radius: var(--radius-xs);
  background-color: var(--background);
  cursor: pointer;
  position: relative;
  transition: var(--transition-colors);
}

.radio {
  border-radius: var(--radius-full);
}

.checkbox:checked,
.radio:checked {
  background-color: var(--primary);
  border-color: var(--primary);
}

.checkbox:checked::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 5px;
  width: 4px;
  height: 8px;
  border: 2px solid white;
  border-top: 0;
  border-left: 0;
  transform: rotate(45deg);
}

.radio:checked::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 8px;
  height: 8px;
  background-color: white;
  border-radius: var(--radius-full);
}


/* ============================================
   CARDS
   ============================================ */

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

.card-header {
  margin-bottom: var(--spacing-4);
  padding-bottom: var(--spacing-4);
  border-bottom: 1px solid var(--border-subtle);
}

.card-title {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  color: var(--text);
  margin: 0;
}

.card-description {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  margin-top: var(--spacing-2);
}

.card-body {
  color: var(--text);
}

.card-footer {
  margin-top: var(--spacing-4);
  padding-top: var(--spacing-4);
  border-top: 1px solid var(--border-subtle);
  display: flex;
  gap: var(--spacing-3);
}

/* Card variants */
.card-interactive {
  cursor: pointer;
}

.card-interactive:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

.card-interactive:active {
  transform: translateY(0);
  box-shadow: var(--shadow-sm);
}


/* ============================================
   BADGES & TAGS
   ============================================ */

.badge {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-1);
  padding: var(--spacing-0-5) var(--spacing-2);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  line-height: 1;
  border-radius: var(--radius-xs);
  white-space: nowrap;
}

.badge-primary {
  background-color: var(--primary-subtle);
  color: var(--primary);
}

.badge-secondary {
  background-color: var(--secondary-subtle);
  color: var(--secondary);
}

.badge-success {
  background-color: var(--success-subtle);
  color: var(--success);
}

.badge-warning {
  background-color: var(--warning-subtle);
  color: var(--warning);
}

.badge-danger {
  background-color: var(--danger-subtle);
  color: var(--danger);
}

.badge-outline {
  background-color: transparent;
  border: 1px solid var(--border);
  color: var(--text);
}


/* ============================================
   ALERTS
   ============================================ */

.alert {
  padding: var(--spacing-4);
  border-radius: var(--radius-md);
  border: 1px solid transparent;
  display: flex;
  gap: var(--spacing-3);
}

.alert-icon {
  flex-shrink: 0;
  width: var(--icon-lg);
  height: var(--icon-lg);
}

.alert-content {
  flex: 1;
}

.alert-title {
  font-weight: var(--font-weight-semibold);
  margin-bottom: var(--spacing-1);
}

.alert-description {
  font-size: var(--font-size-sm);
  opacity: 0.9;
}

.alert-info {
  background-color: var(--info-subtle);
  color: var(--info);
  border-color: var(--info);
}

.alert-success {
  background-color: var(--success-subtle);
  color: var(--success);
  border-color: var(--success);
}

.alert-warning {
  background-color: var(--warning-subtle);
  color: var(--warning);
  border-color: var(--warning);
}

.alert-danger {
  background-color: var(--danger-subtle);
  color: var(--danger);
  border-color: var(--danger);
}


/* ============================================
   MODALS
   ============================================ */

.modal-overlay {
  position: fixed;
  inset: 0;
  background-color: var(--overlay);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-4);
  z-index: var(--z-modal-backdrop);
  animation: fade-in var(--duration-base) var(--ease-out);
}

.modal {
  background-color: var(--surface);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-2xl);
  max-width: 32rem;
  width: 100%;
  max-height: 90vh;
  overflow: auto;
  animation: modal-enter var(--duration-base) var(--ease-out);
  z-index: var(--z-modal);
}

.modal-header {
  padding: var(--spacing-6);
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.modal-title {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  color: var(--text);
  margin: 0;
}

.modal-close {
  background: transparent;
  border: none;
  padding: var(--spacing-2);
  cursor: pointer;
  color: var(--text-muted);
  border-radius: var(--radius-sm);
  transition: var(--transition-colors);
}

.modal-close:hover {
  background-color: var(--surface-hover);
  color: var(--text);
}

.modal-body {
  padding: var(--spacing-6);
}

.modal-footer {
  padding: var(--spacing-6);
  border-top: 1px solid var(--border-subtle);
  display: flex;
  gap: var(--spacing-3);
  justify-content: flex-end;
}

@keyframes fade-in {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes modal-enter {
  from {
    opacity: 0;
    transform: translateY(-1rem) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}


/* ============================================
   TOOLTIPS
   ============================================ */

.tooltip {
  position: relative;
  display: inline-block;
}

.tooltip-content {
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%) translateY(-0.5rem);
  padding: var(--spacing-2) var(--spacing-3);
  background-color: var(--text);
  color: var(--text-inverse);
  font-size: var(--font-size-sm);
  border-radius: var(--radius-sm);
  white-space: nowrap;
  opacity: 0;
  pointer-events: none;
  transition: var(--transition-opacity);
  z-index: var(--z-tooltip);
}

.tooltip:hover .tooltip-content {
  opacity: 1;
}

.tooltip-content::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 4px solid transparent;
  border-top-color: var(--text);
}


/* ============================================
   LOADING SKELETON
   ============================================ */

.skeleton {
  background: linear-gradient(
    90deg,
    var(--surface-subtle) 0%,
    var(--surface-hover) 50%,
    var(--surface-subtle) 100%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
  border-radius: var(--radius-sm);
}

.skeleton-text {
  height: 1em;
  margin-bottom: var(--spacing-2);
}

.skeleton-title {
  height: 1.5em;
  width: 60%;
  margin-bottom: var(--spacing-3);
}

.skeleton-avatar {
  width: var(--avatar-md);
  height: var(--avatar-md);
  border-radius: var(--radius-full);
}

.skeleton-card {
  height: 12rem;
  border-radius: var(--radius-lg);
}

@keyframes shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}


/* ============================================
   AVATARS
   ============================================ */

.avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: var(--avatar-md);
  height: var(--avatar-md);
  border-radius: var(--radius-full);
  overflow: hidden;
  background-color: var(--surface-subtle);
  color: var(--text);
  font-weight: var(--font-weight-medium);
}

.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-sm {
  width: var(--avatar-sm);
  height: var(--avatar-sm);
  font-size: var(--font-size-sm);
}

.avatar-lg {
  width: var(--avatar-lg);
  height: var(--avatar-lg);
  font-size: var(--font-size-xl);
}


/* ============================================
   EMPTY STATES
   ============================================ */

.empty-state {
  text-align: center;
  padding: var(--spacing-16) var(--spacing-8);
}

.empty-state-icon {
  width: var(--spacing-16);
  height: var(--spacing-16);
  margin: 0 auto var(--spacing-6);
  color: var(--text-muted);
}

.empty-state-title {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  color: var(--text);
  margin-bottom: var(--spacing-2);
}

.empty-state-description {
  font-size: var(--font-size-base);
  color: var(--text-secondary);
  margin-bottom: var(--spacing-6);
  max-width: 28rem;
  margin-left: auto;
  margin-right: auto;
}

.empty-state-action {
  margin-top: var(--spacing-6);
}


/* ============================================
   ERROR STATES
   ============================================ */

.error-state {
  text-align: center;
  padding: var(--spacing-12) var(--spacing-8);
  background-color: var(--danger-subtle);
  border-radius: var(--radius-lg);
  border: 1px solid var(--danger);
}

.error-state-icon {
  width: var(--spacing-12);
  height: var(--spacing-12);
  margin: 0 auto var(--spacing-4);
  color: var(--danger);
}

.error-state-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--danger);
  margin-bottom: var(--spacing-2);
}

.error-state-message {
  font-size: var(--font-size-base);
  color: var(--text);
  margin-bottom: var(--spacing-4);
}

.error-state-actions {
  display: flex;
  gap: var(--spacing-3);
  justify-content: center;
  margin-top: var(--spacing-4);
}


/* ============================================
   RESPONSIVE UTILITIES
   ============================================ */

/* Hide on mobile */
@media (max-width: 767px) {
  .hide-mobile {
    display: none !important;
  }
}

/* Hide on tablet and up */
@media (min-width: 768px) {
  .hide-tablet {
    display: none !important;
  }
}

/* Hide on desktop */
@media (min-width: 1024px) {
  .hide-desktop {
    display: none !important;
  }
}
