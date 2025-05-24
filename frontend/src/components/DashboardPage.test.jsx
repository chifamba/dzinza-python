import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { BrowserRouter } from 'react-router-dom'; // Needed for <Link> components
import DashboardPage from './DashboardPage'; // Adjust path if needed
import api from '../api'; // Mock API

// Mock the API module
jest.mock('../api');

// Mock the FamilyTreeVisualization component
jest.mock('./FamilyTreeVisualization', () => () => <div data-testid="family-tree-viz">Mock Family Tree</div>);

// Helper to render with Router context
const renderDashboard = () => {
  return render(
    <BrowserRouter>
      <DashboardPage />
    </BrowserRouter>
  );
};

describe('DashboardPage Component', () => {
  beforeEach(() => {
    // Reset mocks
    jest.clearAllMocks();
    // Mock successful API calls by default
    api.getAllPeople.mockResolvedValue([
      { id: 'p1', firstName: 'Alice', lastName: 'A', dateOfBirth: '1990-01-01' },
      { id: 'p2', firstName: 'Bob', lastName: 'B', dateOfBirth: '1992-02-02' },
    ]);
    api.getAllRelationships.mockResolvedValue([
      { id: 'r1', person1: 'p1', person2: 'p2', relationshipType: 'spouse' },
    ]);
  });

  test('renders dashboard elements and buttons', () => {
    renderDashboard();

    // Check for buttons
    expect(screen.getByRole('button', { name: /add person/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /add relationship/i })).toBeInTheDocument();

    // Check links associated with buttons
    expect(screen.getByRole('link', { name: /add person/i })).toHaveAttribute('href', '/add-person');
    expect(screen.getByRole('link', { name: /add relationship/i })).toHaveAttribute('href', '/add-relationship');
  });

   test('renders FamilyTreeVisualization component', async () => {
     renderDashboard();

     // The FamilyTreeVisualization mock should be rendered.
     // Since data fetching inside the viz component is mocked away here,
     // we just check for the presence of our mock component.
     await waitFor(() => {
          expect(screen.getByTestId('family-tree-viz')).toBeInTheDocument();
     });
   });

   // Note: Testing the actual data fetching and rendering within
   // FamilyTreeVisualization would require more complex mocking of its
   // internal state and API calls, or testing it in isolation.
   // This test primarily checks if DashboardPage renders its main structure
   // and includes the visualization component.

});
