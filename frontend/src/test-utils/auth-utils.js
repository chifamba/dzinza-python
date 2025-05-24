// src/test-utils/auth-utils.js
import React from 'react';
import { AuthContext } from '@/contexts/AuthContext';

/**
 * Creates a mock AuthProvider for testing components that use the useAuth hook
 * @param {Object} authValue - Mock auth context value to provide
 * @returns {Function} - Mocked AuthProvider component
 */
export function createMockAuthProvider(authValue = {}) {
  const defaultAuthValue = {
    user: null,
    loading: false,
    login: jest.fn(),
    logout: jest.fn(),
    refresh: jest.fn(),
    hasRole: jest.fn().mockReturnValue(false),
    checkTreePermission: jest.fn().mockResolvedValue(false),
    ...authValue
  };

  return ({ children }) => (
    <AuthContext.Provider value={defaultAuthValue}>
      {children}
    </AuthContext.Provider>
  );
}

/**
 * Mock user objects for testing
 */
export const mockUsers = {
  admin: {
    id: 'admin-123',
    username: 'adminuser',
    email: 'admin@example.com',
    role: 'admin',
    active_tree_id: 'tree-123'
  },
  user: {
    id: 'user-123',
    username: 'testuser',
    email: 'test@example.com',
    role: 'user',
    active_tree_id: 'tree-123'
  },
  guest: {
    id: 'guest-123',
    username: 'guestuser',
    email: 'guest@example.com',
    role: 'guest',
    active_tree_id: 'tree-123'
  }
};

/**
 * Creates a mocked AuthProvider with a specific user role
 * @param {string} role - Role to set for the mock user ('admin', 'user', 'guest')
 * @returns {Function} - Mocked AuthProvider component with the specified user role
 */
export function createAuthProviderWithRole(role) {
  const user = mockUsers[role] || null;
  
  return createMockAuthProvider({
    user,
    hasRole: jest.fn(requiredRole => {
      if (!user) return false;
      if (Array.isArray(requiredRole)) {
        return requiredRole.includes(user.role);
      }
      return user.role === requiredRole;
    }),
    checkTreePermission: jest.fn(async (treeId, permission) => {
      if (!user) return false;
      
      // Admin has all permissions
      if (user.role === 'admin') return true;
      
      // User has view and edit permissions
      if (user.role === 'user') {
        return permission === 'view' || permission === 'edit';
      }
      
      // Guest has only view permission
      if (user.role === 'guest') {
        return permission === 'view';
      }
      
      return false;
    })
  });
}
