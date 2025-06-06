import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ReactFlowProvider } from 'reactflow';
import FamilyTreeCanvas from './FamilyTreeCanvas';
import * as apiService from '../services/apiService';

// Mock the entire apiService module
vi.mock('../services/apiService');

const mockedGetTreeData = vi.mocked(apiService.getTreeData);
const mockedGetTreeLayout = vi.mocked(apiService.getTreeLayout);
// Mock other service functions if your component uses them directly e.g. addRelationship
const mockedAddRelationship = vi.mocked(apiService.addRelationship);


describe('FamilyTreeCanvas', () => {
  beforeEach(() => {
    // Reset mocks before each test
    mockedGetTreeData.mockReset();
    mockedGetTreeLayout.mockReset();
    mockedAddRelationship.mockReset(); // Reset if it's used

    // Default successful mock implementations
    mockedGetTreeData.mockResolvedValue({
      persons: [{ id: 'p1', name: 'Mocked Person 1', birthDate: '1990-01-01' }],
      relationships: [],
    });
    mockedGetTreeLayout.mockResolvedValue({
      treeId: 'test-tree',
      positions: [{ id: 'p1', x: 10, y: 20 }],
      zoom: 1,
      offsetX: 0,
      offsetY: 0,
    });
    // Mock addRelationship if it's called during tests (e.g. onConnect)
    mockedAddRelationship.mockResolvedValue({
        id: 'new-rel-1', type: 'parent-child', person1Id: 'p1', person2Id: 'p2' // Corrected type
    });
  });

  it('renders loading state initially when no data is present', () => {
    // Override default mock for this specific test to ensure loading is shown
    mockedGetTreeData.mockImplementation(() => new Promise(() => {})); // Pending promise
    render(
      <ReactFlowProvider>
        <FamilyTreeCanvas treeId="test-tree-loading" />
      </ReactFlowProvider>
    );
    expect(screen.getByText(/Loading family tree.../i)).toBeInTheDocument();
  });

  it('fetches and displays tree data using custom nodes', async () => {
    render(
      <ReactFlowProvider>
        <FamilyTreeCanvas treeId="test-tree" />
      </ReactFlowProvider>
    );

    // Wait for data to be loaded. CustomPersonNode renders name and dates.
    await waitFor(() => {
      // Person name from CustomPersonNode via PersonNodeData
      expect(screen.getByText('Mocked Person 1')).toBeInTheDocument();
      // Birth date from CustomPersonNode
      expect(screen.getByText('B: 1990-01-01')).toBeInTheDocument();
    });

    expect(mockedGetTreeData).toHaveBeenCalledWith('test-tree');
    expect(mockedGetTreeLayout).toHaveBeenCalledWith('test-tree', undefined); // userId is undefined
  });

  it('displays error message if fetching tree data fails', async () => {
    mockedGetTreeData.mockRejectedValueOnce(new Error('Network Error'));
    render(
      <ReactFlowProvider>
        <FamilyTreeCanvas treeId="test-tree-fail" />
      </ReactFlowProvider>
    );
    await waitFor(() => {
      expect(screen.getByText(/Error: Network Error/i)).toBeInTheDocument();
    });
  });

  it('displays error message if fetching layout fails', async () => {
    mockedGetTreeLayout.mockRejectedValueOnce(new Error('Layout Fetch Error'));
    render(
      <ReactFlowProvider>
        <FamilyTreeCanvas treeId="test-layout-fail" />
      </ReactFlowProvider>
    );
    await waitFor(() => {
      expect(screen.getByText(/Error: Layout Fetch Error/i)).toBeInTheDocument();
    });
  });

  // Add more tests for:
  // - User interactions: node click, double click, edge click, pane click
  // - Connecting nodes (onConnect) and verifying if addRelationship is called
  // - Layout saving functionality (mocking node drag, viewport change, button click)
  // - Empty state (no persons in tree)
});
