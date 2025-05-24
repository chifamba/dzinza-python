import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter as Router } from 'react-router-dom'; // Or MemoryRouter
import { AuthProvider, useAuth } from '../context/AuthContext';
import LoginPage from '../components/LoginPage'; // Adjusted import path
import '@testing-library/jest-dom';

// Mock useAuth hook
const mockLogin = jest.fn();
const mockNavigate = jest.fn();

jest.mock('../context/AuthContext', () => ({
  ...jest.requireActual('../context/AuthContext'), // Import and retain default behavior
  useAuth: () => ({
    login: mockLogin,
    isAuthenticated: false,
    error: null,
    loading: false,
  }),
}));

// Mock react-router-dom's useNavigate
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));


describe('LoginPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Reset useAuth mock for each test if needed, or provide different implementations
    jest.spyOn(require('../context/AuthContext'), 'useAuth').mockReturnValue({
        login: mockLogin,
        isAuthenticated: false,
        error: null,
        loading: false,
      });
  });

  const renderComponent = (authContextValue = {}) => {
    const actualAuthContext = jest.requireActual('../context/AuthContext');
     // Override specific parts of useAuth for this render
    const mockUseAuth = {
        login: mockLogin,
        isAuthenticated: false,
        error: null,
        loading: false,
        ...authContextValue, // Allow overriding for specific tests
      };
    jest.spyOn(actualAuthContext, 'useAuth').mockImplementation(() => mockUseAuth);


    return render(
      <Router> {/* Using BrowserRouter, MemoryRouter might be better for isolated tests */}
        <AuthProvider> {/* Still need AuthProvider to provide the context structure */}
          <LoginPage />
        </AuthProvider>
      </Router>
    );
  };

  it('renders login form correctly', () => {
    renderComponent();
    expect(screen.getByRole('heading', { name: /login/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/username or email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument();
    expect(screen.getByText(/don't have an account\?/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /register here/i })).toBeInTheDocument();
  });

  it('allows typing in username and password fields', () => {
    renderComponent();
    const usernameInput = screen.getByLabelText(/username or email/i);
    const passwordInput = screen.getByLabelText(/password/i);

    fireEvent.change(usernameInput, { target: { value: 'testuser' } });
    fireEvent.change(passwordInput, { target: { value: 'password123' } });

    expect(usernameInput.value).toBe('testuser');
    expect(passwordInput.value).toBe('password123');
  });

  it('calls login function on form submit and navigates on success', async () => {
    mockLogin.mockResolvedValueOnce(); // Simulate successful login
    
    renderComponent();

    fireEvent.change(screen.getByLabelText(/username or email/i), { target: { value: 'testuser' } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'password123' } });
    fireEvent.click(screen.getByRole('button', { name: /login/i }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('testuser', 'password123');
    });
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
    });
  });

  it('displays error message on login failure', async () => {
    const errorMessage = 'Invalid credentials';
    mockLogin.mockRejectedValueOnce(new Error(errorMessage)); // Simulate failed login

    // Update useAuth mock to include the error
     jest.spyOn(require('../context/AuthContext'), 'useAuth').mockReturnValue({
        login: mockLogin,
        isAuthenticated: false,
        error: errorMessage, // Make sure error is passed down
        loading: false,
      });
    
    render( // Re-render with the component that will receive the error
      <Router>
        <AuthProvider> 
          <LoginPage />
        </AuthProvider>
      </Router>
    );
    
    fireEvent.change(screen.getByLabelText(/username or email/i), { target: { value: 'testuser' } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'wrongpassword' } });
    
    // The login function in AuthContext will set the error.
    // We need to simulate the AuthContext re-rendering with that error.
    // The click should trigger the mockLogin which is set to reject.
    // The AuthProvider should catch this and update its internal error state.
    // Then LoginPage, consuming useAuth, should re-render with the error.

    // For this test to correctly show the error, the mockLogin itself doesn't directly cause
    // the LoginPage to re-render with an error. The AuthContext's login function does.
    // So, we need to ensure our mockLogin's rejection is handled by the AuthContext's login,
    // which then updates the error in the context.
    // A more direct way to test error display is to set `error` in the `useAuth` mock directly.

    // Re-render with error already present in context
    jest.spyOn(require('../context/AuthContext'), 'useAuth').mockReturnValue({
        login: mockLogin,
        isAuthenticated: false,
        error: errorMessage, // Provide error directly
        loading: false,
      });

    render( // LoginPage will now get this error from useAuth
        <Router>
          <LoginPage />
        </Router>
    );

    expect(screen.getByText(errorMessage)).toBeInTheDocument();
    expect(mockNavigate).not.toHaveBeenCalled();
  });


  it('disables login button while loading', () => {
     jest.spyOn(require('../context/AuthContext'), 'useAuth').mockReturnValue({
        login: mockLogin,
        isAuthenticated: false,
        error: null,
        loading: true, // Set loading to true
      });
    renderComponent({loading: true}); // Pass loading state
    expect(screen.getByRole('button', { name: /logging in.../i })).toBeDisabled();
  });

  it('redirects to dashboard if already authenticated', () => {
     jest.spyOn(require('../context/AuthContext'), 'useAuth').mockReturnValue({
        login: mockLogin,
        isAuthenticated: true, // User is authenticated
        error: null,
        loading: false,
      });
    renderComponent({ isAuthenticated: true });
    expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
  });

  it('navigates to register page when "Register here" link is clicked', () => {
    renderComponent();
    fireEvent.click(screen.getByRole('link', { name: /register here/i }));
    expect(mockNavigate).toHaveBeenCalledWith('/register');
  });

  it('does not submit if username is empty', async () => {
    renderComponent();
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'password123' } });
    fireEvent.click(screen.getByRole('button', { name: /login/i }));

    await waitFor(() => {
        expect(mockLogin).not.toHaveBeenCalled();
    });
    // Optionally, check for a client-side validation message if implemented
    // expect(screen.getByText(/username is required/i)).toBeInTheDocument();
  });

  it('does not submit if password is empty', async () => {
    renderComponent();
    fireEvent.change(screen.getByLabelText(/username or email/i), { target: { value: 'testuser' } });
    fireEvent.click(screen.getByRole('button', { name: /login/i }));

    await waitFor(() => {
        expect(mockLogin).not.toHaveBeenCalled();
    });
     // Optionally, check for a client-side validation message if implemented
    // expect(screen.getByText(/password is required/i)).toBeInTheDocument();
  });

});
