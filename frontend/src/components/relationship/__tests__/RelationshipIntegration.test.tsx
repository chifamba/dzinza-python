/**
 * @jest-environment jsdom
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import axios from 'axios';
import MockAdapter from 'axios-mock-adapter';
import { RelationshipDetailsForm } from '../../components/relationship/RelationshipDetailsForm';
import { RelationshipTimeline } from '../../components/relationship/RelationshipTimeline'; 
import { mockPeople, mockRelationships } from '../../test-utils/mock-data';

// Create axios mock
const mockAxios = new MockAdapter(axios);

describe('Relationship Components API Integration', () => {
  // Mock data
  const treeId = 'tree-123';
  const relationshipId = 'rel-123';
  const apiBaseUrl = 'http://localhost:8090/api'; 
  
  // Setup and cleanup
  beforeEach(() => {
    mockAxios.reset();
  });
  
  afterAll(() => {
    mockAxios.restore();
  });
  
  describe('Error Handling', () => {
    test('RelationshipDetailsForm handles API errors gracefully on submission', async () => {
      // Mock API error
      mockAxios.onPost(`${apiBaseUrl}/trees/${treeId}/relationships`).reply(500, {
        message: 'Internal server error'
      });
      
      // Mock handlers
      const onSubmit = jest.fn(async (data) => {
        try {
          await axios.post(`${apiBaseUrl}/trees/${treeId}/relationships`, data);
          return true;
        } catch (error) {
          // Return the error for testing
          return error;
        }
      });
      
      const onError = jest.fn();
      
      // Render with error handler
      render(
        <RelationshipDetailsForm
          selectablePeople={mockPeople}
          onSubmit={onSubmit}
          onError={onError}
        />
      );
      
      // Fill form with minimum required data
      const user = userEvent.setup();
      
      // Select first person (implementation depends on component UI)
      await user.click(screen.getByLabelText(/First Person/i));
      await user.click(screen.getByText(mockPeople[0].name));
      
      // Select second person
      await user.click(screen.getByLabelText(/Second Person/i));
      await user.click(screen.getByText(mockPeople[1].name));
      
      // Select relationship type
      await user.click(screen.getByLabelText(/Relationship Type/i));
      await user.click(screen.getByText(/Current Spouse/i));
      
      // Submit form
      await user.click(screen.getByRole('button', { name: /Save Relationship/i }));
      
      // Wait for submission and error handling
      await waitFor(() => {
        expect(onSubmit).toHaveBeenCalled();
        expect(onError).toHaveBeenCalledWith(expect.objectContaining({
          response: expect.objectContaining({
            status: 500
          })
        }));
      });
    });
    
    test('RelationshipTimeline handles API errors when fetching relationships', async () => {
      // Mock API error
      mockAxios.onGet(`${apiBaseUrl}/trees/${treeId}/relationships`).reply(404, {
        message: 'Relationships not found'
      });
      
      // Mock functions
      const onLoadError = jest.fn();
      
      // Create a wrapper component that handles API calls
      const RelationshipTimelineWrapper = () => {
        const [relationships, setRelationships] = React.useState([]);
        const [error, setError] = React.useState(null);
        const [loading, setLoading] = React.useState(true);
        
        React.useEffect(() => {
          const fetchRelationships = async () => {
            try {
              const response = await axios.get(`${apiBaseUrl}/trees/${treeId}/relationships`);
              setRelationships(response.data);
            } catch (err) {
              setError(err);
              onLoadError(err);
            } finally {
              setLoading(false);
            }
          };
          
          fetchRelationships();
        }, []);
        
        if (loading) return <div>Loading...</div>;
        if (error) return <div data-testid="error-message">Error loading relationships</div>;
        
        return (
          <RelationshipTimeline
            relationships={relationships}
            people={mockPeople}
          />
        );
      };
      
      // Render the wrapper
      render(<RelationshipTimelineWrapper />);
      
      // Check that error message is displayed
      await waitFor(() => {
        expect(screen.getByTestId('error-message')).toBeInTheDocument();
        expect(onLoadError).toHaveBeenCalledWith(expect.objectContaining({
          response: expect.objectContaining({
            status: 404
          })
        }));
      });
    });
  });
  
  describe('RBAC Testing', () => {
    test('RelationshipDetailsForm respects read-only permission', async () => {
      // Mock data for a user with read-only permission
      const permissionsData = {
        canEdit: false,
        canDelete: false
      };
      
      // Render with read-only permissions
      render(
        <RelationshipDetailsForm
          selectablePeople={mockPeople}
          initialData={mockRelationships[0]}
          permissions={permissionsData}
        />
      );
      
      // All form fields should be disabled
      expect(screen.getByLabelText(/First Person/i)).toBeDisabled();
      expect(screen.getByLabelText(/Second Person/i)).toBeDisabled();
      expect(screen.getByLabelText(/Relationship Type/i)).toBeDisabled();
      
      // Save button should be disabled or not rendered
      const saveButton = screen.queryByRole('button', { name: /Save Relationship/i });
      if (saveButton) {
        expect(saveButton).toBeDisabled();
      } else {
        expect(screen.queryByRole('button', { name: /Save Relationship/i })).not.toBeInTheDocument();
      }
    });
    
    test('RelationshipTimeline shows edit/delete buttons only for users with permission', async () => {
      // Test with different permission scenarios
      const permissionScenarios = [
        { canEdit: true, canDelete: true, description: 'Full permissions' },
        { canEdit: true, canDelete: false, description: 'Edit only' },
        { canEdit: false, canDelete: false, description: 'Read only' }
      ];
      
      for (const scenario of permissionScenarios) {
        render(
          <RelationshipTimeline
            relationships={mockRelationships}
            people={mockPeople}
            permissions={scenario}
          />
        );
        
        if (scenario.canEdit) {
          expect(screen.getAllByLabelText(/Edit relationship/i).length).toBeGreaterThan(0);
        } else {
          expect(screen.queryAllByLabelText(/Edit relationship/i).length).toBe(0);
        }
        
        if (scenario.canDelete) {
          expect(screen.getAllByLabelText(/Delete relationship/i).length).toBeGreaterThan(0);
        } else {
          expect(screen.queryAllByLabelText(/Delete relationship/i).length).toBe(0);
        }
        
        // Cleanup
        cleanup();
      }
    });
  });
  
  describe('API Integration', () => {
    test('Successfully creates relationship via API', async () => {
      // Mock successful API response
      const mockResponse = {
        id: relationshipId,
        person1Id: mockPeople[0].id,
        person2Id: mockPeople[1].id,
        type: 'spouse_current',
        startDate: '2023-01-01',
        description: 'Test relationship'
      };
      
      mockAxios.onPost(`${apiBaseUrl}/trees/${treeId}/relationships`).reply(201, mockResponse);
      
      // Mock handlers
      const onSubmit = jest.fn(async (data) => {
        const response = await axios.post(`${apiBaseUrl}/trees/${treeId}/relationships`, data);
        return response.data;
      });
      
      const onSuccess = jest.fn();
      
      // Render the form
      render(
        <RelationshipDetailsForm
          selectablePeople={mockPeople}
          onSubmit={onSubmit}
          onSuccess={onSuccess}
          treeId={treeId}
        />
      );
      
      // Fill and submit the form
      const user = userEvent.setup();
      
      // Select people and relationship type
      await user.click(screen.getByLabelText(/First Person/i));
      await user.click(screen.getByText(mockPeople[0].name));
      
      await user.click(screen.getByLabelText(/Second Person/i));
      await user.click(screen.getByText(mockPeople[1].name));
      
      await user.click(screen.getByLabelText(/Relationship Type/i));
      await user.click(screen.getByText(/Current Spouse/i));
      
      // Submit the form
      await user.click(screen.getByRole('button', { name: /Save Relationship/i }));
      
      // Verify API was called and success handler triggered
      await waitFor(() => {
        expect(onSubmit).toHaveBeenCalled();
        expect(onSuccess).toHaveBeenCalledWith(mockResponse);
      });
    });
    
    test('Successfully deletes relationship via API', async () => {
      // Mock successful deletion
      mockAxios.onDelete(`${apiBaseUrl}/trees/${treeId}/relationships/${relationshipId}`).reply(204);
      
      // Mock handlers
      const onDelete = jest.fn(async (id) => {
        await axios.delete(`${apiBaseUrl}/trees/${treeId}/relationships/${id}`);
        return true;
      });
      
      // Render timeline with delete functionality
      render(
        <RelationshipTimeline
          relationships={[{ ...mockRelationships[0], id: relationshipId }]}
          people={mockPeople}
          onDelete={onDelete}
          treeId={treeId}
        />
      );
      
      // Find and click delete button
      const user = userEvent.setup();
      await user.click(screen.getByLabelText(/Delete relationship/i));
      
      // Confirm deletion (if there's a confirmation dialog)
      await user.click(screen.getByText(/Confirm/i));
      
      // Verify API was called
      await waitFor(() => {
        expect(onDelete).toHaveBeenCalledWith(relationshipId);
        expect(mockAxios.history.delete.length).toBe(1);
      });
    });
  });
});
