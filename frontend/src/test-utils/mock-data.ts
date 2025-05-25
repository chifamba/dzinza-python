// Mock data for tests
import { Person, Relationship, Event, Media } from '@/lib/types';

// Mock people
export const mockPeople: Record<string, Person> = {
  'person1': {
    id: 'person1',
    name: 'John Smith',
    gender: 'male',
    birthDate: '1980-01-01',
    birthPlace: 'New York',
    occupation: 'Engineer',
    biography: 'John is an engineer with 20 years of experience.',
    images: ['john.jpg'],
  },
  'person2': {
    id: 'person2',
    name: 'Jane Smith',
    gender: 'female',
    birthDate: '1982-05-15',
    birthPlace: 'Boston',
    occupation: 'Doctor',
    biography: 'Jane is a doctor specializing in cardiology.',
    images: ['jane.jpg'],
  },
  'person3': {
    id: 'person3',
    name: 'Michael Smith',
    gender: 'male',
    birthDate: '2010-08-20',
    birthPlace: 'Chicago',
    images: ['michael.jpg'],
  },
};

// Mock relationships
export const mockRelationships: Relationship[] = [
  {
    id: 'rel1',
    person1Id: 'person1',
    person2Id: 'person2',
    type: 'spouse_current',
    startDate: '2008-06-15',
    location: 'New York',
    description: 'Married in a small ceremony',
    customAttributes: {
      verificationStatus: 'verified',
      marriageLicense: '12345',
    },
  },
  {
    id: 'rel2',
    person1Id: 'person1',
    person2Id: 'person3',
    type: 'biological_parent',
    description: 'Father-son relationship',
    customAttributes: {
      verificationStatus: 'verified',
    },
  },
  {
    id: 'rel3',
    person1Id: 'person2',
    person2Id: 'person3',
    type: 'biological_parent',
    description: 'Mother-son relationship',
    customAttributes: {
      verificationStatus: 'verified',
    },
  },
];

// Mock events
export const mockEvents: Event[] = [
  {
    id: 'event1',
    title: 'Smith Family Reunion',
    date: '2023-07-15',
    location: 'Central Park, New York',
    description: 'Annual family gathering',
    personIds: ['person1', 'person2', 'person3'],
  },
  {
    id: 'event2',
    title: 'Graduation Ceremony',
    date: '2023-05-20',
    location: 'State University',
    description: 'College graduation',
    personIds: ['person1'],
  },
];

// Mock media
export const mockMedia: Media[] = [
  {
    id: 'media1',
    filename: 'family_photo.jpg',
    filePath: '/uploads/family_photo.jpg',
    fileType: 'image/jpeg',
    fileSize: 2500000,
    uploaded: '2023-01-10',
    description: 'Family photo from Christmas 2022',
    personIds: ['person1', 'person2', 'person3'],
  },
  {
    id: 'media2',
    filename: 'wedding.jpg',
    filePath: '/uploads/wedding.jpg',
    fileType: 'image/jpeg',
    fileSize: 3500000,
    uploaded: '2023-02-15',
    description: 'Wedding photo',
    personIds: ['person1', 'person2'],
  },
];
