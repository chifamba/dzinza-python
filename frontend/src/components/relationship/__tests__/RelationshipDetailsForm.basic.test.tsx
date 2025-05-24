// src/components/relationship/__tests__/RelationshipDetailsForm.basic.test.tsx
import React from 'react';
import { render, screen } from '@testing-library/react';
import { RelationshipDetailsForm } from '../RelationshipDetailsForm';
import { Person, RelationshipType } from '@/lib/types';

// Mock UI components to avoid nested form issues
jest.mock('@/components/ui/form', () => ({
  FormProvider: ({ children, ...props }: { children: React.ReactNode, [key: string]: any }) => (
    <div data-testid="form-provider" {...props}>{children}</div>
  ),
  FormField: ({ name, control, render }: { name: string, control: any, render: Function }) => {
    const field = {
      value: '',
      onChange: jest.fn(),
      onBlur: jest.fn(),
      name,
      ref: { current: null },
    };
    return <div data-testid={`form-field-${name}`}>{render({ field })}</div>;
  },
  FormItem: ({ children }: { children: React.ReactNode }) => <div data-testid="form-item">{children}</div>,
  FormLabel: ({ children }: { children: React.ReactNode }) => <div data-testid="form-label">{children}</div>,
  FormControl: ({ children }: { children: React.ReactNode }) => <div data-testid="form-control">{children}</div>,
  FormDescription: ({ children }: { children: React.ReactNode }) => <div data-testid="form-description">{children}</div>,
  FormMessage: () => <div data-testid="form-message"></div>,
}));

// Mock other UI components needed for the test
jest.mock('@/components/ui/select', () => ({
  Select: ({ children }: { children: React.ReactNode }) => <div data-testid="select">{children}</div>,
  SelectTrigger: ({ children }: { children: React.ReactNode }) => <div data-testid="select-trigger">{children}</div>,
  SelectValue: ({ placeholder }: { placeholder: string }) => <div data-testid="select-value">{placeholder}</div>,
  SelectContent: ({ children }: { children: React.ReactNode }) => <div data-testid="select-content">{children}</div>,
  SelectItem: ({ children }: { children: React.ReactNode }) => <div data-testid="select-item">{children}</div>,
}));

jest.mock('@/components/ui/tabs', () => ({
  Tabs: ({ children }: { children: React.ReactNode }) => <div data-testid="tabs">{children}</div>,
  TabsList: ({ children }: { children: React.ReactNode }) => <div data-testid="tabs-list">{children}</div>,
  TabsTrigger: ({ children }: { children: React.ReactNode }) => <div data-testid="tabs-trigger">{children}</div>,
  TabsContent: ({ children }: { children: React.ReactNode }) => <div data-testid="tabs-content">{children}</div>,
}));

jest.mock('@/components/ui/button', () => ({
  Button: ({ children, onClick, type }: { children: React.ReactNode, onClick?: any, type?: string }) => {
    // Create a more unique testId based on the button's text content
    const textContent = typeof children === 'string' ? children : 'button';
    return (
      <button data-testid={`button-${textContent.replace(/\s+/g, '-').toLowerCase()}`} onClick={onClick}>{children}</button>
    );
  },
}));

jest.mock('@/components/ui/badge', () => ({
  Badge: ({ children }: { children: React.ReactNode }) => <div data-testid="badge">{children}</div>,
}));

jest.mock('@/components/ui/popover', () => ({
  Popover: ({ children }: { children: React.ReactNode }) => <div data-testid="popover">{children}</div>,
  PopoverTrigger: ({ children }: { children: React.ReactNode }) => <div data-testid="popover-trigger">{children}</div>,
  PopoverContent: ({ children }: { children: React.ReactNode }) => <div data-testid="popover-content">{children}</div>,
}));

jest.mock('@/components/ui/calendar', () => ({
  Calendar: () => <div data-testid="calendar"></div>,
}));

jest.mock('@/components/ui/input', () => ({
  Input: (props: any) => <input data-testid="input" {...props} />,
}));

jest.mock('@/components/ui/textarea', () => ({
  Textarea: (props: any) => <textarea data-testid="textarea" {...props} />,
}));

jest.mock('react-hook-form', () => ({
  useForm: () => ({
    register: jest.fn(),
    handleSubmit: jest.fn((fn) => jest.fn()),
    formState: {
      errors: {},
      isSubmitting: false,
    },
    reset: jest.fn(),
    control: {
      register: jest.fn(),
      unregister: jest.fn(),
      getFieldState: jest.fn(),
      _formValues: {},
    },
    setValue: jest.fn(),
    getValues: jest.fn(),
    watch: jest.fn(() => ''),
  }),
}));

// Mock people data
const mockPeople: Person[] = [
  {
    id: 'person-1',
    name: 'John Doe',
    gender: 'Male',
  },
  {
    id: 'person-2',
    name: 'Jane Doe',
    gender: 'Female',
  }
];

// Mock initial data
const mockInitialData = {
  person1Id: 'person-1',
  person2Id: 'person-2',
  type: 'spouse_current' as RelationshipType,
  startDate: new Date('2010-01-01'),
  location: 'New York',
  description: 'Test relationship',
};

// Mock functions
const mockOnSubmit = jest.fn();

describe('RelationshipDetailsForm Basic Tests', () => {
  it('renders without crashing', () => {
    render(
      <RelationshipDetailsForm 
        selectablePeople={mockPeople}
        initialData={mockInitialData}
        onSubmit={mockOnSubmit}
      />
    );

    // Verify that some key elements are rendered
    expect(screen.getByTestId('form-provider')).toBeInTheDocument();
    expect(screen.getByTestId('tabs')).toBeInTheDocument();
    expect(screen.getByTestId('button-save-relationship')).toBeInTheDocument();
  });
});
