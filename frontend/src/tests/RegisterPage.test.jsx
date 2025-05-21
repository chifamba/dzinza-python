import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter as Router } from 'react-router-dom';
import { AuthProvider, useAuth } from '../context/AuthContext';
import RegisterPage from '../components/RegisterPage'; // Adjusted import path
import '@testing-library/jest-dom';

// Mock useAuth hook
const mockRegister = jest.fn();
const mockNavigate = jest.fn();

jest.mock('../context/AuthContext', () => ({
  ...jest.requireActual('../context/AuthContext'),
  useAuth: () => ({
    register: mockRegister,
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

describe('RegisterPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
     // Reset useAuth mock for each test
    jest.spyOn(require('../context/AuthContext'), 'useAuth').mockReturnValue({
        register: mockRegister,
        isAuthenticated: false,
        error: null,
        loading: false,
      });
  });

  const renderComponent = (authContextValue = {}) => {
     const actualAuthContext = jest.requireActual('../context/AuthContext');
     const mockUseAuth = {
        register: mockRegister,
        isAuthenticated: false,
        error: null,
        loading: false,
        ...authContextValue, 
      };
    jest.spyOn(actualAuthContext, 'useAuth').mockImplementation(() => mockUseAuth);

    return render(
      <Router>
        <AuthProvider>
          <RegisterPage />
        </AuthProvider>
      </Router>
    );
  };

  it('renders registration form correctly', () => {
    renderComponent();
    expect(screen.getByRole('heading', { name: /register/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/full name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /register/i })).toBeInTheDocument();
    expect(screen.getByText(/already have an account\?/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /login here/i })).toBeInTheDocument();
  });

  it('allows typing in all form fields', () => {
    renderComponent();
    fireEvent.change(screen.getByLabelText(/full name/i), { target: { value: 'Test User' } });
    fireEvent.change(screen.getByLabelText(/username/i), { target: { value: 'testuser' } });
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'test@example.com' } });
    fireEvent.change(screen.getByLabelText(/^password$/i), { target: { value: 'password123' } });
    fireEvent.change(screen.getByLabelText(/confirm password/i), { target: { value: 'password123' } });

    expect(screen.getByLabelText(/full name/i).value).toBe('Test User');
    expect(screen.getByLabelText(/username/i).value).toBe('testuser');
    expect(screen.getByLabelText(/email/i).value).toBe('test@example.com');
    expect(screen.getByLabelText(/^password$/i).value).toBe('password123');
    expect(screen.getByLabelText(/confirm password/i).value).toBe('password123');
  });

  it('calls register function on form submit and navigates on success', async () => {
    mockRegister.mockResolvedValueOnce(); // Simulate successful registration
    renderComponent();

    fireEvent.change(screen.getByLabelText(/full name/i), { target: { value: 'Test User' } });
    fireEvent.change(screen.getByLabelText(/username/i), { target: { value: 'testuser' } });
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'test@example.com' } });
    fireEvent.change(screen.getByLabelText(/^password$/i), { target: { value: 'password123' } });
    fireEvent.change(screen.getByLabelText(/confirm password/i), { target: { value: 'password123' } });
    fireEvent.click(screen.getByRole('button', { name: /register/i }));

    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalledWith('testuser', 'test@example.com', 'password123', 'Test User');
    });
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
    });
  });

  it('displays error message if passwords do not match', async () => {
    renderComponent();
    fireEvent.change(screen.getByLabelText(/^password$/i), { target: { value: 'password123' } });
    fireEvent.change(screen.getByLabelText(/confirm password/i), { target: { value: 'password456' } });
    fireEvent.click(screen.getByRole('button', { name: /register/i }));

    await waitFor(() => {
      expect(screen.getByText(/passwords do not match/i)).toBeInTheDocument();
    });
    expect(mockRegister).not.toHaveBeenCalled();
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it('displays error message from AuthContext on registration failure', async () => {
    const errorMessage = 'Username already taken';
    mockRegister.mockRejectedValueOnce(new Error(errorMessage)); // Simulate failed registration

    // Update useAuth mock to include the error
    jest.spyOn(require('../context/AuthContext'), 'useAuth').mockReturnValue({
        register: mockRegister,
        isAuthenticated: false,
        error: errorMessage, // Make sure error is passed down from context
        loading: false,
      });
      
    render( // Re-render with the component that will receive the error
        <Router>
          <AuthProvider>
            <RegisterPage />
          </AuthProvider>
        </Router>
      );

    fireEvent.change(screen.getByLabelText(/full name/i), { target: { value: 'Test User' } });
    fireEvent.change(screen.getByLabelText(/username/i), { target: { value: 'testuser' } });
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'test@example.com' } });
    fireEvent.change(screen.getByLabelText(/^password$/i), { target: { value: 'password123' } });
    fireEvent.change(screen.getByLabelText(/confirm password/i), { target: { value: 'password123' } });
    
    // The error should be displayed from the context after the register attempt
    // Forcing the error directly for this render to test display:
     jest.spyOn(require('../context/AuthContext'), 'useAuth').mockReturnValue({
        register: mockRegister,
        isAuthenticated: false,
        error: errorMessage,
        loading: false,
      });
    render(
        <Router>
            <RegisterPage />
        </Router>
    );


    expect(screen.getByText(errorMessage)).toBeInTheDocument();
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it('disables register button while loading', () => {
     jest.spyOn(require('../context/AuthContext'), 'useAuth').mockReturnValue({
        register: mockRegister,
        isAuthenticated: false,
        error: null,
        loading: true, // Set loading to true
      });
    renderComponent({ loading: true });
    expect(screen.getByRole('button', { name: /registering.../i })).toBeDisabled();
  });

  it('redirects to dashboard if already authenticated', () => {
    jest.spyOn(require('../context/AuthContext'), 'useAuth').mockReturnValue({
        register: mockRegister,
        isAuthenticated: true, // User is authenticated
        error: null,
        loading: false,
      });
    renderComponent({ isAuthenticated: true });
    expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
  });

  it('navigates to login page when "Login here" link is clicked', () => {
    renderComponent();
    fireEvent.click(screen.getByRole('link', { name: /login here/i }));
    expect(mockNavigate).toHaveBeenCalledWith('/login');
  });

   it('does not submit if a required field is empty', async () => {
    renderComponent();
    // Leave username empty
    fireEvent.change(screen.getByLabelText(/full name/i), { target: { value: 'Test User' } });
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'test@example.com' } });
    fireEvent.change(screen.getByLabelText(/^password$/i), { target: { value: 'password123' } });
    fireEvent.change(screen.getByLabelText(/confirm password/i), { target: { value: 'password123' } });
    fireEvent.click(screen.getByRole('button', { name: /register/i }));

    await waitFor(() => {
        expect(mockRegister).not.toHaveBeenCalled();
    });
    // You might want to add specific client-side validation messages if they exist
    // For example: expect(screen.getByText(/username is required/i)).toBeInTheDocument();
  });

});
