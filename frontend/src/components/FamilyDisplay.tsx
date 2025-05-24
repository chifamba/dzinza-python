import React, { useState, useCallback, useRef } from 'react';
import { Person, Relationship, RelationshipType } from '@/lib/types';
import EventTracker from '@/services/EventTracker';
import PersonCard from '@/components/PersonCard';
import { Button } from '@/components/ui/button';
import { ZoomIn, ZoomOut, Move } from 'lucide-react';

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
  relationships,
  onPersonDrag,
  onEditPerson,
  onDeletePerson,
  onAddRelative,
  onAiSuggest,
  isLoadingAiSuggestions,
}) => {
  const CARD_WIDTH = 320;
  const CARD_HEIGHT = 250;
  const containerRef = useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });
  const eventTracker = EventTracker.getInstance();

  const handleZoomIn = () => {
    setZoom(prev => {
      const newZoom = Math.min(prev + 0.1, 2);
      eventTracker.trackActivity('tree_update', 'view', { 
        action: 'zoom',
        from: prev,
        to: newZoom
      });
      return newZoom;
    });
  };

  const handleZoomOut = () => {
    setZoom(prev => {
      const newZoom = Math.max(prev - 0.1, 0.5);
      eventTracker.trackActivity('tree_update', 'view', { 
        action: 'zoom',
        from: prev,
        to: newZoom
      });
      return newZoom;
    });
  };

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button === 1 || e.button === 2) {
      e.preventDefault();
      setIsPanning(true);
      setPanStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
      eventTracker.trackActivity('tree_update', 'view', { 
        action: 'pan_start',
        position: { x: e.clientX, y: e.clientY }
      });
    }
  }, [pan]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (isPanning) {
      const newPan = {
        x: e.clientX - panStart.x,
        y: e.clientY - panStart.y
      };
      setPan(newPan);
      // Only track significant pan movements to avoid flooding
      if (Math.abs(newPan.x - pan.x) > 50 || Math.abs(newPan.y - pan.y) > 50) {
        eventTracker.trackActivity('tree_update', 'view', { 
          action: 'pan_update',
          position: newPan
        });
      }
    }
  }, [isPanning, panStart, pan]);

  const handleMouseUp = useCallback(() => {
    if (isPanning) {
      setIsPanning(false);
      eventTracker.trackActivity('tree_update', 'view', { 
        action: 'pan_end',
        final_position: pan
      });
    }
  }, [isPanning, pan]);

  const handlePersonDrag = (personId: string, newPosition: { x: number; y: number }) => {
    eventTracker.trackActivity('person_update', personId, {
      action: 'move',
      position: newPosition
    });
    onPersonDrag(personId, newPosition);
  };

  // A map for quick lookup of person positions
  const personPositionMap = new Map(Object.entries(peoplePositions));

  const handleZoomIn = () => {
    setZoom(prev => {
      const newZoom = Math.min(prev + 0.1, 2);
      eventTracker.trackActivity('tree_update', 'view', { 
        action: 'zoom',
        from: prev,
        to: newZoom
      });
      return newZoom;
    });
  };

  const handleZoomOut = () => {
    setZoom(prev => {
      const newZoom = Math.max(prev - 0.1, 0.5);
      eventTracker.trackActivity('tree_update', 'view', { 
        action: 'zoom',
        from: prev,
        to: newZoom
      });
      return newZoom;
    });
  };

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button === 1 || e.button === 2) { // Middle or right mouse button
      e.preventDefault();
      setIsPanning(true);
      setPanStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
      eventTracker.trackActivity('tree_update', 'view', { 
        action: 'pan_start',
        position: { x: e.clientX, y: e.clientY }
      });
    }
  }, [pan, eventTracker]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (isPanning) {
      const newPan = {
        x: e.clientX - panStart.x,
        y: e.clientY - panStart.y
      };
      setPan(newPan);
      // Only track significant pan movements to avoid flooding
      if (Math.abs(newPan.x - pan.x) > 50 || Math.abs(newPan.y - pan.y) > 50) {
        eventTracker.trackActivity('tree_update', 'view', { 
          action: 'pan_update',
          position: newPan
        });
      }
    }
  }, [isPanning, panStart, pan, eventTracker]);

  const handleMouseUp = useCallback(() => {
    if (isPanning) {
      setIsPanning(false);
      eventTracker.trackActivity('tree_update', 'view', { 
        action: 'pan_end',
        final_position: pan
      });
    }
  }, [isPanning, pan, eventTracker]);

  // Calculate relationship line styles based on type
  const getRelationshipLineStyle = (type: RelationshipType) => {
    if (type.includes('parent') || type.includes('child')) {
      return {
        stroke: type.startsWith('biological') 
          ? "hsl(var(--primary))" 
          : type.startsWith('adoptive')
          ? "hsl(var(--primary)/0.8)"
          : "hsl(var(--primary)/0.6)",
        strokeWidth: 2,
        strokeDasharray: type.startsWith('biological') ? "none" : "5,5"
      };
    } else if (type.includes('spouse') || type === 'partner') {
      return {
        stroke: type === 'spouse_current'
          ? "hsl(var(--destructive))"
          : "hsl(var(--destructive)/0.6)",
        strokeWidth: 2,
        strokeDasharray: type === 'spouse_current' ? "none" : "5,5"
      };
    } else if (type.includes('sibling')) {
      return {
        stroke: type === 'sibling_full'
          ? "hsl(var(--secondary))"
          : "hsl(var(--secondary)/0.6)",
        strokeWidth: 1.5,
        strokeDasharray: type === 'sibling_full' ? "none" : "3,3"
      };
    } else {
      return {
        stroke: "gray",
        strokeWidth: 1,
        strokeDasharray: "2,2"
      };
    }
  };

  return (
    <div
      ref={containerRef}
      className="relative min-h-screen min-w-full bg-slate-50 dark:bg-slate-900 overflow-hidden"
      style={{ 
        width: '3000px',
        height: '1500px',
        cursor: isPanning ? 'grabbing' : 'default'
      }}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onContextMenu={(e) => e.preventDefault()}
    >
      <div className="fixed top-4 right-4 flex gap-2 z-50">
        <Button variant="outline" onClick={handleZoomOut} title="Zoom Out">
          <ZoomOut className="h-4 w-4" />
        </Button>
        <Button variant="outline" onClick={handleZoomIn} title="Zoom In">
          <ZoomIn className="h-4 w-4" />
        </Button>
      </div>

      <div
        style={{
          transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
          transformOrigin: '0 0',
          transition: isPanning ? 'none' : 'transform 0.1s ease-out'
        }}
      >
        <svg
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            pointerEvents: 'none',
            overflow: 'visible'
          }}
        >
          {relationships.map((rel) => {
            const pos1 = personPositionMap.get(rel.person1Id);
            const pos2 = personPositionMap.get(rel.person2Id);

            if (pos1 && pos2) {
              let x1, y1, x2, y2;
              const style = getRelationshipLineStyle(rel.type);

              // Calculate connection points based on relationship type
              if (rel.type.includes('spouse') || rel.type === 'partner') {
                x1 = pos1.x + CARD_WIDTH;
                y1 = pos1.y + CARD_HEIGHT / 2;
                x2 = pos2.x;
                y2 = pos2.y + CARD_HEIGHT / 2;
              } else if (rel.type.includes('parent')) {
                x1 = pos1.x + CARD_WIDTH / 2;
                y1 = pos1.y + CARD_HEIGHT;
                x2 = pos2.x + CARD_WIDTH / 2;
                y2 = pos2.y;
              } else if (rel.type.includes('child')) {
                x1 = pos1.x + CARD_WIDTH / 2;
                y1 = pos1.y;
                x2 = pos2.x + CARD_WIDTH / 2;
                y2 = pos2.y + CARD_HEIGHT;
              } else if (rel.type.includes('sibling')) {
                const isLeftToRight = pos1.x < pos2.x;
                if (isLeftToRight) {
                  x1 = pos1.x + CARD_WIDTH;
                  y1 = pos1.y + CARD_HEIGHT / 3;
                  x2 = pos2.x;
                  y2 = pos2.y + CARD_HEIGHT / 3;
                } else {
                  x1 = pos1.x;
                  y1 = pos1.y + CARD_HEIGHT / 3;
                  x2 = pos2.x + CARD_WIDTH;
                  y2 = pos2.y + CARD_HEIGHT / 3;
                }
              } else {
                x1 = pos1.x + CARD_WIDTH / 2;
                y1 = pos1.y + CARD_HEIGHT / 2;
                x2 = pos2.x + CARD_WIDTH / 2;
                y2 = pos2.y + CARD_HEIGHT / 2;
              }

              // Add curved paths for better visualization
              const midX = (x1 + x2) / 2;
              const midY = (y1 + y2) / 2;
              const path = `M ${x1} ${y1} Q ${midX} ${midY} ${x2} ${y2}`;

              return (
                <g key={rel.id}>
                  <path
                    d={path}
                    fill="none"
                    {...style}
                    markerEnd={rel.type.includes('parent') || rel.type.includes('child') ? `url(#arrow-${rel.id})` : undefined}
                  />
                  {/* Add arrow markers for parent/child relationships */}
                  {(rel.type.includes('parent') || rel.type.includes('child')) && (
                    <marker
                      id={`arrow-${rel.id}`}
                      viewBox="0 0 10 10"
                      refX="5"
                      refY="5"
                      markerWidth="6"
                      markerHeight="6"
                      orient="auto-start-reverse"
                    >
                      <path d="M 0 0 L 10 5 L 0 10 z" fill={style.stroke} />
                    </marker>
                  )}
                </g>
              );
            }
            return null;
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
    </div>
  );
};

export default FamilyDisplay;
