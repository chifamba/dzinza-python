import { Person, PrivacyLevel, Relationship, RelationshipType } from '../types';
import config from '../config';
import { mockPersons, mockRelationships } from '../data/mockData';

/**
 * CONVERSION FUNCTIONS
 * These functions handle the data mapping between frontend and backend formats
 */

// Function to convert backend person data to frontend format
const convertBackendPersonToFrontend = (backendPerson: any): Person => {
  // Extract UI data from custom_fields if available
  const uiData = backendPerson.custom_fields?.ui_data || {};
  
  return {
    id: backendPerson.id,
    firstName: backendPerson.first_name,
    middleNames: backendPerson.middle_names,
    lastName: backendPerson.last_name,
    maidenName: backendPerson.maiden_name,
    nickname: backendPerson.nickname,
    gender: backendPerson.gender,
    birthDate: backendPerson.birth_date,
    birthDateApprox: backendPerson.birth_date_approx,
    birthPlace: backendPerson.birth_place,
    placeOfBirth: backendPerson.place_of_birth,
    deathDate: backendPerson.death_date,
    deathDateApprox: backendPerson.death_date_approx,
    deathPlace: backendPerson.death_place,
    placeOfDeath: backendPerson.place_of_death,
    burialPlace: backendPerson.burial_place,
    privacyLevel: backendPerson.privacy_level as PrivacyLevel,
    isLiving: backendPerson.is_living,
    notes: backendPerson.notes,
    biography: backendPerson.biography,
    customAttributes: backendPerson.custom_attributes,
    profilePictureUrl: backendPerson.profile_picture_url,
    customFields: backendPerson.custom_fields,
    createdBy: backendPerson.created_by,
    createdAt: backendPerson.created_at,
    updatedAt: backendPerson.updated_at,
    
    // Legacy fields from UI data
    name: `${backendPerson.first_name || ''} ${backendPerson.last_name || ''}`.trim(),
    color: uiData.color || 'blue',
    parentId: uiData.parent_id,
    spouseId: uiData.spouse_id,
    hasImage: uiData.has_image || !!backendPerson.profile_picture_url,
    isPlaceholder: uiData.is_placeholder,
    category: uiData.category
  };
};

// Function to convert frontend person to backend format
const convertFrontendPersonToBackend = (person: Partial<Person>): any => {
  return {
    first_name: person.firstName,
    middle_names: person.middleNames,
    last_name: person.lastName,
    maiden_name: person.maidenName,
    nickname: person.nickname,
    gender: person.gender,
    birth_date: person.birthDate,
    birth_date_approx: person.birthDateApprox,
    birth_place: person.birthPlace || person.placeOfBirth,
    death_date: person.deathDate,
    death_date_approx: person.deathDateApprox,
    death_place: person.deathPlace || person.placeOfDeath,
    burial_place: person.burialPlace,
    privacy_level: person.privacyLevel,
    is_living: person.isLiving,
    notes: person.notes,
    biography: person.biography,
    custom_attributes: person.customAttributes,
    profile_picture_url: person.profilePictureUrl,
    custom_fields: {
      ...person.customFields,
      ui_data: {
        color: person.color,
        parent_id: person.parentId,
        spouse_id: person.spouseId,
        has_image: person.hasImage,
        is_placeholder: person.isPlaceholder,
        category: person.category
      }
    }
  };
};

// Function to convert backend relationship data to frontend format
const convertBackendRelationshipToFrontend = (backendRelationship: any): Relationship => {
  return {
    id: backendRelationship.id,
    person1Id: backendRelationship.person1_id,
    person2Id: backendRelationship.person2_id,
    relationshipType: backendRelationship.relationship_type as RelationshipType,
    startDate: backendRelationship.start_date,
    endDate: backendRelationship.end_date,
    location: backendRelationship.location,
    certaintyLevel: backendRelationship.certainty_level,
    customAttributes: backendRelationship.custom_attributes,
    notes: backendRelationship.notes,
    createdBy: backendRelationship.created_by,
    createdAt: backendRelationship.created_at,
    updatedAt: backendRelationship.updated_at
  };
};

// Function to convert frontend relationship to backend format
const convertFrontendRelationshipToBackend = (relationship: Partial<Relationship>): any => {
  return {
    person1_id: relationship.person1Id,
    person2_id: relationship.person2Id,
    relationship_type: relationship.relationshipType,
    start_date: relationship.startDate,
    end_date: relationship.endDate,
    location: relationship.location,
    certainty_level: relationship.certaintyLevel,
    custom_attributes: relationship.customAttributes,
    notes: relationship.notes
  };
};

