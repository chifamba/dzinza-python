"use server";

import { Person, Relationship, RelationshipType } from '@/lib/types';
import { PersonFormData, RelationshipFormData } from '@/lib/schemas';

// Initial mock data
const initialMockPeople: Person[] = [
  { id: 'p1', name: 'Eleanor Vance', gender: 'Female', birthDate: '1945-03-15', bio: 'Matriarch of the Vance family.' },
  { id: 'p2', name: 'James Holden', gender: 'Male', birthDate: '1942-11-02', deathDate: '2010-07-21', bio: 'Patriarch, loved astronomy.' },
  { id: 'p3', name: 'Sarah Miller', gender: 'Female', birthDate: '1970-06-25', bio: 'Daughter of Eleanor and James.' , imageUrl: 'https://i.pravatar.cc/150?u=p3'},
  { id: 'p4', name: 'David Chen', gender: 'Male', birthDate: '1968-09-01', bio: 'Husband of Sarah.' , imageUrl: 'https://i.pravatar.cc/150?u=p4'},
  { id: 'p5', name: 'Olivia Chen', gender: 'Female', birthDate: '1995-12-12', bio: 'Daughter of Sarah and David.' },
  { id: 'p6', name: 'Michael Brown', gender: 'Male', birthDate: '1972-01-30', bio: 'Brother of Sarah.' },
  { id: 'p7', name: 'Laura Smith', gender: 'Female', birthDate: '1985-07-19', bio: 'Cousin from afar.' },
  { id: 'p8', name: 'Robert Jones', gender: 'Male', birthDate: '1955-02-22', bio: 'Old family friend.' },
  { id: 'p9', name: 'Emily White', gender: 'Female', birthDate: '2000-11-30', bio: 'Niece.' },
  { id: 'p10', name: 'William Green', gender: 'Male', birthDate: '1978-04-05', bio: 'Colleague.' },
  { id: 'p11', name: 'Sophia Black', gender: 'Female', birthDate: '1992-08-14', bio: 'Artist.' },
  { id: 'p12', name: 'Daniel Blue', gender: 'Male', birthDate: '1960-01-01', bio: 'Musician.' },
];

// Mock database (persists during server lifetime)
let mockPeopleDB: Person[] = JSON.parse(JSON.stringify(initialMockPeople));
let nextId = mockPeopleDB.length + 1;

// Mock Relationship Database
let mockRelationshipsDB: Relationship[] = [];
let nextRelationshipId = 1;

export interface GetPeoplePaginatedResponse {
  people: Person[];
  totalCount: number;
  totalPages: number;
  currentPage: number;
}

export async function getPeopleAction(
  page: number = 1,
  limit: number = 5 // Default limit to 5 for easier testing of pagination
): Promise<GetPeoplePaginatedResponse> {
  console.log(`Fetching people from server action (mock DB) - Page: ${page}, Limit: ${limit}`);
  try {
    await new Promise(resolve => setTimeout(resolve, 500));

    const totalCount = mockPeopleDB.length;
    const totalPages = Math.ceil(totalCount / limit);

    // Handle page out of bounds
    let currentPage = page;
    if (currentPage < 1) {
      currentPage = 1;
    }
    if (currentPage > totalPages && totalPages > 0) { // Allow currentPage to be 1 if totalPages is 0
      currentPage = totalPages;
    }
    
    const startIndex = (currentPage - 1) * limit;
    const endIndex = currentPage * limit;
    const paginatedPeople = mockPeopleDB.slice(startIndex, endIndex);

    console.log('People fetched successfully from mock DB.');
    return {
      people: JSON.parse(JSON.stringify(paginatedPeople)),
      totalCount,
      totalPages,
      currentPage,
    };
  } catch (error) {
    console.error('Error fetching people from mock DB:', error);
    return { people: [], totalCount: 0, totalPages: 0, currentPage: 1 };
  }
}

export async function addPersonAction(
  data: PersonFormData
): Promise<{ success: boolean; person?: Person; error?: string }> {
  console.log('Adding person via server action...', data);
  try {
    await new Promise(resolve => setTimeout(resolve, 700));
    if (!data.name) {
      return { success: false, error: "Name is required." };
    }
    const newPerson: Person = {
      id: `p${nextId++}`,
      name: data.name,
      gender: data.gender,
      imageUrl: data.imageUrl,
      birthDate: data.birthDate ? data.birthDate.toISOString().split('T')[0] : undefined,
      deathDate: data.deathDate ? data.deathDate.toISOString().split('T')[0] : undefined,
      bio: data.bio,
    };
    mockPeopleDB.push(newPerson);
    console.log('Person added successfully to mock DB:', newPerson);
    return { success: true, person: newPerson };
  } catch (error) {
    console.error('Error adding person:', error);
    const errorMessage = error instanceof Error ? error.message : "An unknown error occurred.";
    return { success: false, error: `Failed to add person: ${errorMessage}` };
  }
}

