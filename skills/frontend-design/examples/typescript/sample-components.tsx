/**
 * Sample Components — Production-Ready React Components
 * 
 * This file demonstrates how to build type-safe, accessible React components
 * using the design token system.
 * 
 * Location: {project_path}/skills/frontend-design/examples/typescript/sample-components.tsx
 * 
 * All components include:
 * - Full TypeScript type safety
 * - Complete state coverage (default/hover/active/focus/disabled/loading/error)
 * - Accessibility (ARIA labels, keyboard navigation)
 * - Responsive design
 * - Token-based styling
 */

import React, { useState, forwardRef, InputHTMLAttributes, ButtonHTMLAttributes } from 'react';
import { cn } from './utils'; // Utility for classname merging

// ============================================
// BUTTON COMPONENT
// ============================================

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      isLoading = false,
      disabled,
      leftIcon,
      rightIcon,
      children,
      className,
      ...props
    },
    ref
  ) => {
    const baseClasses = 'btn';
    const variantClasses = {
      primary: 'btn-primary',
      secondary: 'btn-secondary',
      outline: 'btn-outline',
      ghost: 'btn-ghost',
      danger: 'btn-danger',
    };
    const sizeClasses = {
      sm: 'btn-sm',
      md: '',
      lg: 'btn-lg',
    };

    return (
      <button
        ref={ref}
        className={cn(
          baseClasses,
          variantClasses[variant],
          sizeClasses[size],
          isLoading && 'btn-loading',
          className
        )}
        disabled={disabled || isLoading}
        {...props}
      >
        {!isLoading && leftIcon && <span className="btn-icon-left">{leftIcon}</span>}
        <span className={isLoading ? 'opacity-0' : ''}>{children}</span>
        {!isLoading && rightIcon && <span className="btn-icon-right">{rightIcon}</span>}
      </button>
    );
  }
);

Button.displayName = 'Button';

// Usage Example:
/*
<Button variant="primary" size="md">
  Click me
</Button>

<Button variant="outline" isLoading>
  Loading...
</Button>

<Button
  variant="primary"
  leftIcon={<PlusIcon />}
  rightIcon={<ArrowRightIcon />}
>
  Get Started
</Button>
*/

// ============================================
// INPUT COMPONENT
// ============================================

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  size?: 'sm' | 'md' | 'lg';
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      label,
      error,
      helperText,
      size = 'md',
      leftIcon,
      rightIcon,
      className,
      id,
      required,
      ...props
    },
    ref
  ) => {
    const inputId = id || `input-${Math.random().toString(36).substr(2, 9)}`;
    const errorId = error ? `${inputId}-error` : undefined;
    const helperId = helperText ? `${inputId}-helper` : undefined;

    const sizeClasses = {
      sm: 'input-sm',
      md: '',
      lg: 'input-lg',
    };

    return (
      <div className="form-group">
        {label && (
          <label htmlFor={inputId} className={cn('label', required && 'label-required')}>
            {label}
          </label>
        )}
        
        <div className="relative">
          {leftIcon && (
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted">
              {leftIcon}
            </div>
          )}
          
          <input
            ref={ref}
            id={inputId}
            className={cn(
              'input',
              sizeClasses[size],
              error && 'input-error',
              leftIcon && 'pl-10',
              rightIcon && 'pr-10',
              className
            )}
            aria-invalid={error ? 'true' : 'false'}
            aria-describedby={cn(errorId, helperId)}
            {...props}
          />
          
          {rightIcon && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted">
              {rightIcon}
            </div>
          )}
        </div>
        
        {error && (
          <span id={errorId} className="helper-text helper-text-error" role="alert">
            {error}
          </span>
        )}
        
        {!error && helperText && (
          <span id={helperId} className="helper-text">
            {helperText}
          </span>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

// Usage Example:
/*
<Input
  label="Email"
  type="email"
  placeholder="you@example.com"
  required
  leftIcon={<MailIcon />}
/>

<Input
  label="Password"
  type="password"
  error="Password must be at least 8 characters"
  helperText="Use a strong, unique password"
/>
*/

// ============================================
// CARD COMPONENT
// ============================================

interface CardProps {
  children: React.ReactNode;
  className?: string;
  interactive?: boolean;
  onClick?: () => void;
}

export function Card({ children, className, interactive = false, onClick }: CardProps) {
  return (
    <div
      className={cn(
        'card',
        interactive && 'card-interactive',
        className
      )}
      onClick={onClick}
      role={interactive ? 'button' : undefined}
      tabIndex={interactive ? 0 : undefined}
      onKeyDown={
        interactive
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onClick?.();
              }
            }
          : undefined
      }
    >
      {children}
    </div>
  );
}

export function CardHeader({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn('card-header', className)}>{children}</div>;
}

export function CardTitle({ children, className }: { children: React.ReactNode; className?: string }) {
  return <h3 className={cn('card-title', className)}>{children}</h3>;
}

export function CardDescription({ children, className }: { children: React.ReactNode; className?: string }) {
  return <p className={cn('card-description', className)}>{children}</p>;
}

export function CardBody({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn('card-body', className)}>{children}</div>;
}

export function CardFooter({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn('card-footer', className)}>{children}</div>;
}

// Usage Example:
/*
<Card>
  <CardHeader>
    <CardTitle>Project Overview</CardTitle>
    <CardDescription>Track your project's progress</CardDescription>
  </CardHeader>
  <CardBody>
    <p>Your project is 75% complete</p>
  </CardBody>
  <CardFooter>
    <Button variant="primary">View Details</Button>
    <Button variant="outline">Share</Button>
  </CardFooter>
</Card>

<Card interactive onClick={() => console.log('Clicked')}>
  <CardBody>Click me!</CardBody>
</Card>
*/

// ============================================
// BADGE COMPONENT
// ============================================

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'success' | 'warning' | 'danger' | 'outline';
  className?: string;
}

