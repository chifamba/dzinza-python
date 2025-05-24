// Mock implementation for UI components
import React from 'react';

// Mock UI components
const mockUIComponents = {
  Badge: ({ children, className }) => (
    <span data-testid="mock-badge" className={className}>{children}</span>
  ),
  Button: ({ children, onClick, disabled }) => (
    <button data-testid="mock-button" onClick={onClick} disabled={disabled}>{children}</button>
  ),
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
  Form: ({ children }) => <form data-testid="mock-form">{children}</form>,
  FormControl: ({ children }) => <div data-testid="mock-form-control">{children}</div>,
  FormDescription: ({ children }) => <div data-testid="mock-form-description">{children}</div>,
  FormField: ({ control, name, render }) => {
    const field = {
      value: '',
      onChange: () => {},
    };
    return <div data-testid="mock-form-field">{render({ field })}</div>;
  },
  FormItem: ({ children }) => <div data-testid="mock-form-item">{children}</div>,
  FormLabel: ({ children }) => <label data-testid="mock-form-label">{children}</label>,
  FormMessage: ({ children }) => <div data-testid="mock-form-message">{children}</div>,
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