/**
 * PERSON OPERATIONS
 * Basic CRUD operations for person management
 */

export const getFamilyTree = async (filters?: Record<string, any>): Promise<Person[]> => {
  if (config.useMockData) {
    // Use mock data for development
    return Promise.resolve(mockPersons);
  }
  
  try {
    // Build query string from filters if provided
    const queryParams = filters ? 
      '?' + Object.entries(filters)
        .map(([key, value]) => `${key}=${encodeURIComponent(String(value))}`)
        .join('&') 
      : '';
    
    const response = await fetch(`${config.backendUrl}/api/people${queryParams}`);
    
    if (!response.ok) {
      throw new Error('Failed to fetch family tree data');
    }
    
    const backendPersons = await response.json();
    // Convert backend data to frontend format
    return backendPersons.map(convertBackendPersonToFrontend);
  } catch (error) {
    console.error('Error fetching family tree:', error);
    return [];
  }
};

export const getPerson = async (id: string): Promise<Person | null> => {
  if (config.useMockData) {
    // Use mock data for development
    const mockPerson = mockPersons.find(p => p.id === id);
    return Promise.resolve(mockPerson || null);
  }
  
  try {
    const response = await fetch(`${config.backendUrl}/api/people/${id}`);
    
    if (!response.ok) {
      throw new Error('Failed to fetch person data');
    }
    
    const backendPerson = await response.json();
    return convertBackendPersonToFrontend(backendPerson);
  } catch (error) {
    console.error('Error fetching person:', error);
    return null;
  }
};

export const addPerson = async (personData: Omit<Person, 'id'>): Promise<Person | null> => {
  // If firstName and lastName are provided, ensure name field is consistent
  if (personData.firstName && personData.lastName && !personData.name) {
    personData.name = `${personData.firstName} ${personData.lastName}`.trim();
  }
  
  // For female persons, ensure maidenName field is properly set
  if (personData.gender === 'female' && personData.maidenName) {
    // maidenName is already set correctly
  } else if (personData.gender === 'male') {
    // Clear maidenName for male persons if somehow set
    personData.maidenName = undefined;
  }
  
  if (config.useMockData) {
    // Simulate adding a person with a mock ID
    const newPerson = {
      ...personData,
      id: `mock-${Math.random().toString(36).substr(2, 9)}`,
    };
    return Promise.resolve(newPerson as Person);
  }

  try {
    // Convert to backend format
    const backendPerson = convertFrontendPersonToBackend(personData);
    
    const response = await fetch(`${config.backendUrl}/api/people`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(backendPerson),
    });
    
    if (!response.ok) {
      throw new Error('Failed to add person');
    }
    
    // Convert the backend response back to the frontend model
    const backendResponse = await response.json();
    return convertBackendPersonToFrontend(backendResponse);
  } catch (error) {
    console.error('Error adding person:', error);
    return null;
  }
};

