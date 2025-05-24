import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react'; // Import waitFor
import '@testing-library/jest-dom';
import AddPersonPage from './AddPersonPage';
import { BrowserRouter } from 'react-router-dom'; 
import api from '../api'; // Ensure api is imported for mocking its methods

// Mock dependencies
const mockedNavigate = jest.fn();
jest.mock('../api'); // This will mock all exports from ../api

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockedNavigate, // Use the hoisted mockedNavigate
  Link: ({ children, to }) => <a href={to}>{children}</a>,
}));
jest.mock('../context/AuthContext', () => ({
  useAuth: () => ({ activeTreeId: 'mock-tree-id' }),
}));

describe('AddPersonPage Component - Basic Rendering', () => {
  beforeEach(() => {
    // Render the component within BrowserRouter for each test
    render(
      <BrowserRouter>
        <AddPersonPage />
      </BrowserRouter>
    );
  });

  test('renders the main heading', () => {
    expect(screen.getByRole('heading', { name: /add new person/i })).toBeInTheDocument();
  });

  test('renders all standard input fields', () => {
    expect(screen.getByLabelText(/first name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/last name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/nickname/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/date of birth/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/place of birth/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/date of death/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/place of death/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/gender/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/notes/i)).toBeInTheDocument();
  });

  test('renders custom attribute and action buttons', () => {
    expect(screen.getByRole('button', { name: /add attribute/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /add person/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /cancel/i })).toBeInTheDocument();
  });
});

describe('AddPersonPage Component - Input Handling', () => {
  beforeEach(() => {
    render(
      <BrowserRouter>
        <AddPersonPage />
      </BrowserRouter>
    );
  });

  test('updates text input fields on change', () => {
    const firstNameInput = screen.getByLabelText(/first name/i);
    fireEvent.change(firstNameInput, { target: { value: 'John' } });
    expect(firstNameInput.value).toBe('John');

    const nicknameInput = screen.getByLabelText(/nickname/i);
    fireEvent.change(nicknameInput, { target: { value: 'Johnny' } });
    expect(nicknameInput.value).toBe('Johnny');
  });

  test('updates gender select field on change', () => {
    const genderSelect = screen.getByLabelText(/gender/i);
    fireEvent.change(genderSelect, { target: { value: 'Male' } });
    expect(genderSelect.value).toBe('Male');
  });

  test('allows adding, editing, and removing custom attributes', () => {
    const addAttributeButton = screen.getByRole('button', { name: /add attribute/i });
    fireEvent.click(addAttributeButton);

    // Verify new attribute fields appear
    let attributeNameInputs = screen.getAllByPlaceholderText(/attribute name/i);
    let attributeValueInputs = screen.getAllByPlaceholderText(/attribute value/i);
    expect(attributeNameInputs.length).toBe(1);
    expect(attributeValueInputs.length).toBe(1);

    // Test editing the new attribute
    fireEvent.change(attributeNameInputs[0], { target: { value: 'Height' } });
    fireEvent.change(attributeValueInputs[0], { target: { value: '6ft' } });
    expect(attributeNameInputs[0].value).toBe('Height');
    expect(attributeValueInputs[0].value).toBe('6ft');

    // Test adding another attribute
    fireEvent.click(addAttributeButton);
    attributeNameInputs = screen.getAllByPlaceholderText(/attribute name/i);
    attributeValueInputs = screen.getAllByPlaceholderText(/attribute value/i);
    expect(attributeNameInputs.length).toBe(2);
    expect(attributeValueInputs.length).toBe(2);

    // Test removing the first attribute
    // Assuming the remove buttons are simply named "Remove" and the first one corresponds to the first attribute
    const removeButtons = screen.getAllByRole('button', { name: /remove/i });
    fireEvent.click(removeButtons[0]); 

    // Verify one attribute remains
    // After removal, re-query for the attribute name inputs
    attributeNameInputs = screen.getAllByPlaceholderText(/attribute name/i);
    expect(attributeNameInputs.length).toBe(1);
    
    // Optionally, verify the remaining attribute is the second one added
    // This assumes the second attribute's values were not changed from their initial (empty) state
    // or if they were, that you check for those specific values.
    // For this example, we'll assume the second attribute's name input is now the first in the list.
    // And its value was not set, so it should be empty or have its original placeholder if any.
    // If the second attribute was (Height: 6ft) and first was removed, this would be:
    // expect(attributeNameInputs[0].value).toBe('Height'); 
    // For now, just checking the count is sufficient as per the example.
  });
});

