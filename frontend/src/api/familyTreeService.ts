import { Person } from '../types';
import config from '../config';
import { mockPersons } from '../data/mockData';

export const getFamilyTree = async (): Promise<Person[]> => {
  if (config.useMockData) {
    // Use mock data for development
    return Promise.resolve(mockPersons);
  }
  
  try {
    const response = await fetch(`${config.backendUrl}/persons`);
    if (!response.ok) {
      throw new Error('Failed to fetch family tree data');
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching family tree:', error);
    return [];
  }
};

export const addPerson = async (person: Omit<Person, 'id'>): Promise<Person | null> => {
  // If firstName and lastName are provided, ensure name field is consistent
  if (person.firstName && person.lastName && !person.name) {
    person.name = `${person.firstName} ${person.lastName}`.trim();
  }
  
  // For female persons, ensure maidenName field is properly set
  if (person.gender === 'female' && person.maidenName) {
    // maidenName is already set correctly
  } else if (person.gender === 'male') {
    // Clear maidenName for male persons if somehow set
    person.maidenName = undefined;
  }
  
  if (config.useMockData) {
    // Simulate adding a person with a mock ID
    const newPerson = {
      ...person,
      id: `mock-${Math.random().toString(36).substr(2, 9)}`,
    };
    return Promise.resolve(newPerson as Person);
  }

  try {
    const response = await fetch(`${config.backendUrl}/persons`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(person),
    });
    
    if (!response.ok) {
      throw new Error('Failed to add person');
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error adding person:', error);
    return null;
  }
};

export const updatePerson = async (id: string, data: Partial<Person>): Promise<Person | null> => {
  // If firstName and lastName are provided, ensure name field is consistent
  if (data.firstName && data.lastName && !data.name) {
    data.name = `${data.firstName} ${data.lastName}`.trim();
  }
  
  // For female persons, ensure maidenName field is properly set
  if (data.gender === 'female' && data.maidenName) {
    // maidenName is already set correctly
  } else if (data.gender === 'male') {
    // Clear maidenName for male persons if somehow set
    data.maidenName = undefined;
  }
  
  if (config.useMockData) {
    // Simulate updating a person
    return Promise.resolve({ ...data, id } as Person);
  }

  try {
    const response = await fetch(`${config.backendUrl}/persons/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      throw new Error('Failed to update person');
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error updating person:', error);
    return null;
  }
};

export const deletePerson = async (id: string): Promise<boolean> => {
  if (config.useMockData) {
    // Simulate deleting a person
    return Promise.resolve(true);
  }

  try {
    const response = await fetch(`${config.backendUrl}/persons/${id}`, {
      method: 'DELETE',
    });
    
    return response.ok;
  } catch (error) {
    console.error('Error deleting person:', error);
    return false;
  }
};