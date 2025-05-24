/**
 * @jest-environment jsdom
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PersonForm, { PersonFormProps } from '../PersonForm'; // Adjust path if PersonForm is moved/nested
import { PersonFormData } from '@/lib/schemas'; // Assuming schemas.ts is in lib

// Mock GENDERS from types or directly define here if not easily mockable via module mocks
jest.mock('@/lib/types', () => ({
  ...jest.requireActual('@/lib/types'), // Keep other exports
  GENDERS: ['Male', 'Female', 'Other', 'Unknown'], // Mock GENDERS array
}));

const mockOnSubmit = jest.fn();

const defaultProps: PersonFormProps = {
  onSubmit: mockOnSubmit,
  isLoading: false,
};

const renderPersonForm = (props?: Partial<PersonFormProps>) => {
  return render(<PersonForm {...defaultProps} {...props} />);
};

describe('PersonForm', () => {
  beforeEach(() => {
    mockOnSubmit.mockClear();
  });

  test('renders all basic fields', () => {
    renderPersonForm();
    expect(screen.getByLabelText(/Full Name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Gender/i)).toBeInTheDocument(); // This is the FormLabel
    expect(screen.getByRole('combobox', { name: /Gender/i })).toBeInTheDocument(); // The SelectTrigger
    expect(screen.getByLabelText(/Image URL/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Birth Date/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Death Date/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Biography/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Save Person/i })).toBeInTheDocument();
  });

  test('renders with custom submitButtonText', () => {
    renderPersonForm({ submitButtonText: 'Update Member' });
    expect(screen.getByRole('button', { name: /Update Member/i })).toBeInTheDocument();
  });

  test('calls onSubmit with form data when valid data is submitted', async () => {
    const user = userEvent.setup();
    renderPersonForm();

    await user.type(screen.getByLabelText(/Full Name/i), 'Test User');
    // Gender selection
    await user.click(screen.getByRole('combobox', { name: /Gender/i }));
    await user.click(screen.getByText('Male')); // Assumes 'Male' is an option

    // Date selection needs care due to Popovers and Calendar
    // For now, let's assume dates are optional or test them separately for simplicity in this initial test
    
    await user.click(screen.getByRole('button', { name: /Save Person/i }));

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledTimes(1);
      expect(mockOnSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'Test User',
          gender: 'Male',
        }),
        expect.anything() // For the react-hook-form event
      );
    });
  });

  test('displays validation error for empty name', async () => {
    const user = userEvent.setup();
    renderPersonForm();

    await user.click(screen.getByRole('button', { name: /Save Person/i }));

    expect(await screen.findByText('Name is required.')).toBeInTheDocument(); // From personSchema
    expect(mockOnSubmit).not.toHaveBeenCalled();
  });
  
  // TODO: More tests:
  // - Image URL validation
  // - Birth/Death date validation (death after birth)
  // - Populating with initialData
  // - Loading state (button disabled, spinner)
  // - Custom attributes: rendering, adding, editing, deleting
});
