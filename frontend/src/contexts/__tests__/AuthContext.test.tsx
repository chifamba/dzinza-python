/**
 * @jest-environment jsdom
 */
import React from 'react';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import axios from 'axios';
import MockAdapter from 'axios-mock-adapter';

// Create axios mock
const mockAxios = new MockAdapter(axios);

// Mock the API module
jest.mock('@/api', () => ({
  getSession: jest.fn(),
  login: jest.fn(),
  logout: jest.fn(),
  getTreePermissions: jest.fn(),
  hasTreePermission: jest.fn()
}));

// Import API after mocking
import api from '@/api';
import { AuthProvider, useAuth } from '@/contexts/AuthContext';

// Mock component to test the useAuth hook
const AuthTestComponent = () => {
  const { user, loading, login, logout, hasRole } = useAuth();
  
  return (
    <div>
      {loading ? (
        <div data-testid="loading">Loading...</div>
      ) : (
        <>
          <div data-testid="auth-status">
            {user ? `Logged in as ${user.username} (${user.role})` : 'Not logged in'}
          </div>
          <button
            data-testid="login-btn"
            onClick={() => login('testuser', 'password')}
          >
            Login
          </button>
          <button
            data-testid="logout-btn"
            onClick={() => logout()}
          >
            Logout
          </button>
          <div data-testid="admin-role">
            Has admin role: {hasRole('admin').toString()}
          </div>
          <div data-testid="user-role">
            Has user role: {hasRole('user').toString()}
          </div>
        </>
      )}
    </div>
  );
};

describe('AuthContext', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });
  
  test('initial state shows loading and then not logged in', async () => {
    // Mock session check - no session
    (api.getSession as jest.Mock).mockResolvedValue({ authenticated: false });
    
    render(
      <AuthProvider>
        <AuthTestComponent />
      </AuthProvider>
    );
    
    // First shows loading
    expect(screen.getByTestId('loading')).toBeInTheDocument();
    
    // Then shows logged out state
    await waitFor(() => {
      expect(screen.queryByTestId('loading')).not.toBeInTheDocument();
      expect(screen.getByTestId('auth-status')).toHaveTextContent('Not logged in');
    });
  });
  
  test('login function successfully logs in a user', async () => {
    // Mock login API call
    (api.getSession as jest.Mock).mockResolvedValue({ authenticated: false });
    
    // Ensure the mock for api.login is correctly implemented
    (api.login as jest.Mock).mockImplementation((username, password) => {
      if (username === 'testuser' && password === 'password') {
        return Promise.resolve({ user: { username: 'testuser', role: 'user' } });
      }
      return Promise.reject(new Error('Invalid credentials'));
    });
    
    render(
      <AuthProvider>
        <AuthTestComponent />
      </AuthProvider>
    );
    
    // Wait for initial loading to complete
    await waitFor(() => {
      expect(screen.queryByTestId('loading')).not.toBeInTheDocument();
    });
    
    // Click login button
    fireEvent.click(screen.getByTestId('login-btn'));
    
    // Verify login state updates
    await waitFor(() => {
      expect(screen.getByTestId('auth-status')).toHaveTextContent('Logged in as testuser (user)');
      expect(screen.getByTestId('admin-role')).toHaveTextContent('Has admin role: false');
      expect(screen.getByTestId('user-role')).toHaveTextContent('Has user role: true');
    });
  });
  
  test('logout function successfully logs out a user', async () => {
    // Mock both API calls - first for session check (logged in), then for logout
    (api.getSession as jest.Mock).mockResolvedValue({
      authenticated: true,
      user: {
        id: 'user-123',
        username: 'testuser',
        email: 'test@example.com',
        role: 'user'
      }
    });
    
    (api.logout as jest.Mock).mockResolvedValue({
      message: 'Logged out successfully'
    });
    
    render(
      <AuthProvider>
        <AuthTestComponent />
      </AuthProvider>
    );
    
    // Wait for initial loading to complete and confirm logged in
    await waitFor(() => {
      expect(screen.queryByTestId('loading')).not.toBeInTheDocument();
      expect(screen.getByTestId('auth-status')).toHaveTextContent('Logged in as testuser (user)');
    });
    
    // Click logout button
    fireEvent.click(screen.getByTestId('logout-btn'));
    
    // Verify logged out state
    await waitFor(() => {
      expect(screen.getByTestId('auth-status')).toHaveTextContent('Not logged in');
      expect(screen.getByTestId('admin-role')).toHaveTextContent('Has admin role: false');
      expect(screen.getByTestId('user-role')).toHaveTextContent('Has user role: false');
    });
  });
  
  test('hasRole correctly checks user roles', async () => {
    // Mock login with admin role
    (api.getSession as jest.Mock).mockResolvedValue({
      authenticated: true,
      user: {
        id: 'admin-123',
        username: 'adminuser',
        email: 'admin@example.com',
        role: 'admin'
      }
    });
    
    render(
      <AuthProvider>
        <AuthTestComponent />
      </AuthProvider>
    );
    
    // Wait for initial loading to complete
    await waitFor(() => {
      expect(screen.queryByTestId('loading')).not.toBeInTheDocument();
      expect(screen.getByTestId('admin-role')).toHaveTextContent('Has admin role: true');
      expect(screen.getByTestId('user-role')).toHaveTextContent('Has user role: false');
    });
  });
  
  test('handles API errors during session check', async () => {
    // Mock API error during session check
    (api.getSession as jest.Mock).mockRejectedValue(new Error('Network error'));
    
    // Mock console.error to prevent test output pollution
    const originalConsoleError = console.error;
    console.error = jest.fn();
    
    render(
      <AuthProvider>
        <AuthTestComponent />
      </AuthProvider>
    );
    
    // Should complete loading and show not logged in
    await waitFor(() => {
      expect(screen.queryByTestId('loading')).not.toBeInTheDocument();
      expect(screen.getByTestId('auth-status')).toHaveTextContent('Not logged in');
    });
    
    // Restore console.error
    console.error = originalConsoleError;
  });
  
  test('handles API errors during login', async () => {
    // Mock initial session check
    (api.getSession as jest.Mock).mockResolvedValue({ authenticated: false });
    
    // Mock API error during login
    (api.login as jest.Mock).mockRejectedValue(new Error('Invalid credentials'));
    
    // Mock console.error to prevent test output pollution
    const originalConsoleError = console.error;
    console.error = jest.fn();
    
    render(
      <AuthProvider>
        <AuthTestComponent />
      </AuthProvider>
    );
    
    // Wait for initial loading to complete
    await waitFor(() => {
      expect(screen.queryByTestId('loading')).not.toBeInTheDocument();
    });
    
    // Attempt login - should fail
    await act(async () => {
      fireEvent.click(screen.getByTestId('login-btn'));
    });
    
    // Should remain logged out
    expect(screen.getByTestId('auth-status')).toHaveTextContent('Not logged in');
    expect(console.error).toHaveBeenCalled();
    
    // Restore console.error
    console.error = originalConsoleError;
  });
});
