import React, { useState, useRef, useEffect } from 'react';
import { Person } from '../types';

// Create a new component that wraps the functionality needed by FamilyTreeContainer
interface FamilyTreeViewProps {
  persons: Person[];
  setPersons: React.Dispatch<React.SetStateAction<Person[]>>;
  onAddPerson: (parentId?: string) => void;
  onEditPerson: (personId: string) => void;
  onSelectPerson: (personId: string) => void;
  selectedPersonId: string | null;
}

const FamilyTreeView: React.FC<FamilyTreeViewProps> = (props) => {
  const [scale, setScale] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const treeContainerRef = useRef<HTMLDivElement>(null);
  
  // For individual card dragging
  const [draggedPersonId, setDraggedPersonId] = useState<string | null>(null);
  const [cardDragStart, setCardDragStart] = useState({ x: 0, y: 0 });
  const [cardPositions, setCardPositions] = useState<Record<string, { x: number, y: number }>>({});

  // Initialize card positions from props.persons or use default positions
  useEffect(() => {
    const initialPositions: Record<string, { x: number, y: number }> = {};
    props.persons.forEach(person => {
      // Use existing position data if available, otherwise use default position (0,0)
      initialPositions[person.id] = person.position || { x: 0, y: 0 };
    });
    setCardPositions(initialPositions);
  }, [props.persons]);

  // Handle individual card drag
  const handleCardDragStart = (e: React.MouseEvent, personId: string) => {
    e.stopPropagation(); // Prevent tree panning when dragging a card
    setDraggedPersonId(personId);
    
    const currentPosition = cardPositions[personId] || { x: 0, y: 0 };
    setCardDragStart({
      x: e.clientX - currentPosition.x,
      y: e.clientY - currentPosition.y
    });
  };

  const handleCardDrag = (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent tree panning when dragging a card
    
    if (draggedPersonId) {
      const newPositions = { ...cardPositions };
      newPositions[draggedPersonId] = {
        x: e.clientX - cardDragStart.x,
        y: e.clientY - cardDragStart.y
      };
      setCardPositions(newPositions);
    }
  };

  const handleCardDragEnd = (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent tree panning when dragging a card
    
    if (draggedPersonId) {
      // Update the person's position in the state
      props.setPersons(currentPersons => {
        return currentPersons.map(person => {
          if (person.id === draggedPersonId) {
            return {
              ...person,
              position: cardPositions[draggedPersonId]
            };
          }
          return person;
        });
      });
      
      setDraggedPersonId(null);
    }
  };

  // Group persons by generation (parent-child relationships)
  const getGenerationLevel = (person: Person, level = 0, visited = new Set<string>()): number => {
    if (visited.has(person.id)) return level;
    visited.add(person.id);
    
    if (!person.parentId) return 0;
    
    const parent = props.persons.find(p => p.id === person.parentId);
    if (!parent) return level;
    
    return getGenerationLevel(parent, level + 1, visited);
  };

  const generationMap: Record<number, Person[]> = {};
  props.persons.forEach(person => {
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
      const newScale = prevScale + delta;
      return Math.max(0.5, Math.min(2, newScale));
    });
  };

  // Handle drag for panning
  const handleDragStart = (e: React.MouseEvent) => {
    if (draggedPersonId === null) {
      setIsDragging(true);
      setDragStart({ x: e.clientX - position.x, y: e.clientY - position.y });
    }
  };

  const handleDragMove = (e: React.MouseEvent) => {
    if (isDragging && draggedPersonId === null) {
      setPosition({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
    }
  };

  const handleDragEnd = () => {
    setIsDragging(false);
  };

  // Reset zoom
  const resetZoom = () => {
    setScale(1);
    setPosition({ x: 0, y: 0 });
  };

  useEffect(() => {
    const handleMouseUp = () => {
      setIsDragging(false);
    };

    const handleMouseMove = (e: MouseEvent) => {
      if (isDragging && draggedPersonId === null) {
        setPosition({
          x: e.clientX - dragStart.x,
          y: e.clientY - dragStart.y,
        });
      }
    };

    window.addEventListener('mouseup', handleMouseUp);
    window.addEventListener('mousemove', handleMouseMove);

    return () => {
      window.removeEventListener('mouseup', handleMouseUp);
      window.removeEventListener('mousemove', handleMouseMove);
    };
  }, [isDragging, dragStart, draggedPersonId]);

  return (
    <div 
      className="family-tree-view w-full h-full overflow-hidden relative bg-gradient-to-br from-gray-50 to-gray-100"
      style={{ minHeight: "600px" }}
    >
      {/* Zoom controls */}
      <div className="absolute top-4 right-4 z-10 bg-white rounded-lg shadow-md p-2 flex flex-col">
        <button 
          className="mb-1 px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
          onClick={() => handleZoom(0.1)}
          title="Zoom in"
        >
          <span className="text-lg">+</span>
        </button>
        <button 
          className="mb-1 px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
          onClick={() => handleZoom(-0.1)}
          title="Zoom out"
        >
          <span className="text-lg">−</span>
        </button>
        <button 
          className="px-2 py-1 bg-gray-200 text-gray-800 rounded hover:bg-gray-300 transition-colors text-xs"
          onClick={resetZoom}
          title="Reset view"
        >
          Reset
        </button>
      </div>

      {/* Information panel */}
      <div className="absolute bottom-4 left-4 z-10 bg-white bg-opacity-80 rounded-lg shadow-md p-2 text-xs text-gray-500">
        <p>Click and drag to pan</p>
        <p>Use + and - buttons to zoom</p>
        <p>Drag individual cards to reposition them</p>
      </div>

      {/* Tree container with pan & zoom */}
      <div 
        ref={treeContainerRef}
        className="tree-container h-full w-full"
        onMouseDown={handleDragStart}
        onMouseMove={handleDragMove}
        onMouseUp={handleDragEnd}
        onMouseLeave={handleDragEnd}
        style={{ cursor: isDragging ? 'grabbing' : 'grab' }}
      >
        <div 
          className="tree-content absolute"
          style={{
            transform: `translate(${position.x}px, ${position.y}px) scale(${scale})`,
            transformOrigin: 'center',
            transition: isDragging ? 'none' : 'transform 0.2s ease',
            width: 'max-content',
            padding: '60px'
          }}
        >
          {/* Render the family tree by generations */}
          <div className="generations-container flex flex-col items-center space-y-28">
            {generations.map((generation, genIndex) => (
              <div 
                key={`gen-${generation.level}`} 
                className="generation-row flex justify-center gap-16 relative"
              >
                {/* Optional generation label */}
                <div className="absolute -top-8 left-0 text-xs text-gray-400 font-medium">
                  Generation {generation.level + 1}
                </div>
                
                {generation.persons.map((person) => {
                  const personPosition = cardPositions[person.id] || { x: 0, y: 0 };
                  
                  return (
                    <div 
                      key={person.id} 
                      className="person-container flex flex-col items-center"
                      style={{ 
                        position: 'relative',
                        transform: `translate(${personPosition.x}px, ${personPosition.y}px)`,
                        transition: draggedPersonId === person.id ? 'none' : 'transform 0.2s ease',
                        zIndex: draggedPersonId === person.id ? 10 : 1
                      }}
                    >
                      {/* Person Card */}
                      <div 
                        className={`
                          person-card p-4 rounded-lg shadow-md bg-white border-2
                          ${props.selectedPersonId === person.id 
                            ? 'border-blue-500 shadow-lg' 
                            : 'border-gray-200'}
                          ${draggedPersonId === person.id ? 'shadow-xl border-dashed' : ''}
                          transition-all duration-200 hover:shadow-lg
                          w-64 h-40 flex flex-col relative overflow-hidden
                          cursor-move
                        `}
                        onClick={() => {
                          // Only select if not dragging
                          if (draggedPersonId === null) {
                            props.onSelectPerson(person.id);
                          }
                        }}
                        onMouseDown={(e) => handleCardDragStart(e, person.id)}
                        onMouseMove={handleCardDrag}
                        onMouseUp={handleCardDragEnd}
                        onMouseLeave={handleCardDragEnd}
                        style={{
                          backgroundImage: person.hasImage 
                            ? `linear-gradient(rgba(255, 255, 255, 0.9), rgba(255, 255, 255, 0.9)), url('/images/person-${person.id}.jpg')`
                            : 'none',
                          backgroundSize: 'cover',
                          backgroundPosition: 'center'
                        }}
                      >
                        {/* Decorative elements */}
                        <div 
                          className={`absolute top-0 left-0 w-1 h-full ${
                            person.gender === 'male' ? 'bg-blue-500' :
                            person.gender === 'female' ? 'bg-pink-500' : 'bg-gray-400'
                          }`}
                        ></div>
                        
                        <div className="ml-2 flex-grow">
                          <div className="flex justify-between items-start mb-2">
                            <h3 className="text-lg font-bold text-gray-800 truncate">
                              {person.firstName || ''} {person.lastName || ''}
                              {person.name && !person.firstName && !person.lastName && person.name}
                            </h3>
                            <div 
                              className={`w-3 h-3 rounded-full ${
                                person.gender === 'male' ? 'bg-blue-500' :
                                person.gender === 'female' ? 'bg-pink-500' : 'bg-gray-400'
                              }`}
                            />
                          </div>
                          
                          <div className="text-sm text-gray-600 flex-grow">
                            {person.birthDate && (
                              <p className="mb-1">Birth: {person.birthDate}</p>
                            )}
                            {person.birthPlace && (
                              <p className="truncate mb-1">Place: {person.birthPlace}</p>
                            )}
                            {!person.isLiving && person.deathDate && (
                              <p className="mb-1">Death: {person.deathDate}</p>
                            )}
                            {person.nickname && (
                              <p className="mb-1 italic">"{person.nickname}"</p>
                            )}
                          </div>
                        </div>
                        
                        <div className="actions flex justify-end gap-2 mt-2">
                          <button 
                            className="px-2 py-1 bg-gray-200 rounded text-xs hover:bg-gray-300 transition-colors"
                            onClick={(e) => {
                              e.stopPropagation();
                              props.onEditPerson(person.id);
                            }}
                          >
                            Edit
                          </button>
                          <button 
                            className="px-2 py-1 bg-blue-100 rounded text-xs hover:bg-blue-200 transition-colors"
                            onClick={(e) => {
                              e.stopPropagation();
                              props.onAddPerson(person.id);
                            }}
                          >
                            Add Child
                          </button>
                        </div>
                      </div>
                      
                      {/* Connection line to children */}
                      {genIndex < generations.length - 1 && 
                        props.persons.some(p => p.parentId === person.id) && (
                        <div className="connector-container flex flex-col items-center">
                          <div className="connector-line w-0.5 h-10 bg-gray-300 mt-2"></div>
                          <div className="connector-dot w-2 h-2 rounded-full bg-gray-300"></div>
                          <div className="connector-line w-0.5 h-16 bg-gray-300"></div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
          
          {/* Add Person button at the top level */}
          <div className="add-root-person-button absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-10">
            <button 
              className="px-4 py-2 bg-green-600 text-white rounded-full shadow-lg hover:bg-green-700 transition-colors flex items-center"
              onClick={() => props.onAddPerson(undefined)}
            >
              <span className="mr-1 font-bold">+</span> Add Root Person
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FamilyTreeView;
