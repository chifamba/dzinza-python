import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider, useAuth } from '../context/AuthContext';
import AdminRoute from '../components/AdminRoute'; // Adjusted import path
import '@testing-library/jest-dom';

// Mock useAuth
jest.mock('../context/AuthContext', () => ({
  ...jest.requireActual('../context/AuthContext'),
  useAuth: jest.fn(),
}));

const MockLoginPage = () => <div>Login Page</div>;
const MockDashboardPage = () => <div>Dashboard Page</div>; // Non-admin fallback
const MockAdminContentPage = () => <div>Admin Content Page</div>;


describe('AdminRoute', () => {
  const renderWithRouter = (ui, { route = '/', authState = { isAuthenticated: false, user: null, loading: false } } = {}) => {
    useAuth.mockReturnValue(authState);
    return render(
      <AuthProvider>
        <MemoryRouter initialEntries={[route]}>
          <Routes>
            <Route path="/login" element={<MockLoginPage />} />
            <Route path="/dashboard" element={<MockDashboardPage />} />
            <Route element={<AdminRoute />}>
              <Route path="/admin-only" element={<MockAdminContentPage />} />
            </Route>
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    );
  };

  it('renders admin child component if authenticated and user is admin', () => {
    renderWithRouter(null, { 
      route: '/admin-only', 
      authState: { isAuthenticated: true, user: { role: 'admin' }, loading: false } 
    });
    expect(screen.getByText('Admin Content Page')).toBeInTheDocument();
    expect(screen.queryByText('Login Page')).not.toBeInTheDocument();
    expect(screen.queryByText('Dashboard Page')).not.toBeInTheDocument();
  });

  it('redirects to /login if not authenticated', () => {
    renderWithRouter(null, { 
      route: '/admin-only', 
      authState: { isAuthenticated: false, user: null, loading: false } 
    });
    expect(screen.getByText('Login Page')).toBeInTheDocument();
    expect(screen.queryByText('Admin Content Page')).not.toBeInTheDocument();
  });

  it('redirects to /dashboard if authenticated but user is not admin', () => {
    renderWithRouter(null, { 
      route: '/admin-only', 
      authState: { isAuthenticated: true, user: { role: 'user' }, loading: false } 
    });
    expect(screen.getByText('Dashboard Page')).toBeInTheDocument(); // Redirects to dashboard
    expect(screen.queryByText('Admin Content Page')).not.toBeInTheDocument();
    expect(screen.queryByText('Login Page')).not.toBeInTheDocument();
  });
  
  it('shows loading state or redirects based on current auth if loading', () => {
    // Behavior during loading depends on AdminRoute's specific implementation.
    // If it waits for loading to finish, it might show nothing or a loader.
    // If it acts on current `isAuthenticated` and `user.role`, it will redirect.
    renderWithRouter(null, { 
      route: '/admin-only', 
      authState: { isAuthenticated: false, user: null, loading: true } 
    });
    // Assuming it redirects based on current (false) isAuthenticated
    expect(screen.getByText('Login Page')).toBeInTheDocument(); 
    expect(screen.queryByText('Admin Content Page')).not.toBeInTheDocument();
  });

  it('renders admin child if authenticated as admin even if loading is true (optimistic)', () => {
     renderWithRouter(null, { 
      route: '/admin-only', 
      authState: { isAuthenticated: true, user: { role: 'admin' }, loading: true } 
    });
    expect(screen.getByText('Admin Content Page')).toBeInTheDocument();
  });

   it('redirects to /dashboard if authenticated as non-admin even if loading is true (optimistic)', () => {
     renderWithRouter(null, { 
      route: '/admin-only', 
      authState: { isAuthenticated: true, user: { role: 'user' }, loading: true } 
    });
    expect(screen.getByText('Dashboard Page')).toBeInTheDocument();
  });
});
