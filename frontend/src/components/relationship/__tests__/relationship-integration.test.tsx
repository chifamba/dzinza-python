// src/components/relationship/__tests__/relationship-integration.test.tsx
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@/test-utils/test-utils';
import { setupMockAPI, axiosMock } from '@/test-utils/test-utils';
import AddRelationshipModal from '@/components/modals/AddRelationshipModal';
import { RelationshipDetailsForm } from '@/components/relationship/RelationshipDetailsForm';
import { RelationshipTimeline } from '@/components/relationship/RelationshipTimeline';
import { mockPeople, mockRelationships } from '@/test-utils/mock-data';
import { Person, RelationshipType } from '@/lib/types';

// Transform mockPeople into a Record<string, Person> for RelationshipTimeline
const mockPeopleRecord = mockPeople.reduce((acc, person) => {
  acc[person.id] = person;
  return acc;
}, {} as Record<string, Person>);

describe('Relationship Components Integration', () => {
  // Set up API mocks before each test
  beforeEach(() => {
    setupMockAPI();
  });
  
  afterEach(() => {
    axiosMock.reset();
  });
  
  it('creates a new relationship and updates the timeline', async () => {
    // Mock API responses for creating a relationship
    axiosMock.onPost(/\/api\/trees\/test-tree-id\/relationships/).reply(201, {
      id: 'new-relationship-id',
      person1Id: 'person-1',
      person2Id: 'person-3',
      type: 'biological_parent',
      description: 'New relationship'
    });
    
    // Setup for relationship creation modal and timeline
    const { rerender } = render(
      <>
        <AddRelationshipModal
          isOpen={true}
          onClose={jest.fn()}
          onSubmit={jest.fn()}
          currentPerson={mockPeople[0]}
          selectablePeople={mockPeople}
        />
        <RelationshipTimeline
          relationships={mockRelationships}
          people={mockPeopleRecord}
          onEditRelationship={jest.fn()}
          onDeleteRelationship={jest.fn()}
        />
      </>
    );
    
    // Fill out the relationship form
    fireEvent.click(screen.getByLabelText(/First Person/i));
    fireEvent.click(screen.getByText(/John Doe/i));
    
    fireEvent.click(screen.getByLabelText(/Second Person/i));
    fireEvent.click(screen.getByText(/Michael Doe/i));
    
    fireEvent.click(screen.getByLabelText(/Relationship Type/i));
    fireEvent.click(screen.getByText(/Biological Parent/i));
    
    // Submit the form
    fireEvent.click(screen.getByText(/Create/i));
    
    // Wait for API call to complete
    await waitFor(() => {
      expect(axiosMock.history.post.length).toBe(1);
    });
    
    // Add the new relationship to the list
    const updatedRelationships = [
      ...mockRelationships,
      {
        id: 'new-relationship-id',
        person1Id: 'person-1',
        person2Id: 'person-3',
        type: 'biological_parent',
        description: 'New relationship'
      }
    ];
    
    // Re-render with updated relationships
    rerender(
      <>
        <AddRelationshipModal
          isOpen={false}
          onClose={jest.fn()}
          onSubmit={jest.fn()}
          currentPerson={mockPeople[0]}
          selectablePeople={mockPeople}
        />
        <RelationshipTimeline
          relationships={updatedRelationships as any[]}
          people={mockPeopleRecord}
          onEditRelationship={jest.fn()}
          onDeleteRelationship={jest.fn()}
        />
      </>
    );
    
    // Verify timeline is updated
    expect(screen.getByText(/New relationship/i)).toBeInTheDocument();
  });
  
  it('edits a relationship and updates the timeline', async () => {
    // Mock API responses for updating a relationship
    axiosMock.onPut(/\/api\/trees\/test-tree-id\/relationships\/relationship-1/).reply(200, {
      ...mockRelationships[0],
      description: 'Updated relationship description'
    });
    
    // Setup mock handlers
    const handleEdit = jest.fn();
    
    // Render timeline with mock relationships
    const { rerender } = render(
      <RelationshipTimeline
        relationships={mockRelationships}
        people={mockPeopleRecord}
        onEditRelationship={handleEdit}
        onDeleteRelationship={jest.fn()}
      />
    );
    
    // Click edit on the first relationship
    const editButtons = screen.getAllByLabelText(/Edit relationship/i);
    fireEvent.click(editButtons[0]);
    
    // Verify edit handler was called with correct ID
    expect(handleEdit).toHaveBeenCalledWith('relationship-1');
    
    // Now render the edit form
    rerender(
      <RelationshipDetailsForm
        selectablePeople={mockPeople}
        initialData={{
          ...mockRelationships[0],
          startDate: mockRelationships[0].startDate ? new Date(mockRelationships[0].startDate) : undefined,
          endDate: mockRelationships[0].endDate ? new Date(mockRelationships[0].endDate) : undefined
        }}
        onSubmit={async (data) => {
          await axiosMock.onPut(/\/api\/trees\/test-tree-id\/relationships\/relationship-1/).reply(200, {
            ...data,
            id: 'relationship-1'
          });
        }}
      />
    );
    
    // Go to details tab
    fireEvent.click(screen.getByText(/Details/i));
    
    // Update description
    const descriptionInput = screen.getByLabelText(/Description/i);
    fireEvent.change(descriptionInput, { target: { value: 'Updated relationship description' } });
    
    // Submit the form
    fireEvent.click(screen.getByText(/Save/i));
    
    // Wait for API call to complete
    await waitFor(() => {
      expect(axiosMock.history.put.length).toBe(1);
    });
    
    // Create updated relationships
    const updatedRelationships = [
      {
        ...mockRelationships[0],
        description: 'Updated relationship description'
      },
      ...mockRelationships.slice(1)
    ];
    
    // Re-render timeline with updated data
    rerender(
      <RelationshipTimeline
        relationships={updatedRelationships}
        people={mockPeopleRecord}
        onEditRelationship={handleEdit}
        onDeleteRelationship={jest.fn()}
      />
    );
    
    // Verify timeline is updated
    expect(screen.getByText(/Updated relationship description/i)).toBeInTheDocument();
  });
  
  it('deletes a relationship and updates the timeline', async () => {
    // Mock API responses for deleting a relationship
    axiosMock.onDelete(/\/api\/trees\/test-tree-id\/relationships\/relationship-1/).reply(204);
    
    // Setup delete handler
    const handleDelete = jest.fn(async (id) => {
      await axiosMock.onDelete(`/api/trees/test-tree-id/relationships/${id}`).reply(204);
      return true;
    });
    
    // Render timeline with mock relationships
    const { rerender } = render(
      <RelationshipTimeline
        relationships={mockRelationships}
        people={mockPeopleRecord}
        onEditRelationship={jest.fn()}
        onDeleteRelationship={handleDelete}
      />
    );
    
    // Find and click the delete button for first relationship
    const deleteButtons = screen.getAllByLabelText(/Delete relationship/i);
    fireEvent.click(deleteButtons[0]);
    
    // Confirm deletion in the dialog
    fireEvent.click(screen.getByText(/Confirm/i));
    
    // Verify delete handler was called with correct ID
    expect(handleDelete).toHaveBeenCalledWith('relationship-1');
    
    // Wait for API call to complete
    await waitFor(() => {
      expect(axiosMock.history.delete.length).toBe(1);
    });
    
    // Re-render timeline without the deleted relationship
    rerender(
      <RelationshipTimeline
        relationships={mockRelationships.slice(1)}
        people={mockPeopleRecord}
        onEditRelationship={jest.fn()}
        onDeleteRelationship={handleDelete}
      />
    );
    
    // The deleted relationship should no longer be present
    expect(screen.queryByText(/Married in Central Park/i)).not.toBeInTheDocument();
  });
});