describe('AddPersonPage Component - Form Submission (Happy Path)', () => {
  beforeEach(() => {
    // Reset mocks for each test to ensure clean state
    api.createPerson.mockResolvedValue({ message: 'Person added successfully!' });
    mockedNavigate.mockClear();

    render(
      <BrowserRouter>
        <AddPersonPage />
      </BrowserRouter>
    );
  });

  afterEach(() => {
    jest.clearAllMocks(); // Clears all mocks (toHaveBeenCalledTimes, etc.)
    // jest.useRealTimers(); // Restore real timers if fake timers were used in a test
  });

  test('should submit with valid data, display success, reset form, and navigate', async () => {
    jest.useFakeTimers(); // Use fake timers for this test

    // Fill form
    fireEvent.change(screen.getByLabelText(/first name/i), { target: { value: 'Test' } });
    fireEvent.change(screen.getByLabelText(/last name/i), { target: { value: 'User' } });
    fireEvent.change(screen.getByLabelText(/date of birth/i), { target: { value: '1990-01-01' } });
    fireEvent.change(screen.getByLabelText(/gender/i), { target: { value: 'Female' } });
    
    // Add custom attribute
    fireEvent.click(screen.getByRole('button', { name: /add attribute/i }));
    fireEvent.change(screen.getAllByPlaceholderText(/attribute name/i)[0], { target: { value: 'Hobby' } });
    fireEvent.change(screen.getAllByPlaceholderText(/attribute value/i)[0], { target: { value: 'Testing' } });

    // Submit form
    fireEvent.click(screen.getByRole('button', { name: /add person/i }));

    // Assert API call
    await waitFor(() => {
      expect(api.createPerson).toHaveBeenCalledTimes(1);
      expect(api.createPerson).toHaveBeenCalledWith(
        expect.objectContaining({
          first_name: 'Test',
          last_name: 'User',
          nickname: '', // Assuming not filled
          birth_date: '1990-01-01',
          place_of_birth: '', // Assuming not filled
          death_date: null, // Assuming not filled, so should be null or empty string based on component logic
          place_of_death: '', // Assuming not filled
          gender: 'Female',
          notes: '', // Assuming not filled
          custom_attributes: {
            'Hobby': 'Testing'
          }
        }),
        'mock-tree-id' // From useAuth mock
      );
    });

    // Assert success message
    expect(await screen.findByText(/person added successfully!/i)).toBeInTheDocument();

    // Assert form reset
    expect(screen.getByLabelText(/first name/i).value).toBe('');
    expect(screen.getByLabelText(/last name/i).value).toBe('');
    expect(screen.getByLabelText(/date of birth/i).value).toBe(''); // Date fields might reset to empty
    expect(screen.getByLabelText(/gender/i).value).toBe(''); // Or default value like 'Select...'
    expect(screen.queryByPlaceholderText(/attribute name/i)).not.toBeInTheDocument();

    // Assert navigation after timeout
    jest.advanceTimersByTime(2000); // As per component's setTimeout
    expect(mockedNavigate).toHaveBeenCalledWith('/dashboard');
    expect(mockedNavigate).toHaveBeenCalledTimes(1);

    jest.useRealTimers(); // Restore real timers after this test
  });
});

