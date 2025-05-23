import React from 'react';
import { Person } from '@/lib/types';
import PersonCard from '@/components/PersonCard';

export interface FamilyDisplayProps {
  people: Person[];
  peoplePositions: { [personId: string]: { x: number; y: number } };
  onPersonDrag: (personId: string, newPosition: { x: number; y: number }) => void;
  onEditPerson: (person: Person) => void;
  onDeletePerson: (personId: string) => void; // Changed to accept personId
  onAddRelative: (person: Person) => void;
  onAiSuggest: (person: Person) => void;
}

const FamilyDisplay: React.FC<FamilyDisplayProps> = ({
  people,
  peoplePositions,
  onPersonDrag,
  onEditPerson,
  onDeletePerson,
  onAddRelative,
  onAiSuggest,
}) => {
  return (
    <div
      className="relative min-h-screen min-w-full bg-slate-50 dark:bg-slate-900"
      style={{
        width: '2000px', 
        height: '1500px', 
      }}
    >
      {people.map((person) => {
        const position = peoplePositions[person.id] || { x: 0, y: 0 }; 

        return (
          <PersonCard
            key={person.id}
            person={person}
            position={position}
            onDrag={onPersonDrag}
            onEdit={() => onEditPerson(person)}
            onDelete={() => onDeletePerson(person.id)} // Pass person.id
            onAddRelative={() => onAddRelative(person)}
            onAiSuggest={() => onAiSuggest(person)}
          />
        );
      })}
    </div>
  );
};

export default FamilyDisplay;