export const updatePerson = async (id: string, personData: Partial<Person>): Promise<Person | null> => {
  // If firstName and lastName are provided, ensure name field is consistent
  if (personData.firstName && personData.lastName && !personData.name) {
    personData.name = `${personData.firstName} ${personData.lastName}`.trim();
  }
  
  // For female persons, ensure maidenName field is properly set
  if (personData.gender === 'female' && personData.maidenName) {
    // maidenName is already set correctly
  } else if (personData.gender === 'male') {
    // Clear maidenName for male persons if somehow set
    personData.maidenName = undefined;
  }
  
  if (config.useMockData) {
    // Simulate updating a person
    return Promise.resolve({ ...personData, id } as Person);
  }

  try {
    // Convert to backend format
    const backendPerson = convertFrontendPersonToBackend(personData);
    
    const response = await fetch(`${config.backendUrl}/api/people/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(backendPerson),
    });
    
    if (!response.ok) {
      throw new Error('Failed to update person');
    }
    
    // Convert the backend response back to the frontend model
    const backendResponse = await response.json();
    return convertBackendPersonToFrontend(backendResponse);
  } catch (error) {
    console.error('Error updating person:', error);
    return null;
  }
};

/**
 * PROFILE PICTURE OPERATIONS
 * Functions for handling person profile pictures
 */

export const uploadProfilePicture = async (personId: string, file: File): Promise<Person | null> => {
  if (config.useMockData) {
    // Simulate updating a profile picture in mock data
    return Promise.resolve({
      id: personId,
      profilePictureUrl: URL.createObjectURL(file),
      hasImage: true
    } as Person);
  }

  try {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${config.backendUrl}/people/${personId}/profile_picture`, {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      throw new Error('Failed to upload profile picture');
    }
    
    const backendResponse = await response.json();
    return convertBackendPersonToFrontend(backendResponse);
  } catch (error) {
    console.error('Error uploading profile picture:', error);
    return null;
  }
};

/**
 * PERSON SEARCH AND FILTERING
 * Advanced search and filtering functions for persons
 */

export interface PersonFilterOptions {
  isLiving?: boolean;
  gender?: string;
  searchTerm?: string;
  birthStartDate?: string;
  birthEndDate?: string;
  deathStartDate?: string;
  deathEndDate?: string;
  customFieldsKey?: string;
  customFieldsValue?: string;
  page?: number;
  perPage?: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

export const searchPersons = async (options: PersonFilterOptions): Promise<Person[]> => {
  if (config.useMockData) {
    // Simple filter simulation for mock data
    let filteredPersons = [...mockPersons];
    
    if (options.searchTerm) {
      const searchTermLower = options.searchTerm.toLowerCase();
      filteredPersons = filteredPersons.filter(person => 
        person.firstName?.toLowerCase().includes(searchTermLower) ||
        person.lastName?.toLowerCase().includes(searchTermLower) ||
        person.nickname?.toLowerCase().includes(searchTermLower)
      );
    }
    
    if (options.gender) {
      filteredPersons = filteredPersons.filter(person => 
        person.gender === options.gender
      );
    }
    
    if (options.isLiving !== undefined) {
      filteredPersons = filteredPersons.filter(person => 
        person.isLiving === options.isLiving
      );
    }
    
    return Promise.resolve(filteredPersons);
  }
  
  try {
    // Convert options to query parameters
    const queryParams = new URLSearchParams();
    
    if (options.isLiving !== undefined) queryParams.append('is_living', String(options.isLiving));
    if (options.gender) queryParams.append('gender', options.gender);
    if (options.searchTerm) queryParams.append('search_term', options.searchTerm);
    if (options.birthStartDate) queryParams.append('birth_start_date', options.birthStartDate);
    if (options.birthEndDate) queryParams.append('birth_end_date', options.birthEndDate);
    if (options.deathStartDate) queryParams.append('death_start_date', options.deathStartDate);
    if (options.deathEndDate) queryParams.append('death_end_date', options.deathEndDate);
    if (options.customFieldsKey) queryParams.append('custom_fields_key', options.customFieldsKey);
    if (options.customFieldsValue !== undefined) queryParams.append('custom_fields_value', options.customFieldsValue);
    if (options.page) queryParams.append('page', String(options.page));
    if (options.perPage) queryParams.append('per_page', String(options.perPage));
    if (options.sortBy) queryParams.append('sort_by', options.sortBy);
    if (options.sortOrder) queryParams.append('sort_order', options.sortOrder);
    
    const queryString = queryParams.toString();
    const url = `${config.backendUrl}/people${queryString ? `?${queryString}` : ''}`;
    
    const response = await fetch(url);
    
    if (!response.ok) {
      throw new Error('Failed to search persons');
    }
    
    const backendPersons = await response.json();
    return backendPersons.map(convertBackendPersonToFrontend);
  } catch (error) {
    console.error('Error searching persons:', error);
    return [];
  }
};

/**
 * PERSON MEDIA OPERATIONS
 * Functions for handling person media items
 */

export interface MediaItem {
  id: string;
  entityType: string;
  entityId: string;
  mediaType: string;
  url: string;
  title?: string;
  description?: string;
  tags?: string[];
  customAttributes?: Record<string, any>;
  createdBy?: string;
  createdAt?: string;
  updatedAt?: string;
}

export const getPersonMedia = async (
  personId: string,
  page: number = 1,
  perPage: number = 20,
  sortBy: string = 'created_at',
  sortOrder: 'asc' | 'desc' = 'desc'
): Promise<MediaItem[]> => {
  if (config.useMockData) {
    // Return empty array for mock data
    return Promise.resolve([]);
  }
  
  try {
    const queryParams = new URLSearchParams({
      page: String(page),
      per_page: String(perPage),
      sort_by: sortBy,
      sort_order: sortOrder
    });
    
    const response = await fetch(
      `${config.backendUrl}/people/${personId}/media?${queryParams.toString()}`
    );
    
    if (!response.ok) {
      throw new Error('Failed to fetch person media');
    }
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching person media:', error);
    return [];
  }
};

export const uploadPersonMedia = async (
  personId: string,
  file: File,
  metadata: {
    title?: string;
    description?: string;
    tags?: string[];
    customAttributes?: Record<string, any>;
  }
): Promise<MediaItem | null> => {
  if (config.useMockData) {
    // Simulate uploading media in mock data
    return Promise.resolve({
      id: `mock-media-${Math.random().toString(36).substr(2, 9)}`,
      entityType: 'Person',
      entityId: personId,
      mediaType: file.type.startsWith('image/') ? 'image' : 'document',
      url: URL.createObjectURL(file),
      title: metadata.title,
      description: metadata.description,
      tags: metadata.tags,
      customAttributes: metadata.customAttributes,
      createdAt: new Date().toISOString()
    } as MediaItem);
  }

  try {
    const formData = new FormData();
    formData.append('file', file);
    
    // Add metadata as JSON
    formData.append('metadata', JSON.stringify(metadata));
    
    const response = await fetch(`${config.backendUrl}/people/${personId}/media`, {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      throw new Error('Failed to upload media');
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error uploading person media:', error);
    return null;
  }
};

/**
 * PERSON EVENTS OPERATIONS
 * Functions for handling person life events
 */

export interface Event {
  id: string;
  personId: string;
  eventType: string;
  date?: string;
  dateApprox?: boolean;
  location?: string;
  description?: string;
  notes?: string;
  sources?: string[];
  customAttributes?: Record<string, any>;
  createdBy?: string;
  createdAt?: string;
  updatedAt?: string;
}

export const getPersonEvents = async (
  personId: string,
  page: number = 1,
  perPage: number = 20,
  sortBy: string = 'date',
  sortOrder: 'asc' | 'desc' = 'asc'
): Promise<Event[]> => {
  if (config.useMockData) {
    // Return empty array for mock data
    return Promise.resolve([]);
  }
  
  try {
    const queryParams = new URLSearchParams({
      page: String(page),
      per_page: String(perPage),
      sort_by: sortBy,
      sort_order: sortOrder
    });
    
    const response = await fetch(
      `${config.backendUrl}/people/${personId}/events?${queryParams.toString()}`
    );
    
    if (!response.ok) {
      throw new Error('Failed to fetch person events');
    }
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching person events:', error);
    return [];
  }
};

/**
 * RELATIONSHIP OPERATIONS
 * CRUD operations for relationship management
 */

export const getRelationships = async (
  filters?: {
    personId?: string;
    relationshipType?: RelationshipType;
    page?: number;
    perPage?: number;
    sortBy?: string;
    sortOrder?: 'asc' | 'desc';
  }
): Promise<Relationship[]> => {
  if (config.useMockData) {
    // Filter mock relationships if personId is provided
    if (filters?.personId) {
      return Promise.resolve(
        mockRelationships.filter(r => 
          r.person1Id === filters.personId || r.person2Id === filters.personId
        )
      );
    }
    // Filter by relationship type if provided
    if (filters?.relationshipType) {
      return Promise.resolve(
        mockRelationships.filter(r => r.relationshipType === filters.relationshipType)
      );
    }
    return Promise.resolve(mockRelationships);
  }
  
  try {
    const queryParams = new URLSearchParams();
    
    if (filters?.personId) queryParams.append('person_id', filters.personId);
    if (filters?.relationshipType) queryParams.append('relationship_type', filters.relationshipType);
    if (filters?.page) queryParams.append('page', String(filters.page));
    if (filters?.perPage) queryParams.append('per_page', String(filters.perPage));
    if (filters?.sortBy) queryParams.append('sort_by', filters.sortBy);
    if (filters?.sortOrder) queryParams.append('sort_order', filters.sortOrder);
    
    const queryString = queryParams.toString();
    const url = `${config.backendUrl}/relationships${queryString ? `?${queryString}` : ''}`;
    
    const response = await fetch(url);
    
    if (!response.ok) {
      throw new Error('Failed to fetch relationships');
    }
    
    const backendRelationships = await response.json();
    return backendRelationships.map(convertBackendRelationshipToFrontend);
  } catch (error) {
    console.error('Error fetching relationships:', error);
    return [];
  }
};

export const getRelationship = async (id: string): Promise<Relationship | null> => {
  if (config.useMockData) {
    const mockRelationship = mockRelationships.find(r => r.id === id);
    return Promise.resolve(mockRelationship || null);
  }
  
  try {
    const response = await fetch(`${config.backendUrl}/relationships/${id}`);
    
    if (!response.ok) {
      throw new Error('Failed to fetch relationship');
    }
    
    const backendRelationship = await response.json();
    return convertBackendRelationshipToFrontend(backendRelationship);
  } catch (error) {
    console.error('Error fetching relationship:', error);
    return null;
  }
};

export const addRelationship = async (relationshipData: Omit<Relationship, 'id'>): Promise<Relationship | null> => {
  if (config.useMockData) {
    const newRelationship = {
      ...relationshipData,
      id: `mock-rel-${Math.random().toString(36).substr(2, 9)}`,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    };
    return Promise.resolve(newRelationship as Relationship);
  }

  try {
    const backendRelationship = convertFrontendRelationshipToBackend(relationshipData);
    
    const response = await fetch(`${config.backendUrl}/relationships`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(backendRelationship),
    });
    
    if (!response.ok) {
      throw new Error('Failed to add relationship');
    }
    
    const backendResponse = await response.json();
    return convertBackendRelationshipToFrontend(backendResponse);
  } catch (error) {
    console.error('Error adding relationship:', error);
    return null;
  }
};

export const updateRelationship = async (id: string, relationshipData: Partial<Relationship>): Promise<Relationship | null> => {
  if (config.useMockData) {
    return Promise.resolve({
      ...relationshipData,
      id,
      updatedAt: new Date().toISOString()
    } as Relationship);
  }

  try {
    const backendRelationship = convertFrontendRelationshipToBackend(relationshipData);
    
    const response = await fetch(`${config.backendUrl}/relationships/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(backendRelationship),
    });
    
    if (!response.ok) {
      throw new Error('Failed to update relationship');
    }
    
    const backendResponse = await response.json();
    return convertBackendRelationshipToFrontend(backendResponse);
  } catch (error) {
    console.error('Error updating relationship:', error);
    return null;
  }
};

export const deleteRelationship = async (id: string): Promise<boolean> => {
  if (config.useMockData) {
    return Promise.resolve(true);
  }

  try {
    const response = await fetch(`${config.backendUrl}/relationships/${id}`, {
      method: 'DELETE',
    });
    
    return response.ok;
  } catch (error) {
    console.error('Error deleting relationship:', error);
    return false;
  }
};

/**
 * UTILITY FUNCTIONS
 * Helper functions for common operations
 */

export const getParentChildRelationships = async (personId: string): Promise<Relationship[]> => {
  // Get all relationships for this person
  const relationships = await getRelationships({ personId });
  
  // Filter for parent-child relationships
  const parentChildTypes = [
    RelationshipType.BIOLOGICAL_PARENT,
    RelationshipType.ADOPTIVE_PARENT,
    RelationshipType.STEP_PARENT,
    RelationshipType.FOSTER_PARENT,
    RelationshipType.GUARDIAN,
    RelationshipType.BIOLOGICAL_CHILD,
    RelationshipType.ADOPTIVE_CHILD,
    RelationshipType.STEP_CHILD,
    RelationshipType.FOSTER_CHILD
  ];
  
  return relationships.filter(rel => 
    parentChildTypes.includes(rel.relationshipType)
  );
};

export const getSpouseRelationships = async (personId: string): Promise<Relationship[]> => {
  // Get all relationships for this person
  const relationships = await getRelationships({ personId });
  
  // Filter for spouse relationships
  const spouseTypes = [
    RelationshipType.SPOUSE_CURRENT,
    RelationshipType.SPOUSE_FORMER,
    RelationshipType.PARTNER
  ];
  
  return relationships.filter(rel => 
    spouseTypes.includes(rel.relationshipType)
  );
};

export const getSiblingRelationships = async (personId: string): Promise<Relationship[]> => {
  // Get all relationships for this person
  const relationships = await getRelationships({ personId });
  
  // Filter for sibling relationships
  const siblingTypes = [
    RelationshipType.SIBLING_FULL,
    RelationshipType.SIBLING_HALF,
    RelationshipType.SIBLING_STEP,
    RelationshipType.SIBLING_ADOPTIVE
  ];
  
  return relationships.filter(rel => 
    siblingTypes.includes(rel.relationshipType)
  );
};

/**
 * CONVENIENCE FUNCTIONS
 * Helper functions for common relationship operations
 */

export const addParentChildRelationship = async (
  parentId: string, 
  childId: string, 
  relationshipType: RelationshipType = RelationshipType.BIOLOGICAL_PARENT
): Promise<Relationship | null> => {
  return addRelationship({
    person1Id: parentId,
    person2Id: childId,
    relationshipType
  } as Omit<Relationship, 'id'>);
};

export const addSpouseRelationship = async (
  person1Id: string,
  person2Id: string,
  relationshipType: RelationshipType = RelationshipType.SPOUSE_CURRENT,
  startDate?: string,
  endDate?: string,
  location?: string
): Promise<Relationship | null> => {
  return addRelationship({
    person1Id,
    person2Id,
    relationshipType,
    startDate,
    endDate,
    location
  } as Omit<Relationship, 'id'>);
};

export const addSiblingRelationship = async (
  person1Id: string,
  person2Id: string,
  relationshipType: RelationshipType = RelationshipType.SIBLING_FULL
): Promise<Relationship | null> => {
  return addRelationship({
    person1Id,
    person2Id,
    relationshipType
  } as Omit<Relationship, 'id'>);
};

/**
 * FAMILY TREE OPERATIONS
 * Functions for building and traversing family trees
 */

export interface FamilyTreeNode {
  person: Person;
  parents: FamilyTreeNode[];
  children: FamilyTreeNode[];
  spouses: FamilyTreeNode[];
  siblings: FamilyTreeNode[];
}

export const buildFamilyTreeForPerson = async (
  personId: string, 
  generations: { ancestors: number; descendants: number } = { ancestors: 2, descendants: 2 }
): Promise<FamilyTreeNode | null> => {
  if (config.useMockData) {
    // For mock data, we'll do a simplified version
    const person = mockPersons.find(p => p.id === personId);
    if (!person) return null;
    
    const result: FamilyTreeNode = {
      person,
      parents: [],
      children: [],
      spouses: [],
      siblings: []
    };
    
    // Simple mock relationships
    mockPersons.forEach(p => {
      if (p.parentId === personId) {
        result.children.push({
          person: p,
          parents: [result],
          children: [],
          spouses: [],
          siblings: []
        });
      }
      
      if (person.parentId === p.id) {
        result.parents.push({
          person: p,
          parents: [],
          children: [result],
          spouses: [],
          siblings: []
        });
      }
      
      if (p.spouseId === personId) {
        result.spouses.push({
          person: p,
          parents: [],
          children: [],
          spouses: [result],
          siblings: []
        });
      }
      
      // Simple sibling detection
      if (p.parentId === person.parentId && p.id !== personId && person.parentId) {
        result.siblings.push({
          person: p,
          parents: [...result.parents],
          children: [],
          spouses: [],
          siblings: [result]
        });
      }
    });
    
    return result;
  }
  
  // For real implementation, we would use the relationships API
  // to build the family tree recursively
  try {
    // First get the person
    const person = await getPerson(personId);
    if (!person) return null;
    
    // Initialize the result
    const result: FamilyTreeNode = {
      person,
      parents: [],
      children: [],
      spouses: [],
      siblings: []
    };
    
    // Get relationships
    const relationships = await getRelationships({ personId });
    
    // Process parent-child relationships
    for (const rel of relationships) {
      if (
        rel.person1Id === personId && 
        [
          RelationshipType.BIOLOGICAL_CHILD, 
          RelationshipType.ADOPTIVE_CHILD,
          RelationshipType.STEP_CHILD,
          RelationshipType.FOSTER_CHILD
        ].includes(rel.relationshipType)
      ) {
        // This person is a child of person2
        if (generations.ancestors > 0) {
          const parentPerson = await getPerson(rel.person2Id);
          if (parentPerson) {
            // Recursively build the parent's tree with decreased ancestor generations
            const parentNode = await buildFamilyTreeForPerson(
              rel.person2Id, 
              { 
                ancestors: generations.ancestors - 1, 
                descendants: 0 
              }
            );
            if (parentNode) {
              result.parents.push(parentNode);
            }
          }
        }
      } else if (
        rel.person2Id === personId && 
        [
          RelationshipType.BIOLOGICAL_PARENT, 
          RelationshipType.ADOPTIVE_PARENT,
          RelationshipType.STEP_PARENT,
          RelationshipType.FOSTER_PARENT,
          RelationshipType.GUARDIAN
        ].includes(rel.relationshipType)
      ) {
        // This person is a parent of person1
        if (generations.ancestors > 0) {
          const parentPerson = await getPerson(rel.person1Id);
          if (parentPerson) {
            // Recursively build the parent's tree with decreased ancestor generations
            const parentNode = await buildFamilyTreeForPerson(
              rel.person1Id, 
              { 
                ancestors: generations.ancestors - 1, 
                descendants: 0 
              }
            );
            if (parentNode) {
              result.parents.push(parentNode);
            }
          }
        }
      } else if (
        rel.person1Id === personId && 
        [
          RelationshipType.BIOLOGICAL_PARENT, 
          RelationshipType.ADOPTIVE_PARENT,
          RelationshipType.STEP_PARENT,
          RelationshipType.FOSTER_PARENT,
          RelationshipType.GUARDIAN
        ].includes(rel.relationshipType)
      ) {
        // This person is a parent of person2
        if (generations.descendants > 0) {
          const childPerson = await getPerson(rel.person2Id);
          if (childPerson) {
            // Recursively build the child's tree with decreased descendant generations
            const childNode = await buildFamilyTreeForPerson(
              rel.person2Id, 
              { 
                ancestors: 0, 
                descendants: generations.descendants - 1 
              }
            );
            if (childNode) {
              result.children.push(childNode);
            }
          }
        }
      } else if (
        rel.person2Id === personId && 
        [
          RelationshipType.BIOLOGICAL_CHILD, 
          RelationshipType.ADOPTIVE_CHILD,
          RelationshipType.STEP_CHILD,
          RelationshipType.FOSTER_CHILD
        ].includes(rel.relationshipType)
      ) {
        // This person is a child of person1
        if (generations.descendants > 0) {
          const childPerson = await getPerson(rel.person1Id);
          if (childPerson) {
            // Recursively build the child's tree with decreased descendant generations
            const childNode = await buildFamilyTreeForPerson(
              rel.person1Id, 
              { 
                ancestors: 0, 
                descendants: generations.descendants - 1 
              }
            );
            if (childNode) {
              result.children.push(childNode);
            }
          }
        }
      } else if (
        [
          RelationshipType.SPOUSE_CURRENT,
          RelationshipType.SPOUSE_FORMER,
          RelationshipType.PARTNER
        ].includes(rel.relationshipType)
      ) {
        // This is a spouse relationship
        const spouseId = rel.person1Id === personId ? rel.person2Id : rel.person1Id;
        const spousePerson = await getPerson(spouseId);
        if (spousePerson) {
          // Build a minimal spouse node without recursion
          result.spouses.push({
            person: spousePerson,
            parents: [],
            children: [],
            spouses: [result],
            siblings: []
          });
        }
      } else if (
        [
          RelationshipType.SIBLING_FULL,
          RelationshipType.SIBLING_HALF,
          RelationshipType.SIBLING_STEP,
          RelationshipType.SIBLING_ADOPTIVE
        ].includes(rel.relationshipType)
      ) {
        // This is a sibling relationship
        const siblingId = rel.person1Id === personId ? rel.person2Id : rel.person1Id;
        const siblingPerson = await getPerson(siblingId);
        if (siblingPerson) {
          // Build a minimal sibling node without recursion
          result.siblings.push({
            person: siblingPerson,
            parents: [...result.parents],
            children: [],
            spouses: [],
            siblings: [result]
          });
        }
      }
    }
    
    return result;
  } catch (error) {
    console.error('Error building family tree:', error);
    return null;
  }
};

/**
 * PERSON DELETION
 * Function to delete a person
 */

export const deletePerson = async (personId: string): Promise<boolean> => {
  if (config.useMockData) {
    // Simulate deleting a person in mock data
    console.log(`Mock deleting person with ID: ${personId}`);
    return Promise.resolve(true);
  }

  try {
    const response = await fetch(`${config.backendUrl}/api/people/${personId}`, {
      method: 'DELETE',
    });
    
    if (!response.ok) {
      throw new Error('Failed to delete person');
    }
    
    return true;
  } catch (error) {
    console.error('Error deleting person:', error);
    return false;
  }
};