describe('AddPersonPage Component - Form Submission Errors', () => {
  beforeEach(() => {
    // Clear mocks and render component for each test in this suite
    mockedNavigate.mockClear();
    // api.createPerson.mockClear(); // Covered by afterEach's clearAllMocks
    
    render(
      <BrowserRouter>
        <AddPersonPage />
      </BrowserRouter>
    );
  });

  afterEach(() => {
    jest.clearAllMocks(); // Ensure mocks are clean after each test
  });

  test('displays error message on API failure and does not navigate or show success', async () => {
    // Specific mock for this test case
    api.createPerson.mockRejectedValue(new Error('Custom API Error'));

    // Fill form (at least required fields)
    fireEvent.change(screen.getByLabelText(/first name/i), { target: { value: 'Error User' } });
    fireEvent.change(screen.getByLabelText(/last name/i), { target: { value: 'Test' } }); // Assuming last name is also required

    // Submit form
    fireEvent.click(screen.getByRole('button', { name: /add person/i }));

    // Assert API call
    await waitFor(() => {
      expect(api.createPerson).toHaveBeenCalledTimes(1);
      expect(api.createPerson).toHaveBeenCalledWith(
        expect.objectContaining({
          first_name: 'Error User',
          last_name: 'Test',
        }),
        'mock-tree-id'
      );
    });

    // Assert error message is displayed
    expect(await screen.findByText(/Custom API Error/i)).toBeInTheDocument();

    // Assert success message is NOT displayed
    expect(screen.queryByText(/person added successfully!/i)).not.toBeInTheDocument();

    // Assert navigation did NOT occur
    expect(mockedNavigate).not.toHaveBeenCalled();

    // Assert form fields are NOT reset (optional, but good to check)
    expect(screen.getByLabelText(/first name/i).value).toBe('Error User');
  });

  test('displays a specific error message if provided by API (err.response.data.error)', async () => {
    const specificApiError = "Specific error from backend";
    api.createPerson.mockRejectedValue({ response: { data: { error: specificApiError } } });
  
    fireEvent.change(screen.getByLabelText(/first name/i), { target: { value: 'API Error User' } });
    fireEvent.click(screen.getByRole('button', { name: /add person/i }));
  
    await waitFor(() => expect(api.createPerson).toHaveBeenCalledTimes(1));
    expect(await screen.findByText(specificApiError)).toBeInTheDocument();
    expect(screen.queryByText(/person added successfully!/i)).not.toBeInTheDocument();
    expect(mockedNavigate).not.toHaveBeenCalled();
  });

  test('displays a specific error message if provided by API (err.response.data.message)', async () => {
    const specificApiMessage = "Specific message from backend";
    api.createPerson.mockRejectedValue({ response: { data: { message: specificApiMessage } } });

    fireEvent.change(screen.getByLabelText(/first name/i), { target: { value: 'API Message User' } });
    fireEvent.click(screen.getByRole('button', { name: /add person/i }));

    await waitFor(() => expect(api.createPerson).toHaveBeenCalledTimes(1));
    expect(await screen.findByText(specificApiMessage)).toBeInTheDocument();
    expect(screen.queryByText(/person added successfully!/i)).not.toBeInTheDocument();
    expect(mockedNavigate).not.toHaveBeenCalled();
  });

  test('displays field-specific validation errors and a general message from API', async () => {
    const validationErrorResponse = {
      response: {
        data: {
          message: "Validation failed on server", // This is the top-level message from the backend
          details: {
            first_name: "First name cannot be empty.",
            birth_date: "Invalid date format."
          }
        }
      }
    };
    api.createPerson.mockRejectedValue(validationErrorResponse);

    // Fill some part of the form, e.g., last name.
    // The actual data doesn't trigger the validation here, the mock does.
    fireEvent.change(screen.getByLabelText(/last name/i), { target: { value: 'UserWithValidationIssues' } });
    // Attempt to submit
    fireEvent.click(screen.getByRole('button', { name: /add person/i }));

    // Wait for API call
    await waitFor(() => {
      expect(api.createPerson).toHaveBeenCalledTimes(1);
    });

    // Assert general error message (the component sets a generic one if details are present)
    // The component's logic is: if (err.response?.data?.details) { setError('Please correct the errors below.'); }
    // else { setError(err.response?.data?.message || ...); }
    // So, we expect "Please correct the errors below." if details are present.
    // However, the top-level error (from err.response.data.message) is also displayed.
    // Let's check for the one from the backend first, then the field specific ones.
    // The component will display err.response.data.message first, and then also populate fieldErrors.
    // The main error state `error` will be "Validation failed on server".
    expect(await screen.findByText(/Validation failed on server/i)).toBeInTheDocument();
    
    // Assert field-specific error messages
    expect(await screen.findByText(/First name cannot be empty./i)).toBeInTheDocument();
    expect(await screen.findByText(/Invalid date format./i)).toBeInTheDocument();

    // Ensure success message isn't shown and no navigation
    expect(screen.queryByText(/person added successfully!/i)).not.toBeInTheDocument();
    expect(mockedNavigate).not.toHaveBeenCalled();
  });
});

