// src/test-utils/__tests__/mock-relationship-form.test.js
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { MockRelationshipForm } from '../mock-components';

describe('MockRelationshipForm Component', () => {
  // Mock handlers
  const mockSubmit = jest.fn();
  const mockCancel = jest.fn();
  
  // Reset mocks before each test
  beforeEach(() => {
    mockSubmit.mockReset();
    mockCancel.mockReset();
  });
  
  test('renders with default values', () => {
    render(
      <MockRelationshipForm 
        onSubmit={mockSubmit} 
        onCancel={mockCancel} 
      />
    );
    
    // Check if component renders correctly
    expect(screen.getByTestId('relationship-form')).toBeDefined();
    expect(screen.getByText('Relationship Details')).toBeDefined();
    expect(screen.getByTestId('relationship-type').value).toBe('');
    expect(screen.getByTestId('relationship-description').value).toBe('');
  });
  
  test('renders with initial data', () => {
    const initialData = {
      type: 'spouse_current',
      description: 'Test description'
    };
    
    render(
      <MockRelationshipForm 
        initialData={initialData}
        onSubmit={mockSubmit} 
        onCancel={mockCancel} 
      />
    );
    
    // Check if form is populated with initial data
    expect(screen.getByTestId('relationship-type').value).toBe('spouse_current');
    expect(screen.getByTestId('relationship-description').value).toBe('Test description');
  });
  
  test('handles form input changes', () => {
    render(
      <MockRelationshipForm 
        onSubmit={mockSubmit} 
        onCancel={mockCancel} 
      />
    );
    
    // Change relationship type
    fireEvent.change(screen.getByTestId('relationship-type'), { 
      target: { value: 'biological_parent' } 
    });
    
    // Change description
    fireEvent.change(screen.getByTestId('relationship-description'), { 
      target: { value: 'Parent-child relationship' } 
    });
    
    // Check if values are updated
    expect(screen.getByTestId('relationship-type').value).toBe('biological_parent');
    expect(screen.getByTestId('relationship-description').value).toBe('Parent-child relationship');
  });
  
  test('submits form with entered data', () => {
    render(
      <MockRelationshipForm 
        onSubmit={mockSubmit} 
        onCancel={mockCancel} 
      />
    );
    
    // Change form values
    fireEvent.change(screen.getByTestId('relationship-type'), { 
      target: { value: 'spouse_current' } 
    });
    
    fireEvent.change(screen.getByTestId('relationship-description'), { 
      target: { value: 'Marriage relationship' } 
    });
    
    // Submit the form
    fireEvent.click(screen.getByTestId('submit-button'));
    
    // Check if onSubmit was called with correct data
    expect(mockSubmit).toHaveBeenCalledTimes(1);
    expect(mockSubmit).toHaveBeenCalledWith({
      type: 'spouse_current',
      description: 'Marriage relationship'
    });
  });
  
  test('calls cancel handler when cancel button is clicked', () => {
    render(
      <MockRelationshipForm 
        onSubmit={mockSubmit} 
        onCancel={mockCancel} 
      />
    );
    
    // Click cancel button
    fireEvent.click(screen.getByTestId('cancel-button'));
    
    // Check if onCancel was called
    expect(mockCancel).toHaveBeenCalledTimes(1);
    expect(mockSubmit).not.toHaveBeenCalled();
  });
});
