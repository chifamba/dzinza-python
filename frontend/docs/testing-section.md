## Testing

The application includes a comprehensive test suite that covers:

1. **Unit Tests**: Tests for individual components
2. **Integration Tests**: Tests for component interactions and API calls
3. **Error Handling Tests**: Tests for graceful error handling
4. **RBAC Tests**: Tests for role-based access control (permissions)

### What's Tested

- **Relationship Components**: 
  - Form validation and submission
  - Timeline display with correct formatting
  - Filtering and sorting relationships
  - Error state handling
  - Permission-based UI rendering

- **API Integration**:
  - Successful API interactions
  - Handling and displaying API errors
  - Proper data transformation

- **User Permissions**:
  - Display or hide edit/delete buttons based on permissions
  - Disable form fields for read-only users
  - Permission-based filtering of sensitive information

### Running Tests

```bash
# Run all tests
npm test

# Run tests with watch mode
npm run test:watch

# Run tests with coverage report
npm run test:coverage
```

For more detailed information about the testing strategy, see [Testing Documentation](./docs/testing-documentation.md).
