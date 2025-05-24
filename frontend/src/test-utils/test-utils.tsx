// src/test-utils/test-utils.tsx
import React, { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { AuthProvider } from '@/contexts/AuthContext';
import MockAdapter from 'axios-mock-adapter';
import axios from 'axios';

// Create axios mock
export const axiosMock = new MockAdapter(axios);

// Define a custom render function that includes providers
const AllTheProviders = ({ children }: { children: React.ReactNode }) => {
  return (
    <AuthProvider>
      {children}
    </AuthProvider>
  );
};

const customRender = (
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>,
) => render(ui, { wrapper: AllTheProviders, ...options });

// Mock API responses
export const setupMockAPI = () => {
  // Reset all request handlers
  axiosMock.reset();
  
  // Session endpoint
  axiosMock.onGet(/\/api\/auth\/session/).reply(200, {
    user: {
      id: 'test-user-id',
      username: 'testuser',
      email: 'test@example.com',
      role: 'admin',
      active_tree_id: 'test-tree-id'
    }
  });

  // Mock other API endpoints as needed
  axiosMock.onGet(/\/api\/trees/).reply(200, [
    { id: 'test-tree-id', name: 'Test Family Tree', owner_id: 'test-user-id' }
  ]);

  axiosMock.onGet(/\/api\/trees\/test-tree-id\/people/).reply(200, [
    { 
      id: 'person-1',
      name: 'John Doe',
      gender: 'Male',
      birthDate: '1980-01-01',
      isLiving: true
    },
    {
      id: 'person-2',
      name: 'Jane Doe',
      gender: 'Female',
      birthDate: '1982-03-15',
      isLiving: true
    }
  ]);

  axiosMock.onGet(/\/api\/trees\/test-tree-id\/relationships/).reply(200, [
    {
      id: 'relationship-1',
      person1Id: 'person-1',
      person2Id: 'person-2',
      type: 'spouse_current',
      startDate: '2005-06-15',
      location: 'New York',
      description: 'Married in Central Park'
    }
  ]);

  // Return clean-up function
  return () => {
    axiosMock.reset();
  };
};

// Mock user with different roles
export const mockUserWithRole = (role: 'viewer' | 'editor' | 'admin' | 'owner') => {
  axiosMock.onGet(/\/api\/auth\/session/).reply(200, {
    user: {
      id: 'test-user-id',
      username: 'testuser',
      email: 'test@example.com',
      role: role,
      active_tree_id: 'test-tree-id'
    }
  });
};

// Re-export everything from testing-library
export * from '@testing-library/react';
export { customRender as render };
