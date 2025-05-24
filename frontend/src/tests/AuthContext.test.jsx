import React from 'react';
import { render, screen, act } from '@testing-library/react';
import { AuthProvider, useAuth } from '../context/AuthContext'; // Adjust path as needed
import * as api from '../api'; // Adjust path to your api file
import '@testing-library/jest-dom';

// Mock the api module
jest.mock('../api', () => ({
  loginUser: jest.fn(),
  registerUser: jest.fn(),
  logoutUser: jest.fn(),
  checkSession: jest.fn(),
}));

// LocalStorage mock
const localStorageMock = (() => {
  let store = {};
  return {
    getItem: (key) => store[key] || null,
    setItem: (key, value) => {
      store[key] = value.toString();
    },
    removeItem: (key) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

const TestConsumerComponent = () => {
  const { user, token, isAuthenticated, login, logout, register, loading, error } = useAuth();
  return (
    <div>
      <div data-testid="isAuthenticated">{isAuthenticated.toString()}</div>
      <div data-testid="loading">{loading.toString()}</div>
      {user && <div data-testid="username">{user.username}</div>}
      {user && <div data-testid="role">{user.role}</div>}
      {token && <div data-testid="token">{token}</div>}
      {error && <div data-testid="error">{error}</div>}
      <button onClick={() => login('testuser', 'password')}>Login</button>
      <button onClick={() => register('newuser', 'new@example.com', 'password', 'New User')}>Register</button>
      <button onClick={logout}>Logout</button>
    </div>
  );
};

describe('AuthContext', () => {
  beforeEach(() => {
    // Reset mocks and localStorage before each test
    jest.clearAllMocks();
    localStorageMock.clear();
  });

  it('initial state is not authenticated and not loading', async () => {
    api.checkSession.mockResolvedValue({ isAuthenticated: false });
    await act(async () => {
      render(
        <AuthProvider>
          <TestConsumerComponent />
        </AuthProvider>
      );
    });
    expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('false');
    expect(screen.getByTestId('loading')).toHaveTextContent('false');
    expect(screen.queryByTestId('username')).not.toBeInTheDocument();
  });

  it('login successfully updates context and localStorage', async () => {
    const mockUserData = { id: '1', username: 'testuser', role: 'user', active_tree_id: null };
    const mockToken = 'fake-token';
    api.loginUser.mockResolvedValue({ user: mockUserData, token: mockToken });

    await act(async () => {
      render(
        <AuthProvider>
          <TestConsumerComponent />
        </AuthProvider>
      );
    });
    
    await act(async () => {
      screen.getByText('Login').click();
    });

    expect(api.loginUser).toHaveBeenCalledWith('testuser', 'password');
    expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('true');
    expect(screen.getByTestId('username')).toHaveTextContent('testuser');
    expect(screen.getByTestId('role')).toHaveTextContent('user');
    expect(screen.getByTestId('token')).toHaveTextContent(mockToken);
    expect(localStorageMock.getItem('user')).toEqual(JSON.stringify(mockUserData));
    expect(localStorageMock.getItem('token')).toEqual(mockToken);
    expect(screen.queryByTestId('error')).not.toBeInTheDocument();
  });

  it('login failure updates error state', async () => {
    const errorMessage = 'Invalid credentials';
    api.loginUser.mockRejectedValue(new Error(errorMessage));
    
    await act(async () => {
      render(
        <AuthProvider>
          <TestConsumerComponent />
        </AuthProvider>
      );
    });

    await act(async () => {
      screen.getByText('Login').click();
    });

    expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('false');
    expect(screen.getByTestId('error')).toHaveTextContent(errorMessage);
    expect(localStorageMock.getItem('user')).toBeNull();
    expect(localStorageMock.getItem('token')).toBeNull();
  });

  it('register successfully updates context and localStorage', async () => {
    const mockUserData = { id: '2', username: 'newuser', role: 'user', active_tree_id: null };
    const mockToken = 'new-fake-token';
    api.registerUser.mockResolvedValue({ user: mockUserData, token: mockToken });

    await act(async () => {
      render(
        <AuthProvider>
          <TestConsumerComponent />
        </AuthProvider>
      );
    });

    await act(async () => {
      screen.getByText('Register').click();
    });
    
    expect(api.registerUser).toHaveBeenCalledWith('newuser', 'new@example.com', 'password', 'New User');
    expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('true');
    expect(screen.getByTestId('username')).toHaveTextContent('newuser');
    expect(screen.getByTestId('token')).toHaveTextContent(mockToken);
    expect(localStorageMock.getItem('user')).toEqual(JSON.stringify(mockUserData));
    expect(localStorageMock.getItem('token')).toEqual(mockToken);
  });

  it('register failure updates error state', async () => {
    const errorMessage = 'Username already exists';
    api.registerUser.mockRejectedValue(new Error(errorMessage));

    await act(async () => {
      render(
        <AuthProvider>
          <TestConsumerComponent />
        </AuthProvider>
      );
    });

    await act(async () => {
      screen.getByText('Register').click();
    });

    expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('false');
    expect(screen.getByTestId('error')).toHaveTextContent(errorMessage);
  });


  it('logout clears context and localStorage', async () => {
    // First, simulate a login
    const mockUserData = { id: '1', username: 'testuser', role: 'user' };
    const mockToken = 'fake-token';
    localStorageMock.setItem('user', JSON.stringify(mockUserData));
    localStorageMock.setItem('token', mockToken);
    api.checkSession.mockResolvedValue({ isAuthenticated: true, user: mockUserData, token: mockToken });
    api.logoutUser.mockResolvedValue({}); // Mock logout API call

    await act(async () => {
      render(
        <AuthProvider>
          <TestConsumerComponent />
        </AuthProvider>
      );
    });
    
    // Verify initial logged-in state from localStorage
    expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('true');
    expect(screen.getByTestId('username')).toHaveTextContent('testuser');

    await act(async () => {
      screen.getByText('Logout').click();
    });

    expect(api.logoutUser).toHaveBeenCalled();
    expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('false');
    expect(screen.queryByTestId('username')).not.toBeInTheDocument();
    expect(screen.queryByTestId('token')).not.toBeInTheDocument();
    expect(localStorageMock.getItem('user')).toBeNull();
    expect(localStorageMock.getItem('token')).toBeNull();
  });

  it('initializes from localStorage if session is valid', async () => {
    const mockUserData = { id: '1', username: 'storedUser', role: 'admin', active_tree_id: 'tree1' };
    const mockToken = 'stored-token';
    localStorageMock.setItem('user', JSON.stringify(mockUserData));
    localStorageMock.setItem('token', mockToken);
    api.checkSession.mockResolvedValue({ isAuthenticated: true, user: mockUserData, token: mockToken });

    await act(async () => {
      render(
        <AuthProvider>
          <TestConsumerComponent />
        </AuthProvider>
      );
    });

    expect(api.checkSession).toHaveBeenCalled();
    expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('true');
    expect(screen.getByTestId('username')).toHaveTextContent('storedUser');
    expect(screen.getByTestId('role')).toHaveTextContent('admin');
    expect(screen.getByTestId('token')).toHaveTextContent(mockToken);
  });

  it('clears localStorage if checkSession returns not authenticated despite stored token', async () => {
    const mockUserData = { id: '1', username: 'storedUser', role: 'admin' };
    const mockToken = 'stored-token';
    localStorageMock.setItem('user', JSON.stringify(mockUserData));
    localStorageMock.setItem('token', mockToken);
    api.checkSession.mockResolvedValue({ isAuthenticated: false }); // API says session is invalid

    await act(async () => {
      render(
        <AuthProvider>
          <TestConsumerComponent />
        </AuthProvider>
      );
    });

    expect(api.checkSession).toHaveBeenCalled();
    expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('false');
    expect(localStorageMock.getItem('user')).toBeNull();
    expect(localStorageMock.getItem('token')).toBeNull();
  });

   it('handles checkSession API failure gracefully', async () => {
    localStorageMock.setItem('token', 'some-token'); // Simulate existing token
    api.checkSession.mockRejectedValue(new Error('Network error'));

    await act(async () => {
      render(
        <AuthProvider>
          <TestConsumerComponent />
        </AuthProvider>
      );
    });
    
    expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('false');
    expect(screen.getByTestId('loading')).toHaveTextContent('false'); // Should stop loading
    expect(screen.getByTestId('error')).toHaveTextContent('Failed to check session: Network error');
    expect(localStorageMock.getItem('user')).toBeNull(); // Should clear local storage on error
    expect(localStorageMock.getItem('token')).toBeNull();
  });
});
