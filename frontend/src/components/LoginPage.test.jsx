import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom'; // For extended matchers like .toBeInTheDocument()
import { BrowserRouter } from 'react-router-dom'; // Needed for useNavigate hook used indirectly by AuthContext/LoginPage
import { AuthProvider } from '../context/AuthContext'; // Wrap with provider
import LoginPage from './LoginPage';
import api from '../api'; // Mock the API module

// Mock the api module
jest.mock('../api');

// Mock useNavigate used within AuthContext/LoginPage
const mockedNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'), // Use actual implementation for other hooks/components
  useNavigate: () => mockedNavigate,
}));

// Helper function to render component within necessary providers
const renderLoginPage = () => {
  return render(
    <BrowserRouter>
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    </BrowserRouter>
  );
};

describe('LoginPage Component', () => {
  beforeEach(() => {
    // Reset mocks before each test
    jest.clearAllMocks();
    // Mock successful login by default
    api.login.mockResolvedValue({
      message: 'Login successful!',
      user: { id: 'test-id', username: 'testuser', role: 'basic' },
    });
  });

  test('renders login form correctly', () => {
    renderLoginPage();

    // Check if essential elements are present
    expect(screen.getByRole('heading', { name: /login/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument();
  });

  test('allows entering username and password', () => {
    renderLoginPage();

    const usernameInput = screen.getByLabelText(/username/i);
    const passwordInput = screen.getByLabelText(/password/i);

    fireEvent.change(usernameInput, { target: { value: 'testuser' } });
    fireEvent.change(passwordInput, { target: { value: 'password123' } });

    expect(usernameInput.value).toBe('testuser');
    expect(passwordInput.value).toBe('password123');
  });

  test('calls login API on form submission and navigates on success', async () => {
    renderLoginPage();

    const usernameInput = screen.getByLabelText(/username/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const loginButton = screen.getByRole('button', { name: /login/i });

    // Enter credentials
    fireEvent.change(usernameInput, { target: { value: 'testuser' } });
    fireEvent.change(passwordInput, { target: { value: 'password123' } });

    // Submit form
    fireEvent.click(loginButton);

    // Check if api.login was called with correct credentials
    await waitFor(() => {
      expect(api.login).toHaveBeenCalledTimes(1);
      expect(api.login).toHaveBeenCalledWith('testuser', 'password123');
    });

    // Check for success message (might disappear quickly due to timeout)
    await waitFor(() => {
      expect(screen.getByText(/login successful!/i)).toBeInTheDocument();
    });

    // Check if navigation was called (after timeout in component)
    // Use fake timers to control setTimeout
    jest.useFakeTimers();
    fireEvent.click(loginButton); // Submit again with fake timers
    await waitFor(() => expect(api.login).toHaveBeenCalledTimes(1)); // Ensure API call finishes
    // Fast-forward time past the 3-second delay in LoginPage
    jest.advanceTimersByTime(3000);
    expect(mockedNavigate).toHaveBeenCalledWith('/'); // Check navigation target
    jest.useRealTimers(); // Restore real timers
  });

  test('displays error message on login failure', async () => {
    // Mock API call to simulate failure
    const errorResponse = {
      response: {
        status: 401,
        data: { error: 'Invalid username or password.' },
      },
    };
    api.login.mockRejectedValue(errorResponse);

    renderLoginPage();

    const usernameInput = screen.getByLabelText(/username/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const loginButton = screen.getByRole('button', { name: /login/i });

    // Enter credentials and submit
    fireEvent.change(usernameInput, { target: { value: 'testuser' } });
    fireEvent.change(passwordInput, { target: { value: 'wrongpassword' } });
    fireEvent.click(loginButton);

    // Wait for error message to appear
    await waitFor(() => {
      // Check for the specific error message based on the component's logic
      expect(screen.getByText(/incorrect username or password/i)).toBeInTheDocument();
    });

    // Ensure navigation did not happen
    expect(mockedNavigate).not.toHaveBeenCalled();
  });

  test('disables login button while loading', async () => {
     // Make the API call take time
     api.login.mockImplementation(() => new Promise(resolve => setTimeout(() => resolve({
         message: 'Login successful!',
         user: { id: 'test-id', username: 'testuser', role: 'basic' },
     }), 100)));

     renderLoginPage();

     const loginButton = screen.getByRole('button', { name: /login/i });

     // Initial state: button enabled
     expect(loginButton).not.toBeDisabled();

     // Click the button
     fireEvent.click(loginButton);

     // Button should be disabled immediately after click
     expect(loginButton).toBeDisabled();

     // Wait for the API call to resolve
     await waitFor(() => {
         expect(api.login).toHaveBeenCalledTimes(1);
     });

     // After API call resolves and state updates, button might be enabled again
     // depending on navigation or success message display logic.
     // For this test, we mainly care it's disabled *during* the call.
  });

});
