import { Person, PrivacyLevel } from '../types';
import config from '../config';
import { mockPersons } from '../data/mockData';

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
    
    const backendPersons = await response.json();
    // Convert backend data to frontend format
    return backendPersons.map(convertBackendPersonToFrontend);
  } catch (error) {
    console.error('Error fetching family tree:', error);
    return [];
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
    
    const response = await fetch(`${config.backendUrl}/persons`, {
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
    
    const response = await fetch(`${config.backendUrl}/persons/${id}`, {
      method: 'PATCH',
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