// src/components/relationship/__tests__/RelationshipDetailsForm.basic.test.tsx
import React from 'react';
import { render, screen } from '@testing-library/react';
import { RelationshipDetailsForm } from '../RelationshipDetailsForm';
import { Person, RelationshipType } from '@/lib/types';

// Mock lucide-react icons
jest.mock('lucide-react', () => {
  const original = jest.requireActual('lucide-react');
  return {
    ...original,
    Loader2: () => <span data-testid="mock-loader-icon"></span>,
    CalendarIcon: () => <span data-testid="mock-calendar-icon"></span>,
    Plus: () => <span data-testid="mock-plus-icon"></span>,
    X: () => <span data-testid="mock-x-icon"></span>,
  };
});

// Mock UI components to avoid nested form issues
jest.mock('@/components/ui/form', () => ({
  FormProvider: ({ children, ...props }: { children: React.ReactNode, [key: string]: any }) => {
    // Filter out react-hook-form specific props before spreading onto the div
    const { 
      handleSubmit,
      formState,
      setValue,
      getValues,
      register,
      reset,
      watch,
      control,
      // Add any other RHF props that might be passed here
      ...restProps 
    } = props;
    return <div data-testid="form-provider" {...restProps}>{children}</div>;
  },
  FormField: ({ name, control, render }: { name: string, control: any, render: Function }) => {
    const field = {
      value: '',
      onChange: jest.fn(),
      onBlur: jest.fn(),
      name,
      ref: { current: null },
    };
    // Provide id and labelId for accessibility in tests
    const id = `mock-${name}-input`;
    const labelId = `mock-${name}-label`;
    return <div data-testid={`form-field-${name}`}>{render({ field, id, labelId })}</div>;
  },
  FormItem: ({ children }: { children: React.ReactNode }) => <div data-testid="form-item">{children}</div>,
  FormLabel: ({ children, htmlFor, id }: { children: React.ReactNode, htmlFor?: string, id?: string }) => (
    <label data-testid="form-label" htmlFor={htmlFor} id={id}>{children}</label>
  ),
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
  Button: ({ children, ...rest }: { children: React.ReactNode, [key: string]: any }) => {
    let textContentForTestId = 'button'; // Default fallback
    if (typeof children === 'string') {
      textContentForTestId = children;
    } else if (Array.isArray(children)) {
      const stringChild = children.find(child => typeof child === 'string');
      if (stringChild) {
        textContentForTestId = stringChild;
      }
    }
    // Sanitize for data-testid
    const sanitizedText = textContentForTestId.replace(/\s+/g, '-').replace(/[^a-zA-Z0-9-]/g, '').toLowerCase();
    return (
      <button data-testid={`button-${sanitizedText || 'button'}`} {...rest}>
        {children}
      </button>
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

jest.mock('@/components/ui/input', () => {
  const Input = React.forwardRef((props: any, ref: any) => <input data-testid="input" {...props} ref={ref} />);
  Input.displayName = 'Input'; // Adding displayName for better debugging
  return {
    Input,
  };
});

jest.mock('@/components/ui/textarea', () => {
  const Textarea = React.forwardRef((props: any, ref: any) => <textarea data-testid="textarea" {...props} ref={ref} />);
  Textarea.displayName = 'Textarea'; // Adding displayName for better debugging
  return {
    Textarea,
  };
});

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
    // This assertion should now pass with the updated button mock
    expect(screen.getByTestId('button-save-relationship')).toBeInTheDocument();
  });
});
