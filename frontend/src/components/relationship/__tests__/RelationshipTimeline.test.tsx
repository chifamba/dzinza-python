// src/components/relationship/__tests__/RelationshipTimeline.test.tsx
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@/test-utils/test-utils';
import { RelationshipTimeline } from '@/components/relationship/RelationshipTimeline';
import { mockPeople, mockRelationships } from '@/test-utils/mock-data';
import { Person } from '@/lib/types';

// Transform mockPeople into a Record<string, Person> for RelationshipTimeline
const mockPeopleRecord = mockPeople.reduce((acc, person) => {
  acc[person.id] = person;
  return acc;
}, {} as Record<string, Person>);

describe('RelationshipTimeline', () => {
  // Setup mock functions
  const mockOnEdit = jest.fn();
  const mockOnDelete = jest.fn();
  
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders the timeline with all relationships', () => {
    render(
      <RelationshipTimeline 
        relationships={mockRelationships}
        people={mockPeopleRecord}
        onEditRelationship={mockOnEdit}
        onDeleteRelationship={mockOnDelete}
      />
    );

    // Check for timeline heading
    expect(screen.getByText(/Relationship Timeline/i)).toBeInTheDocument();
    
    // Check for relationship types in the timeline
    expect(screen.getByText(/Married in Central Park/i)).toBeInTheDocument();
    expect(screen.getByText(/Birth of first child/i)).toBeInTheDocument();
    expect(screen.getByText(/Birth of second child/i)).toBeInTheDocument();
    
    // Check for people's names in relationships
    expect(screen.getByText(/John Doe/i)).toBeInTheDocument();
    expect(screen.getByText(/Jane Doe/i)).toBeInTheDocument();
  });

  it('focuses on a specific person when focusPersonId is provided', () => {
    render(
      <RelationshipTimeline 
        relationships={mockRelationships}
        people={mockPeopleRecord}
        focusPersonId="person-1"
        onEditRelationship={mockOnEdit}
        onDeleteRelationship={mockOnDelete}
      />
    );
    
    // Should show focused view title
    expect(screen.getByText(/John Doe's Relationships/i)).toBeInTheDocument();
    
    // Should show all relationships for person-1
    expect(screen.getAllByText(/John Doe/i).length).toBeGreaterThan(1);
  });
  
  it('filters relationships by type when filter is applied', async () => {
    render(
      <RelationshipTimeline 
        relationships={mockRelationships}
        people={mockPeopleRecord}
        onEditRelationship={mockOnEdit}
        onDeleteRelationship={mockOnDelete}
      />
    );
    
    // Open the filter dropdown
    fireEvent.click(screen.getByText(/Filter/i));
    
    // Select spouse relationship type
    fireEvent.click(screen.getByText(/Spouse/i));
    
    await waitFor(() => {
      // Should only show spouse relationships
      expect(screen.getByText(/Married in Central Park/i)).toBeInTheDocument();
      // Shouldn't show parent-child relationships
      const parentChildRelationships = screen.queryAllByText(/Birth of/i);
      expect(parentChildRelationships.length).toBe(0);
    });
  });
  
  it('calls onEdit when edit button is clicked', async () => {
    render(
      <RelationshipTimeline 
        relationships={mockRelationships}
        people={mockPeopleRecord}
        onEditRelationship={mockOnEdit}
        onDeleteRelationship={mockOnDelete}
      />
    );
    
    // Find and click the edit button
    const editButtons = screen.getAllByLabelText(/Edit relationship/i);
    fireEvent.click(editButtons[0]);
    
    expect(mockOnEdit).toHaveBeenCalledTimes(1);
    expect(mockOnEdit).toHaveBeenCalledWith(expect.any(String)); // Called with relationship id
  });
  
  it('calls onDelete when delete button is clicked and confirmed', async () => {
    render(
      <RelationshipTimeline 
        relationships={mockRelationships}
        people={mockPeopleRecord}
        onEditRelationship={mockOnEdit}
        onDeleteRelationship={mockOnDelete}
      />
    );
    
    // Find and click the delete button
    const deleteButtons = screen.getAllByLabelText(/Delete relationship/i);
    fireEvent.click(deleteButtons[0]);
    
    // Confirm deletion in the dialog
    fireEvent.click(screen.getByText(/Confirm/i));
    
    expect(mockOnDelete).toHaveBeenCalledTimes(1);
    expect(mockOnDelete).toHaveBeenCalledWith(expect.any(String)); // Called with relationship id
  });
  
  it('shows custom attributes when expanded', async () => {
    render(
      <RelationshipTimeline 
        relationships={mockRelationships}
        people={mockPeopleRecord}
        onEditRelationship={mockOnEdit}
        onDeleteRelationship={mockOnDelete}
      />
    );
    
    // Find and click expand details button for relationship with custom attributes
    const expandButtons = screen.getAllByText(/Show details/i);
    fireEvent.click(expandButtons[0]);
    
    await waitFor(() => {
      expect(screen.getByText(/Ceremony/i)).toBeInTheDocument();
      expect(screen.getByText(/Traditional/i)).toBeInTheDocument();
      expect(screen.getByText(/Witnesses/i)).toBeInTheDocument();
      expect(screen.getByText(/Robert Smith, Mary Johnson/i)).toBeInTheDocument();
    });
  });
  
  it('shows verification badge for verified relationships', () => {
    // Add a verified property to the first relationship
    const verifiedRelationships = [
      { ...mockRelationships[0], verified: true },
      ...mockRelationships.slice(1)
    ];
    
    render(
      <RelationshipTimeline 
        relationships={verifiedRelationships}
        people={mockPeopleRecord}
        onEditRelationship={mockOnEdit}
        onDeleteRelationship={mockOnDelete}
      />
    );
    
    expect(screen.getByText(/Verified/i)).toBeInTheDocument();
  });
});
