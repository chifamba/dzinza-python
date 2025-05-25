// jest.setup.js
import '@testing-library/jest-dom';

// Mock console.error to prevent test output pollution
// This is helpful for tests that intentionally trigger errors
const originalConsoleError = console.error;
console.error = (...args) => {
  if (
    /Warning.*not wrapped in act/i.test(args[0]) ||
    /Warning.*cannot update a component/i.test(args[0])
  ) {
    return;
  }
  originalConsoleError(...args);
};

// Polyfill for PointerEvent.hasPointerCapture
if (global.Element && !global.Element.prototype.hasPointerCapture) {
  global.Element.prototype.hasPointerCapture = function(pointerId) {
    // Mock implementation: always return false or manage a mock state if needed
    return false;
  };
}

// Polyfill for scrollIntoView
if (global.Element && !global.Element.prototype.scrollIntoView) {
  global.Element.prototype.scrollIntoView = jest.fn();
}

// Mock window.confirm for all tests
global.confirm = jest.fn(() => true);

// Suppress console.error for specific known issues if necessary
// Mock date-fns
jest.mock('date-fns', () => ({
  format: jest.fn((date) => '2024-01-01'),
}));

// Mock react-hook-form with a stateful mock for useForm
jest.mock('react-hook-form', () => {
  const actual = jest.requireActual('react-hook-form');
  // Simple in-memory form state for test fields
  function createFormState(defaultValues = {}) {
    let values = { ...defaultValues };
    const listeners = new Set();
    return {
      getValues: (name) => (name ? values[name] : { ...values }),
      setValue: (name, value) => {
        values[name] = value;
        listeners.forEach((cb) => cb());
      },
      watch: (name) => (name ? values[name] : { ...values }),
      subscribe: (cb) => {
        listeners.add(cb);
        return () => listeners.delete(cb);
      },
      reset: (newValues = {}) => {
        values = { ...newValues };
        listeners.forEach((cb) => cb());
      },
      _getAll: () => values,
    };
  }
  function useForm({ defaultValues = {} } = {}) {
    const formState = createFormState(defaultValues);
    return {
      register: jest.fn((name) => ({
        name,
        onChange: (e) => formState.setValue(name, e.target.value),
        onBlur: jest.fn(),
        ref: jest.fn(),
      })),
      handleSubmit: (cb) => (e) => {
        e && e.preventDefault && e.preventDefault();
        return cb(formState.getValues());
      },
      formState: {
        errors: {},
        isSubmitting: false,
      },
      reset: formState.reset,
      control: {
        ...formState,
      },
      setValue: formState.setValue,
      getValues: formState.getValues,
      watch: formState.watch,
    };
  }
  return {
    ...actual,
    useForm,
  };
});
