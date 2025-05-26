import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ReactFlowProvider } from 'reactflow'; // Needed because useReactFlow is used internally

import FamilyTreeVisualization from './FamilyTreeVisualization';
import api from '../api';

// Mock the api module
jest.mock('../api');

// Mock PersonNode to simplify rendering and avoid complex canvas rendering in tests
jest.mock('./PersonNode', () => ({ personId, data }) => (
  <div data-testid={`person-node-${data.id || personId}`}>
    {data.label}
  </div>
));

// Mock ResizeObserver, often needed for React Flow components
global.ResizeObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));


describe('FamilyTreeVisualization', () => {
  const activeTreeId = 'test-tree-id';

  const mockInitialPageData = {
    nodes: [
      { id: 'node1', type: 'personNode', data: { id: 'node1', label: 'Person 1' } },
      { id: 'node2', type: 'personNode', data: { id: 'node2', label: 'Person 2' } },
    ],
    links: [{ id: 'link1', source: 'node1', target: 'node2', type: 'smoothstep', data: {} }],
    pagination: {
      current_page: 1,
      per_page: 2,
      total_items: 4, // Total 4 items, so 2 pages
      total_pages: 2,
      has_next_page: true,
      has_prev_page: false,
    },
  };

  const mockSecondPageData = {
    nodes: [
      { id: 'node3', type: 'personNode', data: { id: 'node3', label: 'Person 3' } },
      { id: 'node4', type: 'personNode', data: { id: 'node4', label: 'Person 4' } },
    ],
    links: [{ id: 'link2', source: 'node3', target: 'node4', type: 'smoothstep', data: {} }],
    pagination: {
      current_page: 2,
      per_page: 2,
      total_items: 4,
      total_pages: 2,
      has_next_page: false, // This is the last page
      has_prev_page: true,
    },
  };
  
  const renderComponent = () => {
    // Wrap with ReactFlowProvider as useReactFlow is used by the component
    return render(
      <ReactFlowProvider>
        <FamilyTreeVisualization activeTreeId={activeTreeId} />
      </ReactFlowProvider>
    );
  };

  beforeEach(() => {
    // Reset mocks before each test
    jest.clearAllMocks();
    api.getTreeData.mockResolvedValue(mockInitialPageData); // Default mock
  });

  test('initial load: fetches and renders first page of data, shows Load More button', async () => {
    renderComponent();

    // Verify loading state (initial)
    expect(screen.getByText(/Loading family tree visualization.../i)).toBeInTheDocument();

    // Wait for data to load and component to update
    await waitFor(() => {
      expect(api.getTreeData).toHaveBeenCalledWith(activeTreeId, 1, 20); // page 1, default perPage
    });
    
    await waitFor(() => {
      expect(screen.getByTestId('person-node-node1')).toHaveTextContent('Person 1');
      expect(screen.getByTestId('person-node-node2')).toHaveTextContent('Person 2');
    });
    
    // Check for Load More button
    // The button text includes node count, so we wait for it to be updated
    await waitFor(() => {
        const loadMoreButton = screen.getByRole('button', { name: /Load More People \(2\/4\)/i });
        expect(loadMoreButton).toBeInTheDocument();
        expect(loadMoreButton).not.toBeDisabled();
    });
  });

  test('"Load More" functionality: fetches and renders second page, updates state and button', async () => {
    renderComponent();

    // Wait for initial load
    await waitFor(() => {
      expect(api.getTreeData).toHaveBeenCalledTimes(1); // Initial call
      expect(screen.getByTestId('person-node-node1')).toBeInTheDocument();
    });
    
    // Configure mock for the second page load
    api.getTreeData.mockResolvedValue(mockSecondPageData);

    const loadMoreButton = await screen.findByRole('button', { name: /Load More People \(2\/4\)/i });
    fireEvent.click(loadMoreButton);

    // Verify loading state for "load more"
    expect(await screen.findByText(/Loading more.../i)).toBeInTheDocument();
    
    // Wait for second page data to load
    await waitFor(() => {
      expect(api.getTreeData).toHaveBeenCalledWith(activeTreeId, 2, 20); // page 2
    });

    // Check that new nodes are rendered alongside old ones
    await waitFor(() => {
      expect(screen.getByTestId('person-node-node1')).toHaveTextContent('Person 1');
      expect(screen.getByTestId('person-node-node2')).toHaveTextContent('Person 2');
      expect(screen.getByTestId('person-node-node3')).toHaveTextContent('Person 3');
      expect(screen.getByTestId('person-node-node4')).toHaveTextContent('Person 4');
    });

    // Check that "Load More" button is hidden (or shows "all loaded") as it's the last page
    await waitFor(() => {
        // Button should be gone, and "All people loaded" message should appear
        expect(screen.queryByRole('button', { name: /Load More People/i })).not.toBeInTheDocument();
        expect(screen.getByText(/All people loaded \(4\)\./i)).toBeInTheDocument();
    });
  });


  test('loading states: shows indicators during initial load and "Load More"', async () => {
    renderComponent();

    // Initial loading
    expect(screen.getByText(/Loading family tree visualization.../i)).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText(/Loading family tree visualization.../i)).not.toBeInTheDocument()); // Waits for initial load to complete

    // "Load More" loading
    api.getTreeData.mockResolvedValue(mockSecondPageData); // Prepare for next call
    const loadMoreButton = await screen.findByRole('button', { name: /Load More People/i });
    fireEvent.click(loadMoreButton);
    
    expect(await screen.findByText(/Loading more.../i)).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText(/Loading more.../i)).not.toBeInTheDocument()); // Waits for load more to complete
  });

  test('error handling: displays error message if api.getTreeData fails on initial load', async () => {
    const errorMessage = 'Network Error';
    api.getTreeData.mockRejectedValueOnce(new Error(errorMessage)); // Simulate API error

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText(/Error loading visualization:/i)).toBeInTheDocument();
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });
  });
  
  test('error handling: displays error message near button if api.getTreeData fails on "Load More"', async () => {
    // Initial load successful
    api.getTreeData.mockResolvedValueOnce(mockInitialPageData);
    renderComponent();
    await waitFor(() => expect(screen.getByTestId('person-node-node1')).toBeInTheDocument());

    // Subsequent load fails
    const loadMoreErrorMessage = 'Failed to fetch next page';
    api.getTreeData.mockRejectedValueOnce(new Error(loadMoreErrorMessage));

    const loadMoreButton = await screen.findByRole('button', { name: /Load More People/i });
    fireEvent.click(loadMoreButton);

    await waitFor(() => {
      // Check for the error message specific to load more
      expect(screen.getByText(`Error: ${loadMoreErrorMessage}`)).toBeInTheDocument();
    });
    
    // Ensure the main visualization area doesn't get replaced by a full-page error
    expect(screen.getByTestId('person-node-node1')).toBeInTheDocument(); 
    // Load more button might still be visible or change state depending on exact implementation
    expect(screen.getByRole('button', { name: /Load More People/i})).toBeInTheDocument();
  });

});
