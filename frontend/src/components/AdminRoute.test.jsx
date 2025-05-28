import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from '../context/AuthContext';
import AdminRoute from './AdminRoute';

// Mocking the AuthContext
jest.mock('../context/AuthContext', () => ({
  useAuth: jest.fn(),
  AuthProvider: ({ children }) => <div>{children}</div>,
}));

describe('AdminRoute Component', () => {
  const mockUseAuth = jest.requireMock('../context/AuthContext').useAuth;

  beforeEach(() => {
    mockUseAuth.mockClear();
  });

  test('renders children when user is admin', () => {
    mockUseAuth.mockReturnValue({
      user: { id: 'admin1', username: 'admin', role: 'admin' },
      loading: false,
    });

    render(
      <MemoryRouter>
        <AdminRoute>
          <div data-testid="protected-content">Admin content</div>
        </AdminRoute>
      </MemoryRouter>
    );

    expect(screen.getByTestId('protected-content')).toBeInTheDocument();
    expect(screen.getByText('Admin content')).toBeInTheDocument();
  });

  test('redirects to login when user is null', () => {
    mockUseAuth.mockReturnValue({
      user: null,
      loading: false,
    });

    render(
      <MemoryRouter initialEntries={['/admin']}>
        <Routes>
          <Route path="/login" element={<div data-testid="login-page">Login page</div>} />
          <Route 
            path="/admin" 
            element={
              <AdminRoute>
                <div data-testid="admin-content">Admin content</div>
              </AdminRoute>
            } 
          />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByTestId('login-page')).toBeInTheDocument();
    expect(screen.queryByTestId('admin-content')).not.toBeInTheDocument();
  });

  test('redirects to dashboard when user is not admin', () => {
    mockUseAuth.mockReturnValue({
      user: { id: 'user1', username: 'regularuser', role: 'user' },
      loading: false,
    });

    render(
      <MemoryRouter initialEntries={['/admin']}>
        <Routes>
          <Route path="/dashboard" element={<div data-testid="dashboard-page">Dashboard page</div>} />
          <Route 
            path="/admin" 
            element={
              <AdminRoute>
                <div data-testid="admin-content">Admin content</div>
              </AdminRoute>
            } 
          />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
    expect(screen.queryByTestId('admin-content')).not.toBeInTheDocument();
  });

  test('shows loading indicator when authentication is loading', () => {
    mockUseAuth.mockReturnValue({
      user: null,
      loading: true,
    });

    render(
      <MemoryRouter>
        <AdminRoute>
          <div>Admin content</div>
        </AdminRoute>
      </MemoryRouter>
    );

    expect(screen.getByText(/Checking permissions/i)).toBeInTheDocument();
  });
});
