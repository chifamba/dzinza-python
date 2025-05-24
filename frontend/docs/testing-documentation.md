# Testing Documentation for Family Tree Application

## Overview

This document describes the comprehensive testing approach implemented for the family tree application's frontend, focusing on the relationship management components.

## Test Structure

The testing framework is organized into several categories:

1. **Unit Tests**: Tests for individual components in isolation
2. **Integration Tests**: Tests for how components interact with each other and API endpoints
3. **Error Handling Tests**: Tests that validate proper handling of error scenarios
4. **RBAC Tests**: Tests for role-based access control

## Test Files Organization

- `src/__tests__/`: Basic application tests
- `src/components/*/__tests__/`: Component-specific tests
- `src/contexts/__tests__/`: Tests for context providers (Auth, etc.)
- `src/test-utils/`: Testing utilities and mock data

## Testing Technologies

- **Jest**: Test runner and assertion library
- **React Testing Library**: UI component testing library
- **@testing-library/user-event**: Simulating user interactions
- **axios-mock-adapter**: API mocking for integration tests

## Running Tests

```bash
# Run all tests
npm test

# Run tests with watch mode (auto-rerun on changes)
npm run test:watch

# Run tests with coverage report
npm run test:coverage

# Run specific test file
npm test -- path/to/test.js
```

## Writing Tests

### Unit Tests

Unit tests focus on testing individual components in isolation. Example:

```javascript
import { render, screen } from '@testing-library/react';
import { MockRelationshipForm } from '../mock-components';

test('renders with default values', () => {
  render(
    <MockRelationshipForm 
      onSubmit={jest.fn()} 
      onCancel={jest.fn()} 
    />
  );
  
  expect(screen.getByTestId('relationship-form')).toBeDefined();
  expect(screen.getByText('Relationship Details')).toBeDefined();
});
```

### Integration Tests

Integration tests verify that components work correctly with other components and services:

```javascript
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import axios from 'axios';
import MockAdapter from 'axios-mock-adapter';
import { RelationshipDetailsForm } from '../components/relationship/RelationshipDetailsForm';

test('Successfully creates relationship via API', async () => {
  const mockAxios = new MockAdapter(axios);
  const mockResponse = { id: 'rel-123', type: 'spouse_current' };
  
  mockAxios.onPost('/api/relationships').reply(201, mockResponse);
  
  const onSuccess = jest.fn();
  
  render(
    <RelationshipDetailsForm
      selectablePeople={mockPeople}
      onSubmit={async (data) => {
        const response = await axios.post('/api/relationships', data);
        onSuccess(response.data);
      }}
    />
  );
  
  // Fill form fields...
  
  // Submit form
  await userEvent.click(screen.getByRole('button', { name: /Save/i }));
  
  // Verify API interaction
  await waitFor(() => {
    expect(onSuccess).toHaveBeenCalledWith(mockResponse);
  });
});
```

### Error Scenario Testing

Tests that verify components handle errors gracefully:

```javascript
test('RelationshipDetailsForm handles API errors', async () => {
  const mockAxios = new MockAdapter(axios);
  mockAxios.onPost('/api/relationships').reply(500);
  
  const onError = jest.fn();
  
  render(
    <RelationshipDetailsForm
      selectablePeople={mockPeople}
      onSubmit={async (data) => {
        try {
          await axios.post('/api/relationships', data);
        } catch (error) {
          onError(error);
        }
      }}
    />
  );
  
  // Fill and submit form...
  
  await waitFor(() => {
    expect(onError).toHaveBeenCalled();
    expect(screen.getByText(/Error saving relationship/i)).toBeInTheDocument();
  });
});
```

### RBAC Testing

Tests for role-based access control to ensure proper permission handling:

#### Testing Auth Context

We test the AuthContext provider to ensure it correctly manages user sessions and permissions:

