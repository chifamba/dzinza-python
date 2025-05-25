// Test utilities for React Testing Library
import React from 'react';
import { render as rtlRender } from '@testing-library/react';
import axios from 'axios';
import MockAdapter from 'axios-mock-adapter';
import { Person, Relationship } from '@/lib/types';

// Export a reusable axios mock
export const axiosMock = new MockAdapter(axios);

// Reset axios mock after each test
afterEach(() => {
  axiosMock.reset();
});

// Setup common API mocks
export function setupMockAPI() {
  // Mock common API endpoints here
  axiosMock.onGet('/api/people').reply(200, { data: [] });
  axiosMock.onGet('/api/relationships').reply(200, { data: [] });
}

// Custom render function for components that need context providers
export function render(ui, options = {}) {
  function Wrapper({ children }) {
    return children;
  }
  
  return rtlRender(ui, { wrapper: Wrapper, ...options });
}

// Export everything from RTL
export * from '@testing-library/react';

// Sample mock data to use in tests
export const mockPeople: Record<string, Person> = {
  'person1': {
    id: 'person1',
    name: 'John Smith',
    gender: 'male',
    birthDate: '1980-01-01',
  },
  'person2': {
    id: 'person2',
    name: 'Jane Doe',
    gender: 'female',
    birthDate: '1982-05-15',
  },
};

export const mockRelationships: Relationship[] = [
  {
    id: 'rel1',
    person1Id: 'person1',
    person2Id: 'person2',
    type: 'spouse_current',
    startDate: '2010-06-15',
  },
];
