// Mock implementation for UI components
import React from 'react';

// Mock UI components
const mockUIComponents = {
  Badge: ({ children, variant, className, ...props }) => (
    <span data-testid="mock-badge" className={className} {...props}>{children}</span>
  ),
  Button: ({ children, onClick, disabled }) => {
    // Create a more specific test ID based on button content
    const textContent = typeof children === 'string' 
      ? children 
      : (children && React.isValidElement(children) && typeof children.props.children === 'string')
        ? children.props.children
        : 'button';
    
    return (
      <button 
        data-testid={`mock-button-${textContent.toString().replace(/\s+/g, '-').toLowerCase()}`} 
        onClick={onClick} 
        disabled={disabled}
      >
        {children}
      </button>
    );
  },
  Calendar: ({ selected, onSelect }) => (
    <div data-testid="mock-calendar">
      <button onClick={() => onSelect(new Date())}>Select Date</button>
    </div>
  ),
  Card: ({ children }) => <div data-testid="mock-card">{children}</div>,
  CardHeader: ({ children }) => <div data-testid="mock-card-header">{children}</div>,
  CardTitle: ({ children }) => <div data-testid="mock-card-title">{children}</div>,
  CardDescription: ({ children }) => <div data-testid="mock-card-description">{children}</div>,
  CardContent: ({ children }) => <div data-testid="mock-card-content">{children}</div>,
  CardFooter: ({ children }) => <div data-testid="mock-card-footer">{children}</div>,
  Dialog: ({ children, open, onOpenChange }) => (
    <div data-testid="mock-dialog" data-open={open}>{children}</div>
  ),
  DialogClose: ({ children }) => <button data-testid="mock-dialog-close">{children}</button>,
  DialogContent: ({ children }) => <div data-testid="mock-dialog-content">{children}</div>,
  DialogDescription: ({ children }) => <div data-testid="mock-dialog-description">{children}</div>,
  DialogFooter: ({ children }) => <div data-testid="mock-dialog-footer">{children}</div>,
  DialogHeader: ({ children }) => <div data-testid="mock-dialog-header">{children}</div>,
  DialogTitle: ({ children }) => <div data-testid="mock-dialog-title">{children}</div>,
  DialogTrigger: ({ children }) => <div data-testid="mock-dialog-trigger">{children}</div>,
  Form: React.forwardRef(({ children, handleSubmit, formState, setValue, getValues, register, reset, watch, ...props }, ref) => (
    <form ref={ref} {...props} data-testid="mock-form">{children}</form>
  )),
  FormProvider: ({ children }) => <div data-testid="mock-form-provider">{children}</div>,
  FormControl: React.forwardRef(({ children, ...props }, ref) => (
    <div ref={ref} data-testid="mock-form-control" {...props}>{children}</div>
  )),
  FormItem: React.forwardRef(({ children, className, ...props }, ref) => (
    <div ref={ref} className={className} data-testid="mock-form-item" {...props}>{children}</div>
  )),
  FormField: ({ control, name, render, ...props }) => {
    const field = {
      value: '',
      name: name || '',
      onChange: jest.fn(),
      onBlur: jest.fn(),
      ref: { current: null }
    };
    return (
      <div {...props} data-testid="mock-form-field">
        {typeof render === 'function' ? render({ field }) : null}
      </div>
    );
  },
  FormLabel: React.forwardRef(({ children, htmlFor, id, ...props }, ref) => (
    <label ref={ref} htmlFor={htmlFor || id} data-testid="mock-form-label" {...props}>{children}</label>
  )),
  FormMessage: React.forwardRef(({ children, ...props }, ref) => (
    <span ref={ref} role="alert" aria-live="polite" data-testid="mock-form-message" {...props}>{children}</span>
  )),
  Input: ({ type, value, onChange, placeholder }) => (
    <input
      data-testid="mock-input"
      type={type}
      value={value}
      onChange={onChange}
      placeholder={placeholder}
    />
  ),
  Popover: ({ children, open, onOpenChange }) => (
    <div data-testid="mock-popover" data-open={open}>{children}</div>
  ),
  PopoverContent: ({ children }) => <div data-testid="mock-popover-content">{children}</div>,
  PopoverTrigger: ({ children, asChild }) => {
    if (asChild) return children;
    return <button data-testid="mock-popover-trigger">{children}</button>;
  },
  Select: ({ children, onValueChange, defaultValue }) => (
    <div data-testid="mock-select" data-value={defaultValue}>{children}</div>
  ),
  SelectContent: ({ children }) => <div data-testid="mock-select-content">{children}</div>,
  SelectItem: ({ children, value }) => (
    <div data-testid="mock-select-item" data-value={value}>{children}</div>
  ),
  SelectTrigger: ({ children }) => <button data-testid="mock-select-trigger">{children}</button>,
  SelectValue: ({ children, placeholder }) => (
    <span data-testid="mock-select-value">{children || placeholder}</span>
  ),
  Separator: () => <hr data-testid="mock-separator" />,
  Tabs: ({ children, value, onValueChange }) => (
    <div data-testid="mock-tabs" data-value={value}>{children}</div>
  ),
  TabsContent: ({ children, value }) => (
    <div data-testid="mock-tabs-content" data-value={value}>{children}</div>
  ),
  TabsList: ({ children }) => <div data-testid="mock-tabs-list">{children}</div>,
  TabsTrigger: ({ children, value }) => (
    <button data-testid="mock-tabs-trigger" data-value={value}>{children}</button>
  ),
  Textarea: ({ value, onChange, placeholder }) => (
    <textarea
      data-testid="mock-textarea"
      value={value}
      onChange={onChange}
      placeholder={placeholder}
    />
  ),
};

export default mockUIComponents;
