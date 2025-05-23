import React, { useState, useEffect, useCallback } from 'react';
import { Person } from '@/lib/types';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { User, Edit, Trash2, Link as LinkIcon, Sparkles, Loader2 } from 'lucide-react'; // Added Loader2

export interface PersonCardProps {
  person: Person;
  position: { x: number; y: number };
  onEdit: () => void;
  onDelete: (personId: string) => void;
  onAddRelative: () => void;
  onAiSuggest: (person: Person) => void;
  isLoadingAiSuggestions?: boolean;
  onDrag: (personId: string, newPosition: { x: number; y: number }) => void;
}

const PersonCard: React.FC<PersonCardProps> = ({
  person,
  position,
  onEdit,
  onDelete,
  onAddRelative,
  onAiSuggest,
  isLoadingAiSuggestions = false,
  onDrag,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [dragStartOffset, setDragStartOffset] = useState({ x: 0, y: 0 });

  const handleMouseDown = (event: React.MouseEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(true);
    setDragStartOffset({
      x: event.clientX - position.x,
      y: event.clientY - position.y,
    });
  };

  const handleMouseMove = useCallback(
    (event: MouseEvent) => {
      if (!isDragging) return;
      const newX = event.clientX - dragStartOffset.x;
      const newY = event.clientY - dragStartOffset.y;
      onDrag(person.id, { x: newX, y: newY });
    },
    [isDragging, dragStartOffset, onDrag, person.id]
  );

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    } else {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    }
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, handleMouseMove, handleMouseUp]);

  return (
    <Card
      className={`shadow-lg w-80 ${isDragging ? 'cursor-grabbing' : 'cursor-grab'} hover:shadow-xl transition-shadow duration-200 ease-in-out`} // Added hover effect
      style={{
        position: 'absolute',
        left: `${position.x}px`,
        top: `${position.y}px`,
      }}
    >
      <CardHeader onMouseDown={handleMouseDown} className="select-none cursor-grab"> {/* Explicitly set cursor-grab on header */}
        <CardTitle>{person.name}</CardTitle>
        {(person.birthDate || person.deathDate) && (
          <CardDescription>
            {person.birthDate ? `Born: ${person.birthDate}` : ''}
            {person.birthDate && person.deathDate ? ' - ' : ''}
            {person.deathDate ? `Died: ${person.deathDate}` : ''}
          </CardDescription>
        )}
      </CardHeader>
      <CardContent>
        <div className="w-24 h-24 bg-muted rounded-full mx-auto mb-4 flex items-center justify-center">
          {person.imageUrl ? (
            <img
              src={person.imageUrl}
              alt={person.name}
              className="w-full h-full rounded-full object-cover"
            />
          ) : (
            <User size={48} className="text-muted-foreground" />
          )}
        </div>
        {person.bio && (
          <p className="text-sm text-muted-foreground mb-4 leading-relaxed">
            {person.bio.length > 100 ? `${person.bio.substring(0, 97)}...` : person.bio}
          </p>
        )}
        <div className="text-xs text-muted-foreground space-y-1">
          <p>Parents: <span className="font-medium text-foreground">Placeholder</span></p>
          <p>Spouse: <span className="font-medium text-foreground">Placeholder</span></p>
          <p>Children: <span className="font-medium text-foreground">Placeholder</span></p>
        </div>
      </CardContent>
      <CardFooter className="flex justify-between space-x-2">
        <Button variant="outline" size="sm" onClick={onEdit} title="Edit">
          <Edit size={16} />
        </Button>
        <Button variant="destructive" size="sm" onClick={() => onDelete(person.id)} title="Delete">
          <Trash2 size={16} />
        </Button>
        <Button variant="outline" size="sm" onClick={onAddRelative} title="Add Relative">
          <LinkIcon size={16} />
        </Button>
        <Button 
          variant="outline" 
          size="sm" 
          onClick={() => onAiSuggest(person)}
          disabled={isLoadingAiSuggestions}
          title="AI Suggest"
        >
          {isLoadingAiSuggestions ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Sparkles size={16} />
          )}
        </Button>
      </CardFooter>
    </Card>
  );
};

export default PersonCard;
