// filepath: /Users/robert/projects/python/dzinza-python/frontend/src/components/FamilyTreeViewExport.tsx
import React, { useState, useRef, useEffect } from 'react';
import { Person, Relationship, RelationshipType } from '../types';
import { getRelationships } from '../api/familyTreeService';

// Export interfaces that FamilyTreeContainer expects
export interface ZoomControlFunctions {
  zoomIn: () => void;
  zoomOut: () => void;
  resetZoom: () => void;
}

export interface LayoutControlFunctions {
  save: () => Promise<void>;
  reset: () => Promise<void>;
}

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
  
  // State for relationships data
  const [relationships, setRelationships] = useState<Relationship[]>([]);
  const [connectionsVisible, setConnectionsVisible] = useState(true);

  // Initialize card positions from localStorage first, then from props.persons, or use default positions (0,0)
  useEffect(() => {
    // Try to load saved positions from localStorage
    const savedPositions = localStorage.getItem('familyTreeCardPositions');
    let initialPositions: Record<string, { x: number, y: number }> = {};
    
    if (savedPositions) {
      try {
        const parsedPositions = JSON.parse(savedPositions);
        initialPositions = parsedPositions;
      } catch (error) {
        console.error('Error parsing saved card positions:', error);
      }
    }
    
    // Only initialize positions for persons that don't already have them in state
    props.persons.forEach(person => {
      if (!initialPositions[person.id]) {
        initialPositions[person.id] = person.position || { x: 0, y: 0 };
      }
    });
    
    // Only update state if we actually have new positions to set
    setCardPositions(prevPositions => {
      const hasChanges = props.persons.some(person => 
        !prevPositions[person.id] || 
        (prevPositions[person.id].x !== initialPositions[person.id].x ||
         prevPositions[person.id].y !== initialPositions[person.id].y)
      );
      
      return hasChanges ? { ...prevPositions, ...initialPositions } : prevPositions;
    });
  }, [props.persons]);

  // Fetch relationships data
  useEffect(() => {
    const fetchRelationships = async () => {
      try {
        // In a real implementation, you would fetch relationships from the API
        // For now, we'll use mock data or assume relationships are passed as props
        const allRelationships = await getRelationships({});
        setRelationships(allRelationships);
      } catch (error) {
        console.error('Error fetching relationships:', error);
        setRelationships([]);
      }
    };

    fetchRelationships();
  }, []);

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
      // Just end the drag - don't update props.persons here
      // We'll update props.persons only when saving positions
      setDraggedPersonId(null);
    }
  };
  
  // Save positions to localStorage
  const savePositions = () => {
    try {
      localStorage.setItem('familyTreeCardPositions', JSON.stringify(cardPositions));
      
      // Also update the persons props to ensure consistency
      props.setPersons(currentPersons => {
        return currentPersons.map(person => ({
          ...person,
          position: cardPositions[person.id] || { x: 0, y: 0 }
        }));
      });
      
      // Show a temporary success message
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (error) {
      console.error('Error saving card positions:', error);
      setSaveError(true);
      setTimeout(() => setSaveError(false), 3000);
    }
  };
  
  // State for save feedback
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError, setSaveError] = useState(false);

  // Connection rendering functions
  const getPersonPosition = (personId: string) => {
    const person = props.persons.find(p => p.id === personId);
    if (!person) return null;
    
    const generationIndex = getGenerationLevel(person);
    const generationPersons = generations.find(g => g.level === generationIndex)?.persons || [];
    const positionInGeneration = generationPersons.findIndex(p => p.id === personId);
    
    const cardPosition = cardPositions[personId] || { x: 0, y: 0 };
    const baseX = positionInGeneration * 320; // 64px gap + 256px card width
    const baseY = generationIndex * 448; // 112px gap + 336px for card + connectors
    
    return {
      x: baseX + cardPosition.x,
      y: baseY + cardPosition.y,
      generationIndex,
      positionInGeneration
    };
  };

  const getSpouseRelationships = () => {
    return relationships.filter(rel => 
      rel.relationshipType === RelationshipType.SPOUSE_CURRENT ||
      rel.relationshipType === RelationshipType.SPOUSE_FORMER ||
      rel.relationshipType === RelationshipType.PARTNER
    );
  };

  const getSiblingRelationships = () => {
    return relationships.filter(rel => 
      rel.relationshipType === RelationshipType.SIBLING_FULL ||
      rel.relationshipType === RelationshipType.SIBLING_HALF ||
      rel.relationshipType === RelationshipType.SIBLING_STEP ||
      rel.relationshipType === RelationshipType.SIBLING_ADOPTIVE
    );
  };

  const getParentChildPairs = () => {
    const pairs: Array<{ parentId: string; childId: string }> = [];
    
    // From legacy parentId field
    props.persons.forEach(person => {
      if (person.parentId) {
        pairs.push({ parentId: person.parentId, childId: person.id });
      }
    });
    
    // From relationships data
    relationships.forEach(rel => {
      if (rel.relationshipType === RelationshipType.BIOLOGICAL_PARENT ||
          rel.relationshipType === RelationshipType.ADOPTIVE_PARENT ||
          rel.relationshipType === RelationshipType.STEP_PARENT ||
          rel.relationshipType === RelationshipType.FOSTER_PARENT ||
          rel.relationshipType === RelationshipType.GUARDIAN) {
        pairs.push({ parentId: rel.person1Id, childId: rel.person2Id });
      } else if (rel.relationshipType === RelationshipType.BIOLOGICAL_CHILD ||
                 rel.relationshipType === RelationshipType.ADOPTIVE_CHILD ||
                 rel.relationshipType === RelationshipType.STEP_CHILD ||
                 rel.relationshipType === RelationshipType.FOSTER_CHILD) {
        pairs.push({ parentId: rel.person2Id, childId: rel.person1Id });
      }
    });
    
    return pairs;
  };

  // Helper function to calculate age from birthDate
  const calculateAge = (birthDate: string | undefined): number => {
    if (!birthDate) return 0;
    
    try {
      const birth = new Date(birthDate);
      const today = new Date();
      let age = today.getFullYear() - birth.getFullYear();
      const monthDiff = today.getMonth() - birth.getMonth();
      
      if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
        age--;
      }
      
      return age;
    } catch {
      return 0;
    }
  };

  // Group persons by age-based generations
  const getAgeGenerationLevel = (person: Person): number => {
    const age = calculateAge(person.birthDate);
    
    // Define age ranges for generations (older people at top = lower generation number)
    if (age >= 80) return 0;      // Greatest generation
    if (age >= 60) return 1;      // Silent generation / early boomers
    if (age >= 40) return 2;      // Generation X / late boomers
    if (age >= 20) return 3;      // Millennials / Generation Y
    if (age >= 0) return 4;       // Generation Z / Alpha
    
    return 4; // Default to youngest generation
  };

  const ageGenerationMap: Record<number, Person[]> = {};
  props.persons.forEach(person => {
    const level = getAgeGenerationLevel(person);
    if (!ageGenerationMap[level]) {
      ageGenerationMap[level] = [];
    }
    ageGenerationMap[level].push(person);
  });

  // Sort persons within each generation by age (oldest first)
  Object.values(ageGenerationMap).forEach(generationPersons => {
    generationPersons.sort((a, b) => {
      const ageA = calculateAge(a.birthDate);
      const ageB = calculateAge(b.birthDate);
      return ageB - ageA; // Descending order (oldest first)
    });
  });

  const generations = Object.entries(ageGenerationMap)
    .sort(([levelA], [levelB]) => Number(levelA) - Number(levelB))
    .map(([level, persons]) => ({ level: Number(level), persons }));

  // Helper function to get generation label based on age level
  const getGenerationLabel = (level: number): string => {
    switch (level) {
      case 0: return "Greatest Generation (80+)";
      case 1: return "Silent Generation (60-79)";
      case 2: return "Baby Boomers/Gen X (40-59)";
      case 3: return "Millennials (20-39)";
      case 4: return "Gen Z/Alpha (0-19)";
      default: return `Generation ${level + 1}`;
    }
  };

  // Updated function for backward compatibility with connection rendering
  const getGenerationLevel = (person: Person): number => {
    return getAgeGenerationLevel(person);
  };

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
  
  // Reset all card positions
  const resetPositions = () => {
    if (window.confirm('Are you sure you want to reset all card positions? This cannot be undone.')) {
      const defaultPositions: Record<string, { x: number, y: number }> = {};
      props.persons.forEach(person => {
        defaultPositions[person.id] = { x: 0, y: 0 };
      });
      
      // Update state
      setCardPositions(defaultPositions);
      
      // Update persons
      props.setPersons(currentPersons => {
        return currentPersons.map(person => ({
          ...person,
          position: { x: 0, y: 0 }
        }));
      });
      
      // Clear localStorage
      localStorage.removeItem('familyTreeCardPositions');
    }
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

  // Render marriage connection lines
  const renderMarriageConnections = () => {
    if (!connectionsVisible) return null;
    
    const spouseRelationships = getSpouseRelationships();
    
    return spouseRelationships.map(relationship => {
      const person1Pos = getPersonPosition(relationship.person1Id);
      const person2Pos = getPersonPosition(relationship.person2Id);
      
      if (!person1Pos || !person2Pos || person1Pos.generationIndex !== person2Pos.generationIndex) {
        return null;
      }
      
      // Calculate positions for marriage line above the cards
      const leftX = Math.min(person1Pos.x, person2Pos.x) + 128; // Center of left card
      const rightX = Math.max(person1Pos.x, person2Pos.x) + 128; // Center of right card
      const y = person1Pos.y - 20; // Above the cards
      
      return (
        <g key={`marriage-${relationship.id}`}>
          {/* Horizontal marriage line */}
          <line
            x1={leftX}
            y1={y}
            x2={rightX}
            y2={y}
            stroke="#e74c3c"
            strokeWidth="3"
            className="marriage-line"
          />
          {/* Marriage indicator circles */}
          <circle cx={leftX} cy={y} r="4" fill="#e74c3c" />
          <circle cx={rightX} cy={y} r="4" fill="#e74c3c" />
          {/* Marriage symbol in the middle */}
          <circle 
            cx={(leftX + rightX) / 2} 
            cy={y} 
            r="6" 
            fill="white" 
            stroke="#e74c3c" 
            strokeWidth="2"
          />
          <text
            x={(leftX + rightX) / 2}
            y={y + 2}
            textAnchor="middle"
            fontSize="8"
            fill="#e74c3c"
            fontWeight="bold"
          >
            ♥
          </text>
        </g>
      );
    });
  };

  // Render sibling connection lines
  const renderSiblingConnections = () => {
    if (!connectionsVisible) return null;
    
    const siblingRelationships = getSiblingRelationships();
    
    return siblingRelationships.map(relationship => {
      const person1Pos = getPersonPosition(relationship.person1Id);
      const person2Pos = getPersonPosition(relationship.person2Id);
      
      if (!person1Pos || !person2Pos || person1Pos.generationIndex !== person2Pos.generationIndex) {
        return null;
      }
      
      // Calculate positions for sibling line below the cards
      const leftX = Math.min(person1Pos.x, person2Pos.x) + 128; // Center of left card
      const rightX = Math.max(person1Pos.x, person2Pos.x) + 128; // Center of right card
      const y = person1Pos.y + 160; // Below the cards
      
      return (
        <g key={`sibling-${relationship.id}`}>
          {/* Horizontal sibling line */}
          <line
            x1={leftX}
            y1={y}
            x2={rightX}
            y2={y}
            stroke="#3498db"
            strokeWidth="2"
            strokeDasharray="5,5"
            className="sibling-line"
          />
          {/* Sibling indicator circles */}
          <circle cx={leftX} cy={y} r="3" fill="#3498db" />
          <circle cx={rightX} cy={y} r="3" fill="#3498db" />
        </g>
      );
    });
  };

  // Render parent-child connection lines
  const renderParentChildConnections = () => {
    if (!connectionsVisible) return null;
    
    const parentChildPairs = getParentChildPairs();
    
    return parentChildPairs.map((pair, index) => {
      const parentPos = getPersonPosition(pair.parentId);
      const childPos = getPersonPosition(pair.childId);
      
      if (!parentPos || !childPos) return null;
      
      // Calculate connection points
      const parentX = parentPos.x + 128; // Center of parent card
      const parentY = parentPos.y + 160; // Bottom of parent card
      const childX = childPos.x + 128; // Center of child card
      const childY = childPos.y; // Top of child card
      
      // Calculate middle point for the connector
      const midY = parentY + (childY - parentY) / 2;
      
      return (
        <g key={`parent-child-${index}`}>
          {/* Vertical line from parent */}
          <line
            x1={parentX}
            y1={parentY}
            x2={parentX}
            y2={midY}
            stroke="#2ecc71"
            strokeWidth="2"
            className="parent-child-line"
          />
          {/* Horizontal line */}
          <line
            x1={parentX}
            y1={midY}
            x2={childX}
            y2={midY}
            stroke="#2ecc71"
            strokeWidth="2"
            className="parent-child-line"
          />
          {/* Vertical line to child */}
          <line
            x1={childX}
            y1={midY}
            x2={childX}
            y2={childY}
            stroke="#2ecc71"
            strokeWidth="2"
            className="parent-child-line"
          />
          {/* Connection indicators */}
          <circle cx={parentX} cy={parentY} r="3" fill="#2ecc71" />
          <circle cx={childX} cy={childY} r="3" fill="#2ecc71" />
          <circle cx={childX} cy={midY} r="2" fill="#2ecc71" />
        </g>
      );
    });
  };

  return (
    <div 
      className="family-tree-view w-full h-full overflow-hidden relative bg-gradient-to-br from-gray-50 to-gray-100"
      style={{ 
        minHeight: "600px",
        "--tw-animate-duration": "3s" // for fade-out animation
      } as React.CSSProperties}
    >
      {/* Zoom and position controls in the top left */}
      <div className="absolute top-4 left-4 z-10 bg-white rounded-lg shadow-md p-3 flex flex-col gap-3">
        {/* Zoom controls */}
        <div className="flex flex-col">
          <div className="text-xs text-gray-600 mb-1 font-medium">Zoom</div>
          <div className="flex gap-1 mb-2">
            <button 
              className="px-2 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
              onClick={() => handleZoom(0.1)}
              title="Zoom in"
            >
              <span className="text-lg">+</span>
            </button>
            <button 
              className="px-2 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
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
        </div>
        
        {/* Positions controls */}
        <div className="flex flex-col border-t pt-3">
          <div className="text-xs text-gray-600 mb-1 font-medium">Card Positions</div>
          <button 
            className="mb-1 px-3 py-2 bg-green-600 text-white rounded hover:bg-green-700 transition-colors flex items-center"
            onClick={savePositions}
            title="Save card positions"
          >
            <span className="mr-1">💾</span> Save Positions
          </button>
          <button 
            className="px-3 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors flex items-center"
            onClick={resetPositions}
            title="Reset all card positions"
          >
            <span className="mr-1">↺</span> Reset Positions
          </button>
          {saveSuccess && (
            <div className="mt-2 px-3 py-2 bg-green-100 text-green-800 rounded text-sm animate-fade-out">
              Positions saved successfully!
            </div>
          )}
          {saveError && (
            <div className="mt-2 px-3 py-2 bg-red-100 text-red-800 rounded text-sm animate-fade-out">
              Error saving positions!
            </div>
          )}
        </div>

        {/* Connection controls */}
        <div className="flex flex-col border-t pt-3">
          <div className="text-xs text-gray-600 mb-1 font-medium">Connections</div>
          <button 
            className={`px-3 py-2 rounded transition-colors flex items-center ${
              connectionsVisible 
                ? 'bg-blue-600 text-white hover:bg-blue-700' 
                : 'bg-gray-200 text-gray-800 hover:bg-gray-300'
            }`}
            onClick={() => setConnectionsVisible(!connectionsVisible)}
            title="Toggle family connections"
          >
            <span className="mr-1">{connectionsVisible ? '🔗' : '📎'}</span> 
            {connectionsVisible ? 'Hide' : 'Show'} Connections
          </button>
        </div>
      </div>

      {/* Information panel */}
      <div className="absolute bottom-4 left-4 z-10 bg-white bg-opacity-80 rounded-lg shadow-md p-2 text-xs text-gray-500">
        <p>Click and drag to pan</p>
        <p>Use + and - buttons to zoom</p>
        <p>Drag individual cards to reposition them</p>
        <p>Click "Save Positions" to persist card positions</p>
        <p>Toggle connections to show/hide family relationships</p>
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
          {/* SVG overlay for connection lines */}
          <svg 
            className="absolute top-0 left-0 pointer-events-none z-0"
            style={{
              width: '100%',
              height: '100%',
              minWidth: '2000px',
              minHeight: '2000px'
            }}
          >
            {renderMarriageConnections()}
            {renderSiblingConnections()}
            {renderParentChildConnections()}
          </svg>

          {/* Render the family tree by generations */}
          <div className="generations-container flex flex-col items-center space-y-28 relative z-10">
            {generations.map((generation) => (
              <div 
                key={`gen-${generation.level}`} 
                className="generation-row flex justify-center gap-16 relative"
              >
                {/* Age-based generation label */}
                <div className="absolute -top-8 left-0 text-xs text-gray-400 font-medium">
                  {getGenerationLabel(generation.level)}
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
                              <p className="mb-1">
                                Birth: {person.birthDate}
                                {person.isLiving && (
                                  <span className="ml-2 text-blue-600 font-medium">
                                    (Age {calculateAge(person.birthDate)})
                                  </span>
                                )}
                              </p>
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
