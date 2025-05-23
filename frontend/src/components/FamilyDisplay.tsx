import React from 'react';
import { Person, Relationship } from '@/lib/types'; // Import Relationship
import PersonCard from '@/components/PersonCard';

export interface FamilyDisplayProps {
  people: Person[];
  peoplePositions: { [personId: string]: { x: number; y: number } };
  relationships: Relationship[]; // Add relationships prop
  onPersonDrag: (personId: string, newPosition: { x: number; y: number }) => void;
  onEditPerson: (person: Person) => void;
  onDeletePerson: (personId: string) => void;
  onAddRelative: (person: Person) => void;
  onAiSuggest: (person: Person) => void;
  isLoadingAiSuggestions?: boolean; // Keep this if it was added in a previous step
}

const FamilyDisplay: React.FC<FamilyDisplayProps> = ({
  people,
  peoplePositions,
  relationships, // Destructure relationships
  onPersonDrag,
  onEditPerson,
  onDeletePerson,
  onAddRelative,
  onAiSuggest,
  isLoadingAiSuggestions, // Destructure
}) => {
  const CARD_WIDTH = 320; // w-80 from PersonCard
  const CARD_HEIGHT = 250; // Estimated height of PersonCard, adjust as needed

  // A map for quick lookup of person positions
  const personPositionMap = new Map(Object.entries(peoplePositions));

  return (
    <div
      className="relative min-h-screen min-w-full bg-slate-50 dark:bg-slate-900"
      style={{
        width: '3000px', // Adjusted to match CANVAS_WIDTH from page.tsx for consistency
        height: '1500px', 
      }}
    >
      <svg
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          pointerEvents: 'none', // So it doesn't interfere with card dragging
        }}
      >
        {relationships.map((rel) => {
          const pos1 = personPositionMap.get(rel.person1Id);
          const pos2 = personPositionMap.get(rel.person2Id);

          if (pos1 && pos2) {
            let x1, y1, x2, y2;
            let strokeColor = "gray"; // Default stroke color

            if (rel.type === 'Spouse') {
              strokeColor = "hsl(var(--destructive))"; // Example: use destructive color for spouse lines
              if (pos1.x < pos2.x) { // person1 is to the left of person2
                x1 = pos1.x + CARD_WIDTH;
                y1 = pos1.y + CARD_HEIGHT / 2;
                x2 = pos2.x;
                y2 = pos2.y + CARD_HEIGHT / 2;
              } else { // person1 is to the right of person2 (or same x, connect left-to-right by default)
                x1 = pos1.x;
                y1 = pos1.y + CARD_HEIGHT / 2;
                x2 = pos2.x + CARD_WIDTH;
                y2 = pos2.y + CARD_HEIGHT / 2;
              }
            } else if (rel.type === 'Parent') { // person1 is parent, person2 is child
              strokeColor = "hsl(var(--primary))"; // Example: use primary color
              x1 = pos1.x + CARD_WIDTH / 2; // Bottom-center of parent
              y1 = pos1.y + CARD_HEIGHT;
              x2 = pos2.x + CARD_WIDTH / 2; // Top-center of child
              y2 = pos2.y;
            } else if (rel.type === 'Child') { // person1 is child, person2 is parent
              strokeColor = "hsl(var(--primary))"; // Example: use primary color
              x1 = pos1.x + CARD_WIDTH / 2; // Top-center of child
              y1 = pos1.y;
              x2 = pos2.x + CARD_WIDTH / 2; // Bottom-center of parent
              y2 = pos2.y + CARD_HEIGHT;
            } else { // Fallback to center-to-center for other types
              x1 = pos1.x + CARD_WIDTH / 2;
              y1 = pos1.y + CARD_HEIGHT / 2;
              x2 = pos2.x + CARD_WIDTH / 2;
              y2 = pos2.y + CARD_HEIGHT / 2;
            }

            return (
              <line
                key={rel.id}
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                stroke={strokeColor}
                strokeWidth="2"
              />
            );
          }
          return null; // If one or both persons/positions are not found
        })}
      </svg>

      {people.map((person) => {
        const position = personPositionMap.get(person.id) || { x: 0, y: 0 }; 

        return (
          <PersonCard
            key={person.id}
            person={person}
            position={position}
            onDrag={onPersonDrag}
            onEdit={() => onEditPerson(person)}
            onDelete={() => onDeletePerson(person.id)}
            onAddRelative={() => onAddRelative(person)}
            onAiSuggest={() => onAiSuggest(person)}
            isLoadingAiSuggestions={isLoadingAiSuggestions}
          />
        );
      })}
    </div>
  );
};

export default FamilyDisplay;