// New describe block for context-specific tests
describe('AddPersonPage Component - Context Handling (No Active Tree ID)', () => {
  // Store original AuthContext mock if needed, or ensure reset
  let originalAuthContextMock;

  beforeEach(() => {
    // It's important to reset modules to allow re-mocking for specific tests
    // when the initial mock is a factory function at the top level.
    jest.resetModules(); 
  });

  afterEach(() => {
    // Restore original modules or ensure subsequent tests re-mock as needed.
    // This is to prevent this specific mock from affecting other tests.
    jest.resetModules();
  });

  test('displays message and no form when activeTreeId is null', () => {
    // Override the AuthContext mock specifically for this test
    jest.mock('../context/AuthContext', () => ({
      useAuth: () => ({ activeTreeId: null, user: { username: 'testuser' } }), // Provide a user object if Link needs it
    }));
    
    // Re-require the component to use the new mock
    // Also, re-require react-router-dom if its mock was affected by resetModules,
    // or ensure its mock is also re-established if necessary.
    // For this case, our react-router-dom mock is top-level and should persist,
    // but if it were more complex, it might need re-establishment.
    const AddPersonPageActual = require('./AddPersonPage').default;

    render(
      <BrowserRouter> {/* Needed for the <Link> in the error message */}
        <AddPersonPageActual />
      </BrowserRouter>
    );

    // Check for the specific error message
    const expectedMessage = /please select or create a family tree on the dashboard before adding people/i;
    expect(screen.getByText(expectedMessage)).toBeInTheDocument();
    
    // Check that the "Dashboard" part is a link
    const dashboardLink = screen.getByRole('link', { name: /dashboard/i });
    expect(dashboardLink).toBeInTheDocument();
    expect(dashboardLink).toHaveAttribute('href', '/dashboard');

    // Check that form elements are not rendered
    // Main heading "Add New Person" might still be there, or not, depending on implementation.
    // If the component returns early, the heading might not be rendered.
    // Let's assume the heading is part of the main layout rendered before the check.
    // If it's inside the conditional block, then queryByRole for heading would also be null.
    // For now, let's assume the component structure is:
    // <Heading />
    // if (!activeTreeId) return <ErrorMessage />;
    // return <Form />;
    // So, the heading would be present.

    expect(screen.queryByLabelText(/first name/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/last name/i)).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /add person/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /add attribute/i })).not.toBeInTheDocument();
  });
});

describe('AddPersonPage Component - Loading States', () => {
  beforeEach(() => {
    mockedNavigate.mockClear();
    // api.createPerson.mockClear(); // Handled by afterEach jest.clearAllMocks()
    render(
      <BrowserRouter>
        <AddPersonPage />
      </BrowserRouter>
    );
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  test('shows loading state on submit button and re-enables on success', async () => {
    let resolveApiCall;
    api.createPerson.mockImplementation(() => {
      return new Promise(resolve => {
        // Store the resolve function to be called later
        resolveApiCall = () => resolve({ message: 'Person added successfully!' });
      });
    });

    // Fill required fields
    fireEvent.change(screen.getByLabelText(/first name/i), { target: { value: 'Loading Test' } });
    fireEvent.change(screen.getByLabelText(/last name/i), { target: { value: 'Success' } });

    const submitButton = screen.getByRole('button', { name: /add person/i });
    fireEvent.click(submitButton); // Do not await, want to check immediate state

    // Assert loading state
    expect(submitButton).toBeDisabled();
    expect(submitButton).toHaveTextContent(/adding.../i);

    // Resolve the API call
    if (resolveApiCall) {
      resolveApiCall();
    }

    // Wait for UI to update
    await waitFor(() => {
      expect(submitButton).not.toBeDisabled();
      // The button text might revert to "Add Person" or stay as "Adding..." briefly
      // then change due to success message and form reset.
      // The most reliable check is that it's not disabled and original text or success is shown.
      // If the form resets and success message appears, button text should be "Add Person"
      expect(submitButton).toHaveTextContent(/add person/i); 
    });

    // Verify success message
    expect(await screen.findByText(/person added successfully!/i)).toBeInTheDocument();
    // Implicitly, navigation will also be tested if it's part of the success flow with timers.
  });

  test('shows loading state on submit button and re-enables on failure', async () => {
    let rejectApiCall;
    api.createPerson.mockImplementation(() => {
      return new Promise((resolve, reject) => {
        // Store the reject function
        rejectApiCall = () => reject(new Error('API Call Failed'));
      });
    });

    // Fill required fields
    fireEvent.change(screen.getByLabelText(/first name/i), { target: { value: 'Loading Test' } });
    fireEvent.change(screen.getByLabelText(/last name/i), { target: { value: 'Failure' } });

    const submitButton = screen.getByRole('button', { name: /add person/i });
    fireEvent.click(submitButton); // Do not await

    // Assert loading state
    expect(submitButton).toBeDisabled();
    expect(submitButton).toHaveTextContent(/adding.../i);

    // Reject the API call
    if (rejectApiCall) {
      rejectApiCall();
    }

    // Wait for UI to update
    await waitFor(() => {
      expect(submitButton).not.toBeDisabled();
      expect(submitButton).toHaveTextContent(/add person/i);
    });

    // Verify error message
    expect(await screen.findByText(/API Call Failed/i)).toBeInTheDocument();
    expect(mockedNavigate).not.toHaveBeenCalled();
  });
});
