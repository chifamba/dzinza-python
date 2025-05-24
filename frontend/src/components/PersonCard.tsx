import React, { useState, useEffect, useCallback } from 'react';
import { Person } from '@/lib/types';
import EventTracker from '@/services/EventTracker';
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
  const eventTracker = EventTracker.getInstance();

  const handleEdit = () => {
    eventTracker.trackActivity('person_update', person.id, { 
      name: person.name,
      action: 'edit_start' 
    });
    onEdit();
  };

  const handleDelete = () => {
    eventTracker.trackActivity('person_delete', person.id, { 
      name: person.name 
    });
    onDelete(person.id);
  };

  const handleAddRelative = () => {
    eventTracker.trackActivity('person_update', person.id, { 
      name: person.name,
      action: 'add_relative'
    });
    onAddRelative();
  };

  const handleAiSuggest = () => {
    eventTracker.trackActivity('person_update', person.id, { 
      name: person.name,
      action: 'ai_suggest'
    });
    onAiSuggest(person);
  };

  const handleMouseDown = (event: React.MouseEvent<HTMLDivElement>) => {
    if (event.button !== 0) return; // Only handle left mouse button
    event.preventDefault();
    const rect = event.currentTarget.getBoundingClientRect();
    setIsDragging(true);
    setDragStartOffset({
      x: event.clientX - (rect.left + window.scrollX),
      y: event.clientY - (rect.top + window.scrollY),
    });
  };

  const handleMouseMove = useCallback(
    (event: MouseEvent) => {
      if (!isDragging) return;
      // Calculate new position considering scroll offset
      const newX = event.clientX - dragStartOffset.x + window.scrollX;
      const newY = event.clientY - dragStartOffset.y + window.scrollY;
      onDrag(person.id, { x: newX, y: newY });
    },
    [isDragging, dragStartOffset, onDrag, person.id]
  );

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  useEffect(() => {
    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    } else {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    }
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, handleMouseMove, handleMouseUp]);

  return (
    <Card
      className={`shadow-lg w-80 transition-all duration-200 ease-in-out ${
        isDragging ? 'shadow-2xl cursor-grabbing' : 'cursor-grab shadow-md hover:shadow-xl'
      }`}
      style={{
        position: 'absolute',
        left: `${position.x}px`,
        top: `${position.y}px`,
        transform: isDragging ? 'scale(1.02)' : 'scale(1)',
        zIndex: isDragging ? 1000 : 1,
      }}
    >
      <CardHeader 
        onMouseDown={handleMouseDown} 
        className="select-none cursor-grab active:cursor-grabbing"
      >
        <div className="flex justify-between items-center">
          <CardTitle>{person.name || 'Unknown'}</CardTitle>
          <span className={`w-3 h-3 rounded-full ${
            person.deathDate ? 'bg-gray-400' : 'bg-green-500'
          }`} title={person.deathDate ? 'Deceased' : 'Living'} />
        </div>
        {(person.birthDate || person.deathDate) && (
          <CardDescription>
            {person.birthDate && `Born: ${person.birthDate}`}
            {person.birthDate && person.deathDate && ' - '}
            {person.deathDate && `Died: ${person.deathDate}`}
          </CardDescription>
        )}
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-4 mb-4">
          <div className="w-20 h-20 bg-muted rounded-full flex items-center justify-center overflow-hidden flex-shrink-0">
            {person.imageUrl ? (
              <img
                src={person.imageUrl}
                alt={person.name || 'Profile'}
                className="w-full h-full object-cover"
                onError={(e) => {
                  (e.target as HTMLImageElement).src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"%3E%3Cpath fill="currentColor" d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"%3E%3C/path%3E%3C/svg%3E';
                }}
              />
            ) : (
              <User className="w-10 h-10 text-muted-foreground" />
            )}
          </div>
          <div className="flex-grow space-y-1">
            {person.gender && (
              <p className="text-sm text-muted-foreground">
                Gender: {person.gender}
              </p>
            )}
            {person.birthPlace && (
              <p className="text-sm text-muted-foreground">
                Born in: {person.birthPlace}
              </p>
            )}
            {person.bio && (
              <p className="text-sm text-muted-foreground line-clamp-2">
                {person.bio}
              </p>
            )}
          </div>
        </div>
        <div className="text-sm space-y-1">
          {person.parents && person.parents.length > 0 && (
            <p className="text-muted-foreground">
              {person.parents.length > 1 ? 'Parents' : 'Parent'}: {person.parents.map(p => p.name).join(', ')}
            </p>
          )}
          {person.spouses && person.spouses.length > 0 && (
            <p className="text-muted-foreground">
              {person.spouses.length > 1 ? 'Spouses' : 'Spouse'}: {person.spouses.map(s => s.name).join(', ')}
            </p>
          )}
          {person.children && person.children.length > 0 && (
            <p className="text-muted-foreground">
              {person.children.length > 1 ? 'Children' : 'Child'}: {person.children.map(c => c.name).join(', ')}
            </p>
          )}
        </div>
      </CardContent>
      <CardFooter className="justify-end gap-2">
        <Button variant="outline" size="sm" onClick={handleEdit}>
          <Edit className="h-4 w-4" />
        </Button>
        <Button variant="outline" size="sm" onClick={handleAddRelative}>
          <User className="h-4 w-4" />
        </Button>
        <Button variant="outline" size="sm" onClick={handleAiSuggest} disabled={isLoadingAiSuggestions}>
          {isLoadingAiSuggestions ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Sparkles className="h-4 w-4" />
          )}
        </Button>
        <Button variant="destructive" size="sm" onClick={handleDelete}>
          <Trash2 className="h-4 w-4" />
        </Button>
      </CardFooter>
    </Card>
  );
};

export default PersonCard;
