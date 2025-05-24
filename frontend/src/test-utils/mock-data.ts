// src/test-utils/mock-data.ts
import { Person, Relationship, RelationshipType } from '@/lib/types';

// Mock person data
export const mockPeople: Person[] = [
  {
    id: 'person-1',
    name: 'John Doe',
    gender: 'Male',
    birthDate: '1980-01-01',
    birthPlace: 'New York',
    isLiving: true,
    bio: 'Software developer and family historian',
    customAttributes: {
      'Occupation': 'Software Engineer',
      'Education': 'Computer Science, MIT'
    }
  },
  {
    id: 'person-2',
    name: 'Jane Doe',
    gender: 'Female',
    birthDate: '1982-03-15',
    birthPlace: 'Boston',
    isLiving: true,
    bio: 'Architect and hobby painter',
    customAttributes: {
      'Occupation': 'Architect',
      'Education': 'Architecture, Harvard'
    }
  },
  {
    id: 'person-3',
    name: 'Michael Doe',
    gender: 'Male',
    birthDate: '2010-07-22',
    birthPlace: 'New York',
    isLiving: true,
    parents: [
      { id: 'person-1', name: 'John Doe' },
      { id: 'person-2', name: 'Jane Doe' }
    ]
  },
  {
    id: 'person-4',
    name: 'Sarah Doe',
    gender: 'Female',
    birthDate: '2012-09-10',
    birthPlace: 'New York',
    isLiving: true,
    parents: [
      { id: 'person-1', name: 'John Doe' },
      { id: 'person-2', name: 'Jane Doe' }
    ]
  },
  {
    id: 'person-5',
    name: 'Robert Smith',
    gender: 'Male',
    birthDate: '1955-04-12',
    birthPlace: 'Chicago',
    isLiving: true,
    children: [
      { id: 'person-1', name: 'John Doe' }
    ]
  }
];

// Mock relationship data
export const mockRelationships: Relationship[] = [
  {
    id: 'relationship-1',
    person1Id: 'person-1',
    person2Id: 'person-2',
    type: 'spouse_current',
    startDate: '2005-06-15',
    location: 'New York',
    description: 'Married in Central Park',
    customAttributes: {
      'Ceremony': 'Traditional',
      'Witnesses': 'Robert Smith, Mary Johnson'
    }
  },
  {
    id: 'relationship-2',
    person1Id: 'person-1',
    person2Id: 'person-3',
    type: 'biological_parent',
    startDate: '2010-07-22',
    location: 'New York General Hospital',
    description: 'Birth of first child'
  },
  {
    id: 'relationship-3',
    person1Id: 'person-2',
    person2Id: 'person-3',
    type: 'biological_parent',
    startDate: '2010-07-22',
    location: 'New York General Hospital',
    description: 'Birth of first child'
  },
  {
    id: 'relationship-4',
    person1Id: 'person-1',
    person2Id: 'person-4',
    type: 'biological_parent',
    startDate: '2012-09-10',
    location: 'New York General Hospital',
    description: 'Birth of second child'
  },
  {
    id: 'relationship-5',
    person1Id: 'person-2',
    person2Id: 'person-4',
    type: 'biological_parent',
    startDate: '2012-09-10',
    location: 'New York General Hospital',
    description: 'Birth of second child'
  },
  {
    id: 'relationship-6',
    person1Id: 'person-5',
    person2Id: 'person-1',
    type: 'biological_parent',
    startDate: '1980-01-01',
    location: 'Chicago Memorial Hospital',
    description: 'Birth of only child'
  },
  {
    id: 'relationship-7',
    person1Id: 'person-3',
    person2Id: 'person-4',
    type: 'sibling_full',
    description: 'Full siblings'
  }
];

// Mock form data
export const mockRelationshipFormData = {
  person1Id: 'person-1',
  person2Id: 'person-2',
  type: 'spouse_current' as RelationshipType,
  startDate: new Date('2005-06-15'),
  location: 'New York',
  description: 'Married in Central Park',
  customAttributes: {
    'Ceremony': 'Traditional',
    'Witnesses': 'Robert Smith, Mary Johnson'
  }
};
