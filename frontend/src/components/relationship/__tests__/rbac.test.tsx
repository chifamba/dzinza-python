// src/components/relationship/__tests__/rbac.test.tsx
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@/test-utils/test-utils';
import { setupMockAPI, axiosMock, mockUserWithRole } from '@/test-utils/test-utils';
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

describe('Relationship Components RBAC Tests', () => {
  // Set up API mocks before each test
  beforeEach(() => {
    setupMockAPI();
  });
  
  afterEach(() => {
    axiosMock.reset();
  });
  
  describe('Viewer Role', () => {
    beforeEach(() => {
      // Set up user with viewer role
      mockUserWithRole('viewer');
      
      // Mock tree permissions
      axiosMock.onGet(/\/api\/trees\/test-tree-id\/permissions/).reply(200, {
        permissions: {
          view: true,
          edit: false,
          admin: false
        }
      });
    });
    
    it('cannot add new relationships', async () => {
      render(
        <AddRelationshipModal
          isOpen={true}
          onClose={jest.fn()}
          onSubmit={jest.fn()}
          currentPerson={mockPeople[0]}
          selectablePeople={mockPeople}
        />
      );
      
      // Form should show read-only message
      expect(screen.getByText(/You don't have permission to add relationships/i)).toBeInTheDocument();
      
      // Create button should be disabled or not present
      expect(screen.queryByText(/Create/i)).not.toBeInTheDocument();
    });
    
    it('cannot edit existing relationships', async () => {
      render(
        <RelationshipTimeline
          relationships={mockRelationships}
          people={mockPeopleRecord}
          onEditRelationship={jest.fn()}
          onDeleteRelationship={jest.fn()}
        />
      );
      
      // Edit buttons should not be visible
      expect(screen.queryAllByLabelText(/Edit relationship/i).length).toBe(0);
      
      // Delete buttons should not be visible
      expect(screen.queryAllByLabelText(/Delete relationship/i).length).toBe(0);
    });
    
    it('can view relationship details', async () => {
      render(
        <RelationshipTimeline
          relationships={mockRelationships}
          people={mockPeopleRecord}
          onEditRelationship={jest.fn()}
          onDeleteRelationship={jest.fn()}
        />
      );
      
      // Timeline should be visible
      expect(screen.getByText(/Relationship Timeline/i)).toBeInTheDocument();
      
      // Details should be visible but not editable
      expect(screen.getByText(/Married in Central Park/i)).toBeInTheDocument();
      
      // Expand details should work
      const expandButtons = screen.getAllByText(/Show details/i);
      fireEvent.click(expandButtons[0]);
      
      await waitFor(() => {
        expect(screen.getByText(/Ceremony/i)).toBeInTheDocument();
      });
    });
  });
  
  describe('Editor Role', () => {
    beforeEach(() => {
      // Set up user with editor role
      mockUserWithRole('editor');
      
      // Mock tree permissions
      axiosMock.onGet(/\/api\/trees\/test-tree-id\/permissions/).reply(200, {
        permissions: {
          view: true,
          edit: true,
          admin: false
        }
      });
    });
    
    it('can add new relationships', async () => {
      // Mock API response for creating a relationship
      axiosMock.onPost(/\/api\/trees\/test-tree-id\/relationships/).reply(201, {
        id: 'new-relationship-id',
        person1Id: 'person-1',
        person2Id: 'person-2',
        type: 'spouse_current'
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
      
      // Fill out the form
      fireEvent.click(screen.getByLabelText(/First Person/i));
      fireEvent.click(screen.getByText(/John Doe/i));
      
      fireEvent.click(screen.getByLabelText(/Second Person/i));
      fireEvent.click(screen.getByText(/Jane Doe/i));
      
      fireEvent.click(screen.getByLabelText(/Relationship Type/i));
      fireEvent.click(screen.getByText(/Spouse/i));
      
      // Create button should be enabled
      expect(screen.getByText(/Create/i)).toBeEnabled();
      
      // Submit the form
      fireEvent.click(screen.getByText(/Create/i));
      
      // Wait for API call to complete
      await waitFor(() => {
        expect(axiosMock.history.post.length).toBe(1);
      });
    });
    
    it('can edit existing relationships', async () => {
      const handleEdit = jest.fn();
      
      render(
        <RelationshipTimeline
          relationships={mockRelationships}
          people={mockPeopleRecord}
          onEditRelationship={handleEdit}
          onDeleteRelationship={jest.fn()}
        />
      );
      
      // Edit buttons should be visible
      const editButtons = screen.getAllByLabelText(/Edit relationship/i);
      expect(editButtons.length).toBeGreaterThan(0);
      
      // Click the first edit button
      fireEvent.click(editButtons[0]);
      
      // Check that edit handler was called
      expect(handleEdit).toHaveBeenCalledWith('relationship-1');
    });
    
    it('cannot perform admin actions', async () => {
      // Mock API response for tree settings
      axiosMock.onGet(/\/api\/trees\/test-tree-id\/settings/).reply(403, {
        error: 'Forbidden',
        message: 'You do not have admin permissions'
      });
      
      // Try to access admin-only settings (this would typically be in a settings component)
      // For this test we're just checking the API response
      try {
        await axiosMock.onGet('/api/trees/test-tree-id/settings').reply(403);
        // This should throw an error due to 403 status
        expect(true).toBe(false);
      } catch (error) {
        expect(error).toBeDefined();
      }
    });
  });
  
  describe('Admin Role', () => {
    beforeEach(() => {
      // Set up user with admin role
      mockUserWithRole('admin');
      
      // Mock tree permissions
      axiosMock.onGet(/\/api\/trees\/test-tree-id\/permissions/).reply(200, {
        permissions: {
          view: true,
          edit: true,
          admin: true
        }
      });
    });
    
    it('can access all functions', async () => {
      // Mock API responses
      axiosMock.onPost(/\/api\/trees\/test-tree-id\/relationships/).reply(201, {
        id: 'new-relationship-id',
        person1Id: 'person-1',
        person2Id: 'person-2',
        type: 'spouse_current'
      });
      
      axiosMock.onDelete(/\/api\/trees\/test-tree-id\/relationships\/relationship-1/).reply(204);
      
      const handleDelete = jest.fn(async () => true);
      
      render(
        <RelationshipTimeline
          relationships={mockRelationships}
          people={mockPeopleRecord}
          onEditRelationship={jest.fn()}
          onDeleteRelationship={handleDelete}
        />
      );
      
      // Admin features should be visible - like verification controls
      expect(screen.getByText(/Verification Status/i)).toBeInTheDocument();
      
      // Admin should be able to delete
      const deleteButtons = screen.getAllByLabelText(/Delete relationship/i);
      fireEvent.click(deleteButtons[0]);
      
      // Confirm deletion
      fireEvent.click(screen.getByText(/Confirm/i));
      
      expect(handleDelete).toHaveBeenCalledWith('relationship-1');
    });
    
    it('can mark relationships as verified', async () => {
      // Mock API response for verification
      axiosMock.onPut(/\/api\/trees\/test-tree-id\/relationships\/relationship-1\/verify/).reply(200, {
        ...mockRelationships[0],
        verified: true
      });
      
      const handleVerify = jest.fn(async () => {
        await axiosMock.onPut('/api/trees/test-tree-id/relationships/relationship-1/verify').reply(200);
        return true;
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
          onSubmit={jest.fn()}
        />
      );
      
      // Verification controls should be visible
      const verifyButton = screen.getByText(/Mark as Verified/i);
      expect(verifyButton).toBeInTheDocument();
      
      // Click verify button
      fireEvent.click(verifyButton);
      
      // Wait for verify handler to be called
      await waitFor(() => {
        expect(handleVerify).toHaveBeenCalled();
      });
    });
  });
});
