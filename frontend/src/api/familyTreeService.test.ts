import {
  getFamilyTree,
  updatePersonOrder,
  addPerson,
  updatePerson,
} from './familyTreeService';
import { Person } from '../types';
import config from '../config';
import { mockPersons } from '../data/mockData';

// Mock global fetch
global.fetch = jest.fn();

// Mock config
jest.mock('../config', () => ({
  __esModule: true,
  default: {
    backendUrl: 'http://localhost:8080',
    useMockData: false, // Default to false for API call tests
  },
}));

describe('familyTreeService', () => {
  beforeEach(() => {
    // Reset fetch mock and config before each test
    (fetch as jest.Mock).mockClear();
    config.useMockData = false; // Ensure API calls are tested by default
    // Reset mockPersons for consistent mock data tests
    // This is a shallow copy; if tests modify objects within mockPersons deeply, a deep copy might be needed.
    // For current tests, this should suffice.
    mockPersons.splice(0, mockPersons.length, ...[
      { id: '1', firstName: 'John', lastName: 'Doe', displayOrder: 0, name: "John Doe" },
      { id: '2', firstName: 'Jane', lastName: 'Doe', displayOrder: 1, name: "Jane Doe" },
      { id: '3', firstName: 'Peter', lastName: 'Pan', displayOrder: 2, name: "Peter Pan" },
    ] as Person[]);
  });

  describe('getFamilyTree', () => {
    it('should fetch and sort persons by displayOrder', async () => {
      const unsortedPersons = [
        { id: '2', first_name: 'Jane', last_name: 'Doe', display_order: 1 },
        { id: '1', first_name: 'John', last_name: 'Doe', display_order: 0 },
      ];
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => unsortedPersons,
      });

      const persons = await getFamilyTree();
      expect(fetch).toHaveBeenCalledWith('http://localhost:8080/api/people');
      expect(persons).toHaveLength(2);
      expect(persons[0].id).toBe('1'); // John should be first due to displayOrder: 0
      expect(persons[1].id).toBe('2'); // Jane second
    });

    it('should handle fetch error for getFamilyTree', async () => {
      (fetch as jest.Mock).mockRejectedValueOnce(new Error('API error'));
      const persons = await getFamilyTree();
      expect(persons).toEqual([]);
    });

    it('should return mock data for getFamilyTree when useMockData is true', async () => {
      config.useMockData = true;
      const persons = await getFamilyTree();
      // mockPersons by default are already sorted by displayOrder in this test setup
      expect(persons).toEqual(mockPersons);
      expect(fetch).not.toHaveBeenCalled();
    });
  });

  describe('updatePersonOrder', () => {
    const orderedPersons: Person[] = [
      { id: '1', name: 'Person 1', displayOrder: 0, firstName: "Person", lastName: "1" },
      { id: '2', name: 'Person 2', displayOrder: 1, firstName: "Person", lastName: "2" },
    ];

    it('should send a PUT request with correct payload for updatePersonOrder', async () => {
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
      });

      const success = await updatePersonOrder(orderedPersons);
      expect(success).toBe(true);
      expect(fetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/people/order',
        expect.objectContaining({
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify([
            { id: '1', display_order: 0 },
            { id: '2', display_order: 1 },
          ]),
        })
      );
    });

    it('should return false on API error for updatePersonOrder', async () => {
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        text: async () => 'API Error',
      });
      const success = await updatePersonOrder(orderedPersons);
      expect(success).toBe(false);
    });

    it('should return false on network error for updatePersonOrder', async () => {
      (fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));
      const success = await updatePersonOrder(orderedPersons);
      expect(success).toBe(false);
    });

    it('should handle mock data for updatePersonOrder when useMockData is true', async () => {
      config.useMockData = true;
      const newOrder: Person[] = [
        mockPersons.find(p => p.id === '2')!,
        mockPersons.find(p => p.id === '1')!,
      ].map((p, index) => ({ ...p, displayOrder: index }));

      const success = await updatePersonOrder(newOrder);
      expect(success).toBe(true);
      expect(mockPersons.find(p => p.id === '2')?.displayOrder).toBe(0);
      expect(mockPersons.find(p => p.id === '1')?.displayOrder).toBe(1);
      // Verify the main mockPersons array is sorted
      expect(mockPersons[0].id).toBe('2');
      expect(mockPersons[1].id).toBe('1');
      expect(fetch).not.toHaveBeenCalled();
    });
  });

  describe('addPerson', () => {
    it('should assign displayOrder when adding person with mock data', async () => {
        config.useMockData = true;
        const newPersonData: Omit<Person, 'id'> = {
            firstName: 'Test', lastName: 'User',
            displayOrder: mockPersons.length // Simulate frontend logic for new person
        };
        const newPerson = await addPerson(newPersonData);
        expect(newPerson).not.toBeNull();
        expect(newPerson?.displayOrder).toBe(mockPersons.length -1); // mockPersons was modified by addPerson
                                                                  // and newPerson is last
    });
  });

  describe('updatePerson', () => {
    it('should update displayOrder when updating person with mock data', async () => {
        config.useMockData = true;
        const personToUpdate = mockPersons[0]; // e.g., John Doe with displayOrder 0
        const updatedData: Partial<Person> = { displayOrder: 5 };

        const updatedPerson = await updatePerson(personToUpdate.id, updatedData);
        expect(updatedPerson).not.toBeNull();
        expect(updatedPerson?.displayOrder).toBe(5);
        // Check if the main mockPersons array is re-sorted if displayOrder was changed
        // This depends on updatePerson's mock implementation re-sorting.
        // The familyTreeService.ts mock for updatePerson does re-sort.
        expect(mockPersons.find(p => p.id === personToUpdate.id)?.displayOrder).toBe(5);
    });
  });

});
