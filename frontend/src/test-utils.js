// Test utility functions for providing context to components during testing
import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';

// Mock user object for auth context
export const mockUser = {
  id: 'user123',
  username: 'testuser',
  email: 'test@example.com',
  role: 'user'
};

// Mock admin user for admin routes testing
export const mockAdminUser = {
  id: 'admin123',
  username: 'adminuser',
  email: 'admin@example.com',
  role: 'admin'
};

/**
 * Custom query functions for more flexible text matching
 * Helps find elements where text might be split across multiple elements
 */
export const customQueries = {
  // Find element containing text, even if it's split across child elements
  findByTextContent: async (text, options = {}) => {
    const normalizedText = text.toLowerCase();
    const allElements = await screen.findAllByText(/./, { ...options });
    
    for (const element of allElements) {
      if (element.textContent.toLowerCase().includes(normalizedText)) {
        return element;
      }
    }
    
    throw new Error(`Unable to find an element with the text content: ${text}`);
  },
  
  // Get element containing text, even if it's split across child elements
  getByTextContent: (container, text, options = {}) => {
    const normalizedText = text.toLowerCase();
    const allElements = screen.getAllByText(/./, { container, ...options });
    
    for (const element of allElements) {
      if (element.textContent.toLowerCase().includes(normalizedText)) {
        return element;
      }
    }
    
    throw new Error(`Unable to find an element with the text content: ${text}`);
  }
};

// Add these custom queries to the render result
export const customRender = (ui, options) => {
  const result = render(ui, options);
  return {
    ...result,
    findByTextContent: async (text, options) => customQueries.findByTextContent(text, options),
    getByTextContent: (text, options) => customQueries.getByTextContent(result.container, text, options),
    queryByTextContent: (text, options) => {
      try {
        return customQueries.getByTextContent(result.container, text, options);
      } catch (error) {
        return null;
      }
    }
  };
};

// Update renderWithProviders to include our custom queries
export function renderWithProviders(ui, {
  route = '/',
  initialEntries = [route],
  ...renderOptions
} = {}) {
  // Wrap in all providers needed for tests
  function Wrapper({ children }) {
    return (
      <MemoryRouter initialEntries={initialEntries}>
        <AuthProvider>
          {children}
        </AuthProvider>
      </MemoryRouter>
    );
  }
  
  return customRender(ui, { wrapper: Wrapper, ...renderOptions });
}