export function Badge({ children, variant = 'primary', className }: BadgeProps) {
  const variantClasses = {
    primary: 'badge-primary',
    secondary: 'badge-secondary',
    success: 'badge-success',
    warning: 'badge-warning',
    danger: 'badge-danger',
    outline: 'badge-outline',
  };

  return (
    <span className={cn('badge', variantClasses[variant], className)}>
      {children}
    </span>
  );
}

// Usage Example:
/*
<Badge variant="success">Active</Badge>
<Badge variant="warning">Pending</Badge>
<Badge variant="danger">Failed</Badge>
*/

// ============================================
// ALERT COMPONENT
// ============================================

interface AlertProps {
  children: React.ReactNode;
  variant?: 'info' | 'success' | 'warning' | 'danger';
  title?: string;
  onClose?: () => void;
  className?: string;
}

export function Alert({ children, variant = 'info', title, onClose, className }: AlertProps) {
  const variantClasses = {
    info: 'alert-info',
    success: 'alert-success',
    warning: 'alert-warning',
    danger: 'alert-danger',
  };

  const icons = {
    info: (
      <svg className="alert-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    success: (
      <svg className="alert-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    warning: (
      <svg className="alert-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    ),
    danger: (
      <svg className="alert-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  };

  return (
    <div className={cn('alert', variantClasses[variant], className)} role="alert">
      {icons[variant]}
      <div className="alert-content">
        {title && <div className="alert-title">{title}</div>}
        <div className="alert-description">{children}</div>
      </div>
      {onClose && (
        <button
          onClick={onClose}
          className="ml-auto text-current hover:opacity-70 transition-opacity"
          aria-label="Close alert"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      )}
    </div>
  );
}

// Usage Example:
/*
<Alert variant="success" title="Success">
  Your changes have been saved successfully.
</Alert>

<Alert variant="danger" title="Error" onClose={() => console.log('Closed')}>
  Failed to save changes. Please try again.
</Alert>
*/

// ============================================
// MODAL COMPONENT
// ============================================

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;
  title?: string;
  className?: string;
}

export function Modal({ isOpen, onClose, children, title, className }: ModalProps) {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className={cn('modal', className)}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? 'modal-title' : undefined}
      >
        {title && (
          <div className="modal-header">
            <h2 id="modal-title" className="modal-title">
              {title}
            </h2>
            <button onClick={onClose} className="modal-close" aria-label="Close modal">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
        )}
        {children}
      </div>
    </div>
  );
}

export function ModalBody({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn('modal-body', className)}>{children}</div>;
}

export function ModalFooter({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn('modal-footer', className)}>{children}</div>;
}

// Usage Example:
/*
function Example() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <Button onClick={() => setIsOpen(true)}>Open Modal</Button>
      
      <Modal isOpen={isOpen} onClose={() => setIsOpen(false)} title="Confirm Action">
        <ModalBody>
          <p>Are you sure you want to proceed with this action?</p>
        </ModalBody>
        <ModalFooter>
          <Button variant="outline" onClick={() => setIsOpen(false)}>
            Cancel
          </Button>
          <Button variant="primary" onClick={() => setIsOpen(false)}>
            Confirm
          </Button>
        </ModalFooter>
      </Modal>
    </>
  );
}
*/

