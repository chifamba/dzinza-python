// src/__tests__/setup.test.js
import React from 'react';
import { render, screen } from '@testing-library/react';

// Simple test to verify Jest is working
describe('Test Environment', () => {
  it('should work', () => {
    expect(true).toBe(true);
  });

  it('should render a component', () => {
    render(<div data-testid="test">Test Component</div>);
    const element = screen.getByTestId('test');
    expect(element.textContent).toBe('Test Component');
  });
});
