import { describe, it, expect, vi, beforeEach } from 'vitest';
// Import specific functions and types you want to test
import { getTreeData, Person, Relationship } from './apiService';

// Mock global fetch if your apiService actually uses fetch.
// If apiService directly returns mock data (as it does now), this won't be hit by those functions.
global.fetch = vi.fn();

function createFetchResponse<T>(data: T, ok = true, status = 200) {
  return Promise.resolve({
    ok,
    status,
    json: () => Promise.resolve(data),
  } as Response);
}

describe('apiService', () => {
  beforeEach(() => {
    // Reset all mocks before each test
    vi.resetAllMocks();
  });

  describe('getTreeData', () => {
    it('should return the mock data defined in apiService.ts', async () => {
      const treeId = 'anyTreeId';
      // This test currently relies on getTreeData returning its own internal mock data.
      // If getTreeData were to be refactored to use fetch, this test would need to change
      // to mock the fetch call.
      const result = await getTreeData(treeId);

      expect(result.persons).toBeInstanceOf(Array);
      expect(result.persons.length).toBeGreaterThan(0); // Based on current mock data in apiService
      expect(result.persons[0].id).toBe('p1'); // Check specific mock data
      expect(result.relationships).toBeInstanceOf(Array);
      expect(result.relationships.length).toBeGreaterThan(0);

      // If getTreeData was using fetch, the test would look like:
      // const mockApiResponse = { persons: [{ id: 'p1', name: 'Fetched Person' }], relationships: [] };
      // (fetch as vi.Mock).mockResolvedValue(createFetchResponse(mockApiResponse));
      // const result = await getTreeData(treeId);
      // expect(fetch).toHaveBeenCalledWith(`/api/trees/${treeId}`);
      // expect(result).toEqual(mockApiResponse);
      console.log("Note: getTreeData test verifies the direct mock return from apiService.ts.");
    });

    // Example for testing a function that uses fetch (if apiService is refactored)
    // it('handles error when fetching tree data fails (if using fetch)', async () => {
    //   const treeId = 'testTreeError';
    //   (fetch as vi.Mock).mockResolvedValue(createFetchResponse(null, false, 500));
    //
    //   // To test this, getTreeData would need to actually use fetch and throw an error on !response.ok
    //   // await expect(getTreeData(treeId)).rejects.toThrow('Failed to fetch tree data');
    // });
  });

  // Add tests for addPerson, updatePerson, deletePerson,
  // addRelationship, updateRelationship, deleteRelationship,
  // getTreeLayout, saveTreeLayout as they are implemented or refactored to use fetch.
});
