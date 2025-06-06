// Define basic types for now. These should ideally align with backend models.
export interface Person {
  id: string;
  name: string; // Full name
  firstName?: string;
  lastName?: string;
  birthDate?: string;
  deathDate?: string;
  photoUrl?: string;
  // Other relevant fields like gender, notes, etc.
}

export interface Relationship {
  id:string;
  type: 'parent-child' | 'spouse' | 'sibling'; // Example types
  person1Id: string;
  person2Id: string;
  // Other relevant fields like start_date, end_date for spouse relationship
}

export interface NodePosition {
  id: string; // Corresponds to Person ID
  x: number;
  y: number;
}

export interface TreeLayout {
  treeId: string;
  userId?: string; // Optional, depending on your backend logic
  positions: NodePosition[];
  zoom?: number;
  offsetX?: number;
  offsetY?: number;
}

const API_BASE_URL = '/api'; // Assuming backend is proxied or on the same domain

// --- Tree Data ---
export const getTreeData = async (treeId: string): Promise<{ persons: Person[], relationships: Relationship[] }> => {
  console.log(`[API Service] Fetching tree data for treeId: ${treeId}`);
  // Placeholder: Replace with actual API call
  // const response = await fetch(`${API_BASE_URL}/trees/${treeId}`);
  // if (!response.ok) {
  //   throw new Error('Failed to fetch tree data');
  // }
  // const data = await response.json();
  // return { persons: data.persons, relationships: data.relationships };

  // Mock data for now
  return Promise.resolve({
    persons: [
      { id: 'p1', name: 'John Doe', birthDate: '1970-01-01' },
      { id: 'p2', name: 'Jane Doe', birthDate: '1972-05-10' },
      { id: 'p3', name: 'Peter Doe', birthDate: '2000-10-20' },
      { id: 'p4', name: 'Mary Smith', birthDate: '1975-02-15' },
    ],
    relationships: [
      { id: 'r1', type: 'spouse', person1Id: 'p1', person2Id: 'p2' },
      { id: 'r2', type: 'parent-child', person1Id: 'p1', person2Id: 'p3' },
      { id: 'r3', type: 'parent-child', person1Id: 'p2', person2Id: 'p3' },
    ],
  });
};

// --- Person CRUD ---
export const addPerson = async (treeId: string, personData: Omit<Person, 'id'>): Promise<Person> => {
  console.log('[API Service] Adding person:', personData, 'to treeId:', treeId);
  // const response = await fetch(`${API_BASE_URL}/trees/${treeId}/persons`, {
  //   method: 'POST',
  //   headers: { 'Content-Type': 'application/json' },
  //   body: JSON.stringify(personData),
  // });
  // if (!response.ok) {
  //   throw new Error('Failed to add person');
  // }
  // return response.json();
  const newPerson: Person = { ...personData, id: `new-person-${Date.now()}` };
  return Promise.resolve(newPerson);
};

export const updatePerson = async (personId: string, personData: Partial<Person>): Promise<Person> => {
  console.log(`[API Service] Updating person ${personId}:`, personData);
  // const response = await fetch(`${API_BASE_URL}/persons/${personId}`, {
  //   method: 'PUT',
  //   headers: { 'Content-Type': 'application/json' },
  //   body: JSON.stringify(personData),
  // });
  // if (!response.ok) {
  //   throw new Error('Failed to update person');
  // }
  // return response.json();
  return Promise.resolve({ id: personId, name: 'Updated Name', ...personData } as Person);
};

export const deletePerson = async (personId: string): Promise<void> => {
  console.log(`[API Service] Deleting person ${personId}`);
  // const response = await fetch(`${API_BASE_URL}/persons/${personId}`, {
  //   method: 'DELETE',
  // });
  // if (!response.ok) {
  //   throw new Error('Failed to delete person');
  // }
  return Promise.resolve();
};

// --- Relationship CRUD ---
export const addRelationship = async (treeId: string, relationshipData: Omit<Relationship, 'id'>): Promise<Relationship> => {
  console.log('[API Service] Adding relationship:', relationshipData, 'to treeId:', treeId);
  // ... actual API call
  const newRelationship: Relationship = { ...relationshipData, id: `new-relationship-${Date.now()}` };
  return Promise.resolve(newRelationship);
};

export const updateRelationship = async (relationshipId: string, relationshipData: Partial<Relationship>): Promise<Relationship> => {
  console.log(`[API Service] Updating relationship ${relationshipId}:`, relationshipData);
  // ... actual API call
  return Promise.resolve({ id: relationshipId, type: 'spouse', person1Id: 'p1', person2Id: 'p2', ...relationshipData } as Relationship);
};

export const deleteRelationship = async (relationshipId: string): Promise<void> => {
  console.log(`[API Service] Deleting relationship ${relationshipId}`);
  // ... actual API call
  return Promise.resolve();
};


// --- Tree Layout ---
export const getTreeLayout = async (treeId: string, userId?: string): Promise<TreeLayout | null> => {
  const url = userId ? `${API_BASE_URL}/tree_layouts/${treeId}/${userId}` : `${API_BASE_URL}/tree_layouts/${treeId}`;
  console.log(`[API Service] Fetching tree layout from: ${url}`);
  // const response = await fetch(url);
  // if (response.status === 404) return null; // No layout saved yet
  // if (!response.ok) {
  //   throw new Error('Failed to fetch tree layout');
  // }
  // return response.json();
  return Promise.resolve({
    treeId,
    userId,
    positions: [
      { id: 'p1', x: 50, y: 50 },
      { id: 'p2', x: 50, y: 150 },
      { id: 'p3', x: 250, y: 100 },
    ],
    zoom: 1,
  });
};

export const saveTreeLayout = async (layoutData: TreeLayout): Promise<void> => {
  console.log('[API Service] Saving tree layout:', layoutData);
  // const response = await fetch(`${API_BASE_URL}/tree_layouts`, {
  //   method: 'POST',
  //   headers: { 'Content-Type': 'application/json' },
  //   body: JSON.stringify(layoutData),
  // });
  // if (!response.ok) {
  //   throw new Error('Failed to save tree layout');
  // }
  return Promise.resolve();
};

console.log('API service module loaded.');
