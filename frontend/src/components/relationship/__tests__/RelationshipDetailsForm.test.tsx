// src/components/relationship/__tests__/RelationshipDetailsForm.test.tsx
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@/test-utils/test-utils';
import { RelationshipDetailsForm } from '@/components/relationship/RelationshipDetailsForm';
import { mockRelationshipFormData, mockPeople } from '@/test-utils/mock-data';

describe('RelationshipDetailsForm', () => {
  // Setup mock functions
  const mockOnSubmit = jest.fn();
  
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders the form with all fields', () => {
    render(
      <RelationshipDetailsForm 
        selectablePeople={mockPeople} // Mock selectablePeople
        initialData={mockRelationshipFormData} // Use initialData instead of defaultValues
        onSubmit={mockOnSubmit}
      />
    );

    // Check for basic form elements
    expect(screen.getByLabelText(/First Person/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Second Person/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Relationship Type/i)).toBeInTheDocument();
    
    // Check for tabs
    expect(screen.getByRole('tab', { name: /Basic Info/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Details/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Custom Attributes/i })).toBeInTheDocument();
    
    // Check for verification status
    expect(screen.getByText(/Verification Status/i)).toBeInTheDocument();
  });

  it('switches between tabs correctly', async () => {
    render(
      <RelationshipDetailsForm 
        selectablePeople={mockPeople} // Mock selectablePeople
        initialData={mockRelationshipFormData} // Use initialData instead of defaultValues
        onSubmit={mockOnSubmit}
      />
    );
    
    // Start on Basic Info tab
    expect(screen.getByLabelText(/Relationship Type/i)).toBeVisible();
    
    // Switch to Details tab
    fireEvent.click(screen.getByRole('tab', { name: /Details/i }));
    await waitFor(() => {
      expect(screen.getByLabelText(/Start Date/i)).toBeVisible();
      expect(screen.getByLabelText(/Location/i)).toBeVisible();
      expect(screen.getByLabelText(/Description/i)).toBeVisible();
    });
    
    // Switch to Custom Attributes tab
    fireEvent.click(screen.getByRole('tab', { name: /Custom Attributes/i }));
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/New attribute name/i)).toBeVisible();
    });
  });
  
  it('submits the form with valid data', async () => {
    render(
      <RelationshipDetailsForm 
        selectablePeople={mockPeople} // Mock selectablePeople
        initialData={mockRelationshipFormData} // Use initialData instead of defaultValues
        onSubmit={mockOnSubmit}
      />
    );
    
    // Switch to Details tab and update some fields
    fireEvent.click(screen.getByText(/Details/i));
    
    const locationInput = screen.getByLabelText(/Location/i);
    fireEvent.change(locationInput, { target: { value: 'Updated Location' } });
    
    const descriptionInput = screen.getByLabelText(/Description/i);
    fireEvent.change(descriptionInput, { target: { value: 'Updated description' } });
    
    // Submit the form
    fireEvent.click(screen.getByText(/Save/i));
    
    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledTimes(1);
      expect(mockOnSubmit).toHaveBeenCalledWith(expect.objectContaining({
        location: 'Updated Location',
        description: 'Updated description',
      }));
    });
  });
  
  it('handles custom attributes correctly', async () => {
    render(
      <RelationshipDetailsForm 
        selectablePeople={mockPeople} // Mock selectablePeople
        initialData={mockRelationshipFormData} // Use initialData instead of defaultValues
        onSubmit={mockOnSubmit}
      />
    );
    
    // Switch to Custom Attributes tab
    fireEvent.click(screen.getByRole('tab', { name: /Custom Attributes/i }));
    
    // Find existing attributes
    expect(screen.getByDisplayValue(/Ceremony/i)).toBeInTheDocument();
    expect(screen.getByDisplayValue(/Witnesses/i)).toBeInTheDocument();
    
    // Add a new attribute
    const attributeKeyInput = screen.getByPlaceholderText(/New attribute name/i);
    fireEvent.change(attributeKeyInput, { target: { value: 'Test Attribute' } });
    
    const attributeValueInput = screen.getByPlaceholderText(/New attribute value/i);
    fireEvent.change(attributeValueInput, { target: { value: 'Test Value' } });
    
    fireEvent.click(screen.getByRole('button', { name: /\+/i }));
    
    // Submit the form
    fireEvent.click(screen.getByText(/Save Relationship/i));
    
    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledTimes(1);
      expect(mockOnSubmit).toHaveBeenCalledWith(expect.objectContaining({
        customAttributes: expect.objectContaining({
          'Test Attribute': 'Test Value',
          'Ceremony': 'Traditional',
          'Witnesses': 'Robert Smith, Mary Johnson'
        })
      }));
    });
  });
  
  it('validates required fields', async () => {
    render(
      <RelationshipDetailsForm 
        selectablePeople={mockPeople} // Mock selectablePeople
        initialData={{} as any} // Use initialData instead of defaultValues
        onSubmit={mockOnSubmit}
      />
    );
    
    // Try to submit without required fields
    fireEvent.click(screen.getByText(/Save Relationship/i));
    
    await waitFor(() => {
      expect(screen.getByText(/Relationship type is required/i)).toBeInTheDocument();
      expect(mockOnSubmit).not.toHaveBeenCalled();
    });
  });
});