export async function editPersonAction(
  personId: string,
  data: PersonFormData
): Promise<{ success: boolean; person?: Person; error?: string }> {
  console.log(`Editing person ${personId} via server action...`, data);
  try {
    await new Promise(resolve => setTimeout(resolve, 700));
    const personIndex = mockPeopleDB.findIndex(p => p.id === personId);
    if (personIndex === -1) {
      return { success: false, error: "Person not found." };
    }
    const updatedPerson: Person = {
      ...mockPeopleDB[personIndex],
      name: data.name,
      gender: data.gender,
      imageUrl: data.imageUrl,
      birthDate: data.birthDate ? data.birthDate.toISOString().split('T')[0] : undefined,
      deathDate: data.deathDate ? data.deathDate.toISOString().split('T')[0] : undefined,
      bio: data.bio,
    };
    mockPeopleDB[personIndex] = updatedPerson;
    console.log('Person updated successfully in mock DB:', updatedPerson);
    return { success: true, person: updatedPerson };
  } catch (error) {
    console.error(`Error editing person ${personId}:`, error);
    const errorMessage = error instanceof Error ? error.message : "An unknown error occurred.";
    return { success: false, error: `Failed to edit person: ${errorMessage}` };
  }
}

export async function deletePersonAction(
  personId: string
): Promise<{ success: boolean; error?: string }> {
  console.log(`Deleting person ${personId} via server action...`);
  try {
    await new Promise(resolve => setTimeout(resolve, 700));
    const personIndex = mockPeopleDB.findIndex(p => p.id === personId);
    if (personIndex === -1) {
      console.warn(`Person with ID ${personId} not found for deletion.`);
      return { success: false, error: "Person not found." };
    }
    mockPeopleDB.splice(personIndex, 1);
    mockRelationshipsDB = mockRelationshipsDB.filter(
      rel => rel.person1Id !== personId && rel.person2Id !== personId
    );
    console.log(`Person ${personId} and their relationships deleted successfully from mock DB.`);
    return { success: true };
  } catch (error) {
    console.error(`Error deleting person ${personId}:`, error);
    const errorMessage = error instanceof Error ? error.message : "An unknown error occurred.";
    return { success: false, error: `Failed to delete person: ${errorMessage}` };
  }
}

// Relationship Actions
export async function addRelationshipAction(
  data: RelationshipFormData
): Promise<{ success: boolean; relationship?: Relationship; error?: string }> {
  console.log('Adding relationship via server action...', data);
  try {
    await new Promise(resolve => setTimeout(resolve, 700));
    if (data.person1Id === data.person2Id) {
      return { success: false, error: "Cannot create a relationship with oneself." };
    }
    const existingRelationship = mockRelationshipsDB.find(
      r =>
        (r.person1Id === data.person1Id && r.person2Id === data.person2Id && r.type === data.type) ||
        (r.person1Id === data.person2Id && r.person2Id === data.person1Id && r.type === data.type && r.type === 'Spouse')
    );
    if (existingRelationship) {
      return { success: false, error: "This relationship already exists." };
    }
    const newRelationship: Relationship = {
      id: `r${nextRelationshipId++}`,
      person1Id: data.person1Id,
      person2Id: data.person2Id,
      type: data.type,
    };
    mockRelationshipsDB.push(newRelationship);
    console.log('Relationship added successfully to mock DB:', newRelationship);
    return { success: true, relationship: newRelationship };
  } catch (error) {
    console.error('Error adding relationship:', error);
    const errorMessage = error instanceof Error ? error.message : "An unknown error occurred.";
    return { success: false, error: `Failed to add relationship: ${errorMessage}` };
  }
}

export async function getRelationshipsAction(): Promise<Relationship[]> {
  console.log('Fetching relationships from server action (mock DB)...');
  try {
    await new Promise(resolve => setTimeout(resolve, 500));
    console.log('Relationships fetched successfully from mock DB.');
    return JSON.parse(JSON.stringify(mockRelationshipsDB));
  } catch (error) {
    console.error('Error fetching relationships from mock DB:', error);
    return [];
  }
}

export async function deleteRelationshipAction(
  relationshipId: string
): Promise<{ success: boolean; error?: string }> {
  console.log(`Deleting relationship ${relationshipId} via server action...`);
  try {
    await new Promise(resolve => setTimeout(resolve, 700));
    const relationshipIndex = mockRelationshipsDB.findIndex(r => r.id === relationshipId);
    if (relationshipIndex === -1) {
      console.warn(`Relationship with ID ${relationshipId} not found for deletion.`);
      return { success: false, error: "Relationship not found." };
    }
    mockRelationshipsDB.splice(relationshipIndex, 1);
    console.log(`Relationship ${relationshipId} deleted successfully from mock DB.`);
    return { success: true };
  } catch (error) {
    console.error(`Error deleting relationship ${relationshipId}:`, error);
    const errorMessage = error instanceof Error ? error.message : "An unknown error occurred.";
    return { success: false, error: `Failed to delete relationship: ${errorMessage}` };
  }
}
