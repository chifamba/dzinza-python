// src/components/ui/__tests__/button.test.tsx
import React from 'react';
import { render, screen } from '@testing-library/react';
import { Button } from '@/components/ui/button';

describe('Button Component', () => {
  it('renders correctly with default props', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByRole('button', { name: /Click me/i })).toBeInTheDocument();
  });

  it('renders with variant prop', () => {
    render(<Button variant="outline">Outline Button</Button>);
    const button = screen.getByRole('button', { name: /Outline Button/i });
    expect(button).toBeInTheDocument();
    expect(button).toHaveClass('border');
  });

  it('renders with size prop', () => {
    render(<Button size="sm">Small Button</Button>);
    const button = screen.getByRole('button', { name: /Small Button/i });
    expect(button).toBeInTheDocument();
    expect(button).toHaveClass('px-3');
  });

  it('applies additional className', () => {
    render(<Button className="custom-class">Custom Button</Button>);
    const button = screen.getByRole('button', { name: /Custom Button/i });
    expect(button).toBeInTheDocument();
    expect(button).toHaveClass('custom-class');
  });

  it('forwards a ref', () => {
    const ref = React.createRef<HTMLButtonElement>();
    render(<Button ref={ref}>Ref Button</Button>);
    expect(ref.current).not.toBeNull();
    expect(ref.current?.textContent).toBe('Ref Button');
  });

  it('is disabled when disabled prop is true', () => {
    render(<Button disabled>Disabled Button</Button>);
    const button = screen.getByRole('button', { name: /Disabled Button/i });
    expect(button).toBeDisabled();
  });
});