```javascript
test('hasRole correctly identifies user permissions', async () => {
  // Mock session with admin role
  mockAxios.onGet('/api/auth/session').reply(200, {
    authenticated: true,
    user: {
      id: 'admin-123',
      username: 'adminuser',
      role: 'admin'
    }
  });
  
  render(
    <AuthProvider>
      <AuthTestComponent />
    </AuthProvider>
  );
  
  await waitFor(() => {
    expect(screen.getByTestId('admin-role')).toHaveTextContent('true');
  });
});
```

#### Testing RBAC in Components

We test that components correctly respect user roles and permissions:

```javascript
test('admin-only features are hidden from regular users', () => {
  // Mock the useAuth hook to return a regular user
  useAuth.mockReturnValue({
    user: { id: 'user-123', username: 'testuser', role: 'user' },
    hasRole: (role) => role === 'user'
  });
  
  render(<AdminFeatureComponent />);
  
  // Admin panel should not be visible to regular users
  expect(screen.queryByTestId('admin-panel')).not.toBeInTheDocument();
  
  // Regular user features should be visible
  expect(screen.getByTestId('user-features')).toBeInTheDocument();
});
```

## Mock Data

We use predefined mock data for testing, defined in `src/test-utils/mock-data.js`:

- `mockPeople`: Sample person objects
- `mockRelationships`: Sample relationship objects
- `mockRelationshipFormData`: Sample form data for relationship creation/editing

For auth testing, we use `src/test-utils/auth-utils.js` which provides:
- `createMockAuthProvider`: Creates a mocked AuthProvider component
- `mockUsers`: Sample user objects with different roles
- `createAuthProviderWithRole`: Creates AuthProvider with specific user role

## Test Coverage

We aim for high test coverage, especially for critical components like relationship management and authentication. Current coverage goals:

- Statements: >80%
- Branches: >75%
- Functions: >85%
- Lines: >80%

Run `npm run test:coverage` to generate detailed coverage reports.
import { ComponentToTest } from '../ComponentToTest';

describe('ComponentToTest', () => {
  test('renders correctly', () => {
    render(<ComponentToTest />);
    expect(screen.getByText('Expected Text')).toBeDefined();
  });
});
```

### Integration Tests

Integration tests verify that multiple components work together correctly. Example:

```javascript
import { render, screen, fireEvent } from '@testing-library/react';
import { ParentComponent } from '../ParentComponent';

describe('ParentComponent with ChildComponent', () => {
  test('interaction between components works', () => {
    render(<ParentComponent />);
    fireEvent.click(screen.getByText('Trigger Child'));
    expect(screen.getByText('Child Activated')).toBeDefined();
  });
});
```

### RBAC Tests

RBAC tests verify that role-based access control is enforced correctly. Example:

```javascript
import { render, screen } from '@testing-library/react';
import { AuthProvider } from '../AuthProvider';
import { ProtectedComponent } from '../ProtectedComponent';

describe('RBAC Testing', () => {
  test('admin users can see admin controls', () => {
    render(
      <AuthProvider user={{ role: 'admin' }}>
        <ProtectedComponent />
      </AuthProvider>
    );
    expect(screen.getByText('Admin Controls')).toBeDefined();
  });

  test('viewer users cannot see admin controls', () => {
    render(
      <AuthProvider user={{ role: 'viewer' }}>
        <ProtectedComponent />
      </AuthProvider>
    );
    expect(screen.queryByText('Admin Controls')).toBeNull();
  });
});
```

## Best Practices

1. **Test Behavior, Not Implementation**: Focus on testing what the component does, not how it does it.
2. **Use Data-Testid Attributes**: Use `data-testid` for test-specific element selection.
3. **Mock External Dependencies**: Isolate tests by mocking API calls and external services.
4. **Test Edge Cases**: Include tests for error states, loading states, and edge cases.
5. **Keep Tests Independent**: Each test should run independently of others.

## Coverage Goals

- **Components**: 85%+ coverage
- **Utilities**: 90%+ coverage
- **Contexts**: 80%+ coverage
- **Critical Paths**: 100% coverage
