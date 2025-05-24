// src/components/relationship/__tests__/simple.test.tsx
import React from 'react';
import { render, screen } from '@testing-library/react';

// Simple component for testing
const SimpleComponent = ({title}: {title: string}) => {
  return <div data-testid="simple-component">{title}</div>;
};

describe('Simple TypeScript Component Test', () => {
  it('renders with a title', () => {
    render(<SimpleComponent title="Test Title" />);
    expect(screen.getByTestId('simple-component')).toHaveTextContent('Test Title');
  });
});
