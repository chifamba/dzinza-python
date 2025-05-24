// src/test-utils/__tests__/mock-relationship-timeline.test.js
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { MockRelationshipTimeline } from '../mock-components';

describe('MockRelationshipTimeline Component', () => {
  // Mock data
  const mockRelationships = [
    {
      id: 'rel-1',
      type: 'spouse_current',
      description: 'Married since 2010'
    },
    {
      id: 'rel-2',
      type: 'biological_parent',
      description: 'Parent-child relationship'
    }
  ];
  
  // Mock handlers
  const mockEdit = jest.fn();
  const mockDelete = jest.fn();
  
  // Reset mocks before each test
  beforeEach(() => {
    mockEdit.mockReset();
    mockDelete.mockReset();
  });
  
  test('renders empty state when no relationships', () => {
    render(
      <MockRelationshipTimeline 
        relationships={[]}
        onEdit={mockEdit}
        onDelete={mockDelete}
      />
    );
    
    // Check if empty state is shown
    expect(screen.getByTestId('relationship-timeline')).toBeDefined();
    expect(screen.getByTestId('no-relationships')).toBeDefined();
    expect(screen.getByText('No relationships found')).toBeDefined();
  });
  
  test('renders relationships when provided', () => {
    render(
      <MockRelationshipTimeline 
        relationships={mockRelationships}
        onEdit={mockEdit}
        onDelete={mockDelete}
      />
    );
    
    // Check if relationships are rendered
    expect(screen.getByTestId('relationship-rel-1')).toBeDefined();
    expect(screen.getByTestId('relationship-rel-2')).toBeDefined();
    
    // Check specific relationship content
    expect(screen.getByText('spouse_current')).toBeDefined();
    expect(screen.getByText('Married since 2010')).toBeDefined();
    expect(screen.getByText('biological_parent')).toBeDefined();
    expect(screen.getByText('Parent-child relationship')).toBeDefined();
  });
  
  test('calls edit handler when edit button is clicked', () => {
    render(
      <MockRelationshipTimeline 
        relationships={mockRelationships}
        onEdit={mockEdit}
        onDelete={mockDelete}
      />
    );
    
    // Click edit button for first relationship
    fireEvent.click(screen.getByTestId('edit-rel-1'));
    
    // Check if onEdit was called with correct ID
    expect(mockEdit).toHaveBeenCalledTimes(1);
    expect(mockEdit).toHaveBeenCalledWith('rel-1');
  });
  
  test('calls delete handler when delete button is clicked', () => {
    render(
      <MockRelationshipTimeline 
        relationships={mockRelationships}
        onEdit={mockEdit}
        onDelete={mockDelete}
      />
    );
    
    // Click delete button for second relationship
    fireEvent.click(screen.getByTestId('delete-rel-2'));
    
    // Check if onDelete was called with correct ID
    expect(mockDelete).toHaveBeenCalledTimes(1);
    expect(mockDelete).toHaveBeenCalledWith('rel-2');
  });
});