// ============================================
// SKELETON LOADING COMPONENT
// ============================================

interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'title' | 'avatar' | 'card' | 'rect';
  width?: string;
  height?: string;
}

export function Skeleton({ className, variant = 'text', width, height }: SkeletonProps) {
  const variantClasses = {
    text: 'skeleton-text',
    title: 'skeleton-title',
    avatar: 'skeleton-avatar',
    card: 'skeleton-card',
    rect: '',
  };

  const style: React.CSSProperties = {};
  if (width) style.width = width;
  if (height) style.height = height;

  return (
    <div
      className={cn('skeleton', variantClasses[variant], className)}
      style={style}
      aria-label="Loading"
    />
  );
}

// Usage Example:
/*
// Loading card
<Card>
  <CardHeader>
    <Skeleton variant="title" />
    <Skeleton variant="text" width="60%" />
  </CardHeader>
  <CardBody>
    <Skeleton variant="text" />
    <Skeleton variant="text" />
    <Skeleton variant="text" width="80%" />
  </CardBody>
</Card>

// Loading list
<div className="space-y-4">
  {[1, 2, 3].map((i) => (
    <div key={i} className="flex items-center gap-4">
      <Skeleton variant="avatar" />
      <div className="flex-1">
        <Skeleton variant="text" width="40%" />
        <Skeleton variant="text" width="60%" />
      </div>
    </div>
  ))}
</div>
*/

// ============================================
// EMPTY STATE COMPONENT
// ============================================

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn('empty-state', className)}>
      {icon && <div className="empty-state-icon">{icon}</div>}
      <h3 className="empty-state-title">{title}</h3>
      {description && <p className="empty-state-description">{description}</p>}
      {action && <div className="empty-state-action">{action}</div>}
    </div>
  );
}

// Usage Example:
/*
<EmptyState
  icon={<FolderIcon />}
  title="No projects yet"
  description="Get started by creating your first project"
  action={
    <Button variant="primary" leftIcon={<PlusIcon />}>
      Create Project
    </Button>
  }
/>
*/

// ============================================
// ERROR STATE COMPONENT
// ============================================

interface ErrorStateProps {
  title: string;
  message: string;
  onRetry?: () => void;
  onGoBack?: () => void;
  className?: string;
}

export function ErrorState({ title, message, onRetry, onGoBack, className }: ErrorStateProps) {
  return (
    <div className={cn('error-state', className)}>
      <svg className="error-state-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
        />
      </svg>
      <h3 className="error-state-title">{title}</h3>
      <p className="error-state-message">{message}</p>
      <div className="error-state-actions">
        {onGoBack && (
          <Button variant="outline" onClick={onGoBack}>
            Go Back
          </Button>
        )}
        {onRetry && (
          <Button variant="primary" onClick={onRetry}>
            Try Again
          </Button>
        )}
      </div>
    </div>
  );
}

// Usage Example:
/*
<ErrorState
  title="Failed to load data"
  message="We couldn't load your projects. Please check your connection and try again."
  onRetry={() => refetch()}
  onGoBack={() => navigate('/')}
/>
*/

// ============================================
// AVATAR COMPONENT
// ============================================

interface AvatarProps {
  src?: string;
  alt?: string;
  fallback?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function Avatar({ src, alt, fallback, size = 'md', className }: AvatarProps) {
  const [imageError, setImageError] = useState(false);

  const sizeClasses = {
    sm: 'avatar-sm',
    md: '',
    lg: 'avatar-lg',
  };

  const showFallback = !src || imageError;
  const initials = fallback
    ? fallback
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2)
    : '?';

  return (
    <div className={cn('avatar', sizeClasses[size], className)}>
      {showFallback ? (
        <span>{initials}</span>
      ) : (
        <img
          src={src}
          alt={alt || fallback || 'Avatar'}
          onError={() => setImageError(true)}
        />
      )}
    </div>
  );
}

// Usage Example:
/*
<Avatar src="/user.jpg" alt="John Doe" fallback="John Doe" />
<Avatar fallback="Jane Smith" size="lg" />
<Avatar src="/broken.jpg" fallback="Error" /> // Falls back to initials
*/
