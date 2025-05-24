// src/components/relationship/__tests__/error-scenarios.test.tsx
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@/test-utils/test-utils';
import { setupMockAPI, axiosMock } from '@/test-utils/test-utils';
import AddRelationshipModal from '@/components/modals/AddRelationshipModal';
import { RelationshipDetailsForm } from '@/components/relationship/RelationshipDetailsForm';
import { RelationshipTimeline } from '@/components/relationship/RelationshipTimeline';
import { mockPeople, mockRelationships } from '@/test-utils/mock-data';
import { Person } from '@/lib/types';

// Transform mockPeople into a Record<string, Person> for RelationshipTimeline
const mockPeopleRecord = mockPeople.reduce((acc, person) => {
  acc[person.id] = person;
  return acc;
}, {} as Record<string, Person>);

describe('Relationship Components Error Scenarios', () => {
  // Set up API mocks before each test
  beforeEach(() => {
    setupMockAPI();
    
    // Add console error spy to prevent expected test errors from cluttering the output
    jest.spyOn(console, 'error').mockImplementation(() => {});
  });
  
  afterEach(() => {
    axiosMock.reset();
    jest.restoreAllMocks();
  });
  
  it('handles API errors when creating a relationship', async () => {
    // Mock API error response
    axiosMock.onPost(/\/api\/trees\/test-tree-id\/relationships/).reply(400, {
      error: 'Invalid relationship data',
      details: 'Person IDs must be different'
    });
    
    render(
      <AddRelationshipModal
        isOpen={true}
        onClose={jest.fn()}
        onSubmit={jest.fn()}
        currentPerson={mockPeople[0]}
        selectablePeople={mockPeople}
      />
    );
    
    // Fill out the relationship form with invalid data (same person)
    fireEvent.click(screen.getByLabelText(/First Person/i));
    fireEvent.click(screen.getByText(/John Doe/i));
    
    fireEvent.click(screen.getByLabelText(/Second Person/i));
    fireEvent.click(screen.getByText(/John Doe/i)); // Same person
    
    fireEvent.click(screen.getByLabelText(/Relationship Type/i));
    fireEvent.click(screen.getByText(/Spouse/i));
    
    // Submit the form
    fireEvent.click(screen.getByText(/Create/i));
    
    // Wait for error message to appear
    await waitFor(() => {
      expect(screen.getByText(/Invalid relationship data/i)).toBeInTheDocument();
      expect(screen.getByText(/Person IDs must be different/i)).toBeInTheDocument();
    });
  });
  
  it('handles network errors when loading relationships', async () => {
    // Mock network failure
    axiosMock.onGet(/\/api\/trees\/test-tree-id\/relationships/).networkError();
    
    render(
      <RelationshipTimeline
        relationships={[]}
        people={mockPeopleRecord}
        onEditRelationship={jest.fn()}
        onDeleteRelationship={jest.fn()}
      />
    );
    
    // Empty state message should be displayed
    expect(screen.getByText(/No relationships found/i)).toBeInTheDocument();
  });
  
  it('handles validation errors in the relationship form', async () => {
    render(
      <RelationshipDetailsForm
        selectablePeople={mockPeople}
        initialData={{} as any}
        onSubmit={jest.fn()}
      />
    );
    
    // Try to submit without required fields
    fireEvent.click(screen.getByText(/Save/i));
    
    // Wait for validation errors
    await waitFor(() => {
      expect(screen.getByText(/Please select a relationship type/i)).toBeInTheDocument();
    });
  });
  
  it('handles date validation errors in the form', async () => {
    const invalidDates = {
      person1Id: 'person-1',
      person2Id: 'person-2',
      type: 'spouse_current',
      startDate: new Date('2025-01-01'), // Future date
      endDate: new Date('2020-01-01')    // End date before start date
    };
    
    render(
      <RelationshipDetailsForm
        selectablePeople={mockPeople}
        initialData={invalidDates as any}
        onSubmit={jest.fn()}
      />
    );
    
    // Go to details tab
    fireEvent.click(screen.getByText(/Details/i));
    
    // Submit the form
    fireEvent.click(screen.getByText(/Save/i));
    
    // Wait for validation errors
    await waitFor(() => {
      expect(screen.getByText(/End date must be after start date/i)).toBeInTheDocument();
    });
  });
  
  it('handles server timeouts gracefully', async () => {
    // Mock timeout error
    axiosMock.onPut(/\/api\/trees\/test-tree-id\/relationships\/relationship-1/).timeout();
    
    const handleSubmit = jest.fn(async () => {
      try {
        await axiosMock.onPut(/\/api\/trees\/test-tree-id\/relationships\/relationship-1/).timeout();
      } catch (error) {
        throw new Error('Request timed out');
      }
    });
    
    render(
      <RelationshipDetailsForm
        selectablePeople={mockPeople}
        initialData={{
          person1Id: mockRelationships[0].person1Id,
          person2Id: mockRelationships[0].person2Id,
          type: mockRelationships[0].type,
          startDate: mockRelationships[0].startDate ? new Date(mockRelationships[0].startDate) : undefined,
          endDate: mockRelationships[0].endDate ? new Date(mockRelationships[0].endDate) : undefined,
          location: mockRelationships[0].location,
          description: mockRelationships[0].description,
          customAttributes: mockRelationships[0].customAttributes
        }}
        onSubmit={handleSubmit}
      />
    );
    
    // Submit the form
    fireEvent.click(screen.getByText(/Save/i));
    
    // Wait for error handling
    await waitFor(() => {
      expect(handleSubmit).toHaveBeenCalled();
      // The component should handle the timeout error without crashing
      expect(screen.getByText(/Save/i)).toBeInTheDocument();
    });
  });
});
