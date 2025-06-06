import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import CustomPersonNode from './CustomPersonNode';
import type { PersonNodeData } from './CustomPersonNode'; // Type import
import { Position } from 'reactflow'; // Position is a value
import type { NodeProps } from 'reactflow'; // Type import

// Minimal NodeProps required for testing CustomPersonNode
const defaultNodeProps: Omit<NodeProps<PersonNodeData>, 'data'> = {
  id: 'test-node',
  type: 'person',
  selected: false,
  isConnectable: true,
  xPos: 0, // React Flow internal, might not be directly used by custom node display logic
  yPos: 0, // React Flow internal
  zIndex: 0, // React Flow internal
  dragging: false,
  targetPosition: Position.Top,
  sourcePosition: Position.Bottom,
};

describe('CustomPersonNode', () => {
  it('renders person name', () => {
    const data: PersonNodeData = { name: 'John Doe' };
    render(<CustomPersonNode {...defaultNodeProps} data={data} />);
    expect(screen.getByText('John Doe')).toBeInTheDocument();
  });

  it('renders birth and death dates', () => {
    const data: PersonNodeData = { name: 'Jane Doe', birthDate: '1990-01-01', deathDate: '2020-12-31' };
    render(<CustomPersonNode {...defaultNodeProps} data={data} />);
    expect(screen.getByText('B: 1990-01-01 | D: 2020-12-31')).toBeInTheDocument();
  });

  it('renders only birth date if death date is not provided', () => {
    const data: PersonNodeData = { name: 'Jake Doe', birthDate: '2000-05-05' };
    render(<CustomPersonNode {...defaultNodeProps} data={data} />);
    expect(screen.getByText('B: 2000-05-05')).toBeInTheDocument();
    expect(screen.queryByText(/D:/)).not.toBeInTheDocument();
  });

  it('renders photo if photoUrl is provided', () => {
    const data: PersonNodeData = { name: 'Photo Person', photoUrl: 'http://example.com/photo.jpg' };
    render(<CustomPersonNode {...defaultNodeProps} data={data} />);
    const imgElement = screen.getByRole('img', { name: 'Photo Person' });
    expect(imgElement).toBeInTheDocument();
    expect(imgElement).toHaveAttribute('src', 'http://example.com/photo.jpg');
  });

  it('renders placeholder if photoUrl is not provided', () => {
    const data: PersonNodeData = { name: 'No Photo Person' };
    render(<CustomPersonNode {...defaultNodeProps} data={data} />);
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
    // Optionally, find the placeholder div if it has a specific test id or class
  });
});
