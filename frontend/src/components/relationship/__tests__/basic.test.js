// src/components/relationship/__tests__/basic.test.js
import React from 'react';
import { render, screen } from '@testing-library/react';

describe('Basic React Testing', () => {
  test('basic test works', () => {
    expect(true).toBe(true);
  });

  test('rendering a simple component works', () => {
    render(<div data-testid="test">Test</div>);
    expect(screen.getByTestId('test').textContent).toBe('Test');
  });
});
