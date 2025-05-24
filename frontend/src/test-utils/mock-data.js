// src/test-utils/mock-data.js
// Basic mock data for testing

export const mockPeople = [
  {
    id: 'person-1',
    name: 'John Doe',
    gender: 'Male',
    birthDate: '1980-01-01'
  },
  {
    id: 'person-2',
    name: 'Jane Doe',
    gender: 'Female',
    birthDate: '1985-05-15'
  },
  {
    id: 'person-3',
    name: 'James Doe',
    gender: 'Male',
    birthDate: '2010-10-10'
  }
];

export const mockRelationships = [
  {
    id: 'rel-1',
    person1Id: 'person-1',
    person2Id: 'person-2',
    type: 'spouse_current',
    startDate: '2005-06-15',
    location: 'New York',
    description: 'Marriage'
  },
  {
    id: 'rel-2',
    person1Id: 'person-1',
    person2Id: 'person-3',
    type: 'biological_parent',
    startDate: '2010-10-10',
    location: 'New York',
    description: 'Birth of son'
  },
  {
    id: 'rel-3',
    person1Id: 'person-2',
    person2Id: 'person-3',
    type: 'biological_parent',
    startDate: '2010-10-10',
    location: 'New York',
    description: 'Birth of son'
  }
];
