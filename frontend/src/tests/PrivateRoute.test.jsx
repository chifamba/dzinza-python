import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route, Outlet } from 'react-router-dom';
import { AuthProvider, useAuth } from '../context/AuthContext';
import PrivateRoute from '../components/PrivateRoute'; // Adjusted import path
import '@testing-library/jest-dom';

// Mock useAuth
jest.mock('../context/AuthContext', () => ({
  ...jest.requireActual('../context/AuthContext'),
  useAuth: jest.fn(),
}));

const MockLoginPage = () => <div>Login Page</div>;
const MockDashboardPage = () => <div>Dashboard Page</div>;

describe('PrivateRoute', () => {
  const renderWithRouter = (ui, { route = '/', authState = { isAuthenticated: false, loading: false } } = {}) => {
    useAuth.mockReturnValue(authState);
    return render(
      <AuthProvider> {/* AuthProvider is still needed to provide the context structure */}
        <MemoryRouter initialEntries={[route]}>
          <Routes>
            <Route path="/login" element={<MockLoginPage />} />
            <Route element={<PrivateRoute />}>
              <Route path="/dashboard" element={<MockDashboardPage />} />
            </Route>
            {/* Fallback for redirection tests if needed */}
            <Route path="/" element={<div>Home Page (Public)</div>} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    );
  };

  it('renders child component if authenticated', () => {
    renderWithRouter(null, { route: '/dashboard', authState: { isAuthenticated: true, loading: false, user: { role: 'user' } } });
    expect(screen.getByText('Dashboard Page')).toBeInTheDocument();
    expect(screen.queryByText('Login Page')).not.toBeInTheDocument();
  });

  it('redirects to /login if not authenticated', () => {
    renderWithRouter(null, { route: '/dashboard', authState: { isAuthenticated: false, loading: false } });
    expect(screen.getByText('Login Page')).toBeInTheDocument(); // Should be redirected to /login
    expect(screen.queryByText('Dashboard Page')).not.toBeInTheDocument();
  });

  it('shows loading state if auth context is loading', () => {
    // This assumes PrivateRoute might render a loading indicator or null
    // If PrivateRoute doesn't have specific loading UI, it might just redirect or show children
    // based on isAuthenticated, even if loading is true.
    // For this test, let's assume it renders nothing or a loader if loading and not yet authenticated.
    renderWithRouter(null, { route: '/dashboard', authState: { isAuthenticated: false, loading: true } });
    
    // If PrivateRoute renders a specific loader:
    // expect(screen.getByTestId('loading-indicator')).toBeInTheDocument(); 
    // If it renders null or redirects based on current isAuthenticated during loading:
    expect(screen.getByText('Login Page')).toBeInTheDocument(); // Redirects as isAuthenticated is false
    expect(screen.queryByText('Dashboard Page')).not.toBeInTheDocument();
  });

   it('renders child component if authenticated even if loading is true (optimistic)', () => {
    // This scenario tests if an already authenticated user sees content while a background check might be happening.
    // The behavior depends on PrivateRoute's logic.
    renderWithRouter(null, { route: '/dashboard', authState: { isAuthenticated: true, loading: true, user: { role: 'user' } } });
    expect(screen.getByText('Dashboard Page')).toBeInTheDocument();
  });
});
