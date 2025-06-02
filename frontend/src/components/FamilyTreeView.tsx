import React, { useEffect, useState, useRef } from 'react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  // rectSortingStrategy, // Or other strategies
} from '@dnd-kit/sortable';
import { Person } from '../types';
import PersonCard from './PersonCard';
import TreeConnector from './TreeConnector';
import { SkipBack, Play, SkipForward, Pause } from 'lucide-react';

interface FamilyTreeViewProps {
  persons: Person[];
  setPersons: React.Dispatch<React.SetStateAction<Person[]>>; // Added to update state
  onAddPerson: (parentId?: string) => void;
  onEditPerson: (personId: string) => void;
  onSelectPerson: (personId: string) => void;
  selectedPersonId: string | null;
}

const FamilyTreeView: React.FC<FamilyTreeViewProps> = ({
  persons,
  setPersons, // Added to update state
  onAddPerson,
  onEditPerson,
  onSelectPerson,
  selectedPersonId,
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [scale, setScale] = useState(1);
  const treeContainerRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  function handleDragEnd(event: DragEndEvent) {
    const {active, over} = event;

    if (over && active.id !== over.id) {
      setPersons((items) => {
        const oldIndex = items.findIndex((item) => item.id === active.id);
        const newIndex = items.findIndex((item) => item.id === over.id);
        return arrayMove(items, oldIndex, newIndex);
      });
    }
  }

  // Group persons by generation level
  const getGenerationLevel = (person: Person, level = 0, visited = new Set<string>()): number => {
    if (visited.has(person.id)) return level;
    visited.add(person.id);
    
    if (!person.parentId) return 0;
    
    const parent = persons.find(p => p.id === person.parentId);
    if (!parent) return level;
    
    return getGenerationLevel(parent, level + 1, visited);
  };

  const generationMap: Record<number, Person[]> = {};
  persons.forEach(person => {
    const level = getGenerationLevel(person);
    if (!generationMap[level]) {
      generationMap[level] = [];
    }
    generationMap[level].push(person);
  });

  const generations = Object.entries(generationMap)
    .sort(([levelA], [levelB]) => Number(levelA) - Number(levelB))
    .map(([level, persons]) => ({ level: Number(level), persons }));

  // Handle zoom
  const handleZoom = (delta: number) => {
    setScale(prevScale => {
      const newScale = prevScale + delta * 0.1;
      return Math.max(0.5, Math.min(2, newScale));
    });
  };

  // Handle drag
  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - position.x, y: e.clientY - position.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      setPosition({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  // Handle auto play
  useEffect(() => {
    if (!isPlaying) return;
    
    const interval = setInterval(() => {
      // Implementation for auto-play animation
      // For example, cycling through family members
      if (selectedPersonId) {
        const currentIndex = persons.findIndex(p => p.id === selectedPersonId);
        const nextIndex = (currentIndex + 1) % persons.length;
        onSelectPerson(persons[nextIndex].id);
      } else if (persons.length > 0) {
        onSelectPerson(persons[0].id);
      }
    }, 3000);
    
    return () => clearInterval(interval);
  }, [isPlaying, selectedPersonId, persons, onSelectPerson]);

  // Handle keyboard controls
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') {
        // Previous person
        if (selectedPersonId) {
          const currentIndex = persons.findIndex(p => p.id === selectedPersonId);
          if (currentIndex > 0) {
            onSelectPerson(persons[currentIndex - 1].id);
          }
        }
      } else if (e.key === 'ArrowRight') {
        // Next person
        if (selectedPersonId) {
          const currentIndex = persons.findIndex(p => p.id === selectedPersonId);
          if (currentIndex < persons.length - 1) {
            onSelectPerson(persons[currentIndex + 1].id);
          }
        } else if (persons.length > 0) {
          onSelectPerson(persons[0].id);
        }
      } else if (e.key === ' ') {
        // Toggle play/pause
        setIsPlaying(prev => !prev);
      } else if (e.key === '+') {
        handleZoom(1);
      } else if (e.key === '-') {
        handleZoom(-1);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedPersonId, persons, onSelectPerson]);

  const renderTreeConnections = () => {
    // This would render SVG connections between family members
    // For simplicity, we'll use simpler div-based connectors
    return null;
  };

  return (
    <div className="relative w-full h-full overflow-hidden"
         onWheel={(e) => handleZoom(e.deltaY > 0 ? -1 : 1)}
         onMouseDown={handleMouseDown}
         onMouseMove={handleMouseMove}
         onMouseUp={handleMouseUp}
         onMouseLeave={handleMouseUp}>
      
      {/* Tree background with decorative elements */}
      <div className="absolute inset-0 pointer-events-none">
        {/* Top left decorative element */}
        <div className="absolute left-10 top-10 opacity-20">
          <div className="w-40 h-40 border border-gray-300 rounded-md transform rotate-12 bg-white"></div>
          <div className="w-40 h-40 border border-gray-300 rounded-md transform -rotate-6 bg-white absolute -top-4 -left-4"></div>
        </div>
        
        {/* Top right decorative element */}
        <div className="absolute right-10 top-10 opacity-20">
          <div className="w-20 h-20 rounded-full border-4 border-amber-300 absolute -top-10 -left-10 transform rotate-12"></div>
          <div className="w-40 h-40 border border-gray-300 rounded-md transform -rotate-6 bg-white"></div>
        </div>
        
        {/* Bottom left decorative element */}
        <div className="absolute left-10 bottom-10 opacity-20">
          <div className="w-60 h-40 border border-gray-300 transform -rotate-6 bg-white"></div>
          <div className="w-10 h-40 border-t border-l border-r border-gray-300 transform rotate-45 absolute top-0 left-20 bg-white"></div>
        </div>
        
        {/* Bottom right decorative element */}
        <div className="absolute right-10 bottom-10 opacity-20">
          <div className="flex flex-col items-center">
            <div className="w-40 h-20 border border-gray-300 bg-white"></div>
            <div className="w-36 h-20 border border-gray-300 bg-white -mt-1"></div>
            <div className="w-32 h-20 border border-gray-300 bg-white -mt-1"></div>
            <div className="w-28 h-20 border border-gray-300 bg-white -mt-1"></div>
            <div className="w-24 h-20 border border-gray-300 bg-white -mt-1"></div>
          </div>
        </div>

        {/* Background yellow spot */}
        <div className="absolute right-1/4 top-1/4 w-40 h-40 rounded-full bg-amber-100 opacity-20 blur-lg"></div>
      </div>
      
      {/* Tree container with transform for zoom and pan */}
      <div 
        ref={treeContainerRef}
        className="absolute"
        style={{
          transform: `translate(${position.x}px, ${position.y}px) scale(${scale})`,
          transformOrigin: 'center',
          transition: isDragging ? 'none' : 'transform 0.3s ease',
        }}
      >
        {renderTreeConnections()}
        
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={handleDragEnd}
        >
          <SortableContext
            items={persons.map(p => p.id)}
            // strategy={rectSortingStrategy} // Consider if needed
          >
            <div className="flex flex-col items-center space-y-12 pt-12">
              {generations.map((generation, genIndex) => (
                <div key={`gen-${genIndex}`} className="flex flex-wrap justify-center gap-10">
                  {generation.persons.map((person) => (
                    <div key={person.id} className="flex flex-col items-center">
                      <PersonCard
                        person={person}
                        onAddChild={() => onAddPerson(person.id)}
                        onEdit={() => onEditPerson(person.id)}
                        onSelect={() => onSelectPerson(person.id)}
                        selected={selectedPersonId === person.id}
                      />

                      {/* Show connector if not the last generation */}
                      {genIndex < generations.length - 1 &&
                        persons.some(p => p.parentId === person.id) && (
                          <TreeConnector type="vertical\" length={30} />
                        )
                      }
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </SortableContext>
        </DndContext>
      </div>
      
      {/* Navigation controls */}
      <div className="absolute left-1/2 bottom-10 transform -translate-x-1/2 flex items-center space-x-4 bg-white bg-opacity-70 p-2 rounded-full shadow-md">
        <button 
          className="p-2 rounded-full hover:bg-gray-200 transition-colors"
          onClick={() => {
            if (selectedPersonId) {
              const currentIndex = persons.findIndex(p => p.id === selectedPersonId);
              if (currentIndex > 0) {
                onSelectPerson(persons[currentIndex - 1].id);
              }
            }
          }}
        >
          <SkipBack size={24} />
        </button>
        
        <button 
          className="p-2 rounded-full hover:bg-gray-200 transition-colors"
          onClick={() => setIsPlaying(!isPlaying)}
        >
          {isPlaying ? <Pause size={24} /> : <Play size={24} />}
        </button>
        
        <button 
          className="p-2 rounded-full hover:bg-gray-200 transition-colors"
          onClick={() => {
            if (selectedPersonId) {
              const currentIndex = persons.findIndex(p => p.id === selectedPersonId);
              if (currentIndex < persons.length - 1) {
                onSelectPerson(persons[currentIndex + 1].id);
              }
            } else if (persons.length > 0) {
              onSelectPerson(persons[0].id);
            }
          }}
        >
          <SkipForward size={24} />
        </button>
      </div>
      
      {/* Zoom controls */}
      <div className="absolute right-10 bottom-10 flex flex-col bg-white bg-opacity-70 p-2 rounded-lg shadow-md">
        <button 
          className="p-1 hover:bg-gray-200 transition-colors"
          onClick={() => handleZoom(1)}
        >
          +
        </button>
        <div className="h-0.5 w-full bg-gray-300 my-1"></div>
        <button 
          className="p-1 hover:bg-gray-200 transition-colors"
          onClick={() => handleZoom(-1)}
        >
          -
        </button>
      </div>
    </div>
  );
};

export default FamilyTreeView;