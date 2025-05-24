// src/components/relationship/__tests__/RelationshipTimeline.basic.test.js
import React from 'react';
import { render } from '@testing-library/react';
import { RelationshipTimeline } from '../RelationshipTimeline';
import { mockPeople, mockRelationships } from '../../../test-utils/mock-data';

describe('RelationshipTimeline Component', () => {
  test('renders without crashing', () => {
    const onEdit = jest.fn();
    const onDelete = jest.fn();

    render(
      <RelationshipTimeline 
        relationships={mockRelationships}
        people={mockPeople}
        onEdit={onEdit}
        onDelete={onDelete}
      />
    );
  });
});
