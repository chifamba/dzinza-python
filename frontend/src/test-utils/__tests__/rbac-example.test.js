/**
 * @jest-environment jsdom
 */
import React, { useState, useEffect } from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { createAuthProviderWithRole, mockUsers } from '@/test-utils/auth-utils';

// A simple component that uses RBAC
const RoleBasedComponent = () => {
  const { user, hasRole, checkTreePermission } = useAuth();
  const [canEditTree, setCanEditTree] = useState(false);
  
  useEffect(() => {
    if (user && user.active_tree_id) {
      checkTreePermission(user.active_tree_id, 'edit')
        .then(result => setCanEditTree(result));
    }
  }, [user, checkTreePermission]);
  
  if (!user) {
    return <div data-testid="login-message">Please log in to access this feature</div>;
  }
  
  return (
    <div>
      <h1 data-testid="welcome-message">Welcome, {user.username}</h1>
      
      {hasRole('admin') && (
        <div data-testid="admin-panel">Admin Panel</div>
      )}
      
      <div data-testid="content-area">
        {canEditTree ? (
          <button data-testid="edit-button">Edit Tree</button>
        ) : (
          <div data-testid="view-only-message">View Only Mode</div>
        )}
      </div>
    </div>
  );
};

// Mock the useAuth hook with our test utils
import { useAuth } from '@/contexts/AuthContext';
jest.mock('@/contexts/AuthContext', () => ({
  ...jest.requireActual('@/contexts/AuthContext'),
  useAuth: jest.fn()
}));

describe('RBAC in Components (Example)', () => {
  test('shows login message when user is not logged in', () => {
    useAuth.mockReturnValue({
      user: null,
      hasRole: jest.fn().mockReturnValue(false),
      checkTreePermission: jest.fn().mockResolvedValue(false)
    });
    
    render(<RoleBasedComponent />);
    
    expect(screen.getByTestId('login-message')).toBeInTheDocument();
    expect(screen.queryByTestId('welcome-message')).not.toBeInTheDocument();
  });
  
  test('admin users can see admin panel', () => {
    useAuth.mockReturnValue({
      user: mockUsers.admin,
      hasRole: jest.fn(role => role === 'admin'),
      checkTreePermission: jest.fn().mockResolvedValue(true)
    });
    
    render(<RoleBasedComponent />);
    
    expect(screen.getByTestId('welcome-message')).toHaveTextContent('Welcome, adminuser');
    expect(screen.getByTestId('admin-panel')).toBeInTheDocument();
  });
  
  test('regular users cannot see admin panel but can edit trees', async () => {
    useAuth.mockReturnValue({
      user: mockUsers.user,
      hasRole: jest.fn(role => role === 'user'),
      checkTreePermission: jest.fn().mockResolvedValue(true)
    });
    
    render(<RoleBasedComponent />);
    
    expect(screen.getByTestId('welcome-message')).toHaveTextContent('Welcome, testuser');
    expect(screen.queryByTestId('admin-panel')).not.toBeInTheDocument();
    
    // Wait for checkTreePermission to resolve
    await waitFor(() => {
      expect(screen.getByTestId('edit-button')).toBeInTheDocument();
    });
  });
  
  test('guest users have view-only access', async () => {
    useAuth.mockReturnValue({
      user: mockUsers.guest,
      hasRole: jest.fn(role => role === 'guest'),
      checkTreePermission: jest.fn().mockResolvedValue(false)
    });
    
    render(<RoleBasedComponent />);
    
    expect(screen.getByTestId('welcome-message')).toHaveTextContent('Welcome, guestuser');
    expect(screen.queryByTestId('admin-panel')).not.toBeInTheDocument();
    
    // Wait for checkTreePermission to resolve
    await waitFor(() => {
      expect(screen.getByTestId('view-only-message')).toBeInTheDocument();
      expect(screen.queryByTestId('edit-button')).not.toBeInTheDocument();
    });
  });
});
