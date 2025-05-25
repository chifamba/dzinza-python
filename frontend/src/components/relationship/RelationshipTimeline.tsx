import React, { useState } from 'react';
import { Relationship, RelationshipType, Person } from '@/lib/types';
import { CalendarRange, ArrowRight, Clock, MapPin, FileText, ChevronDown, ChevronUp, Filter } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

// Helper to display human-readable relationship types
const relationshipLabels: Record<string, string> = {
  'biological_parent': 'Biological Parent',
  'adoptive_parent': 'Adoptive Parent',
  'step_parent': 'Step Parent',
  'foster_parent': 'Foster Parent',
  'guardian': 'Guardian',
  'biological_child': 'Biological Child',
  'adoptive_child': 'Adoptive Child',
  'step_child': 'Step Child',
  'foster_child': 'Foster Child',
  'spouse_current': 'Current Spouse',
  'spouse_former': 'Former Spouse',
  'partner': 'Partner',
  'sibling_full': 'Full Sibling',
  'sibling_half': 'Half Sibling',
  'sibling_step': 'Step Sibling',
  'sibling_adoptive': 'Adoptive Sibling',
  'other': 'Other Relationship'
};

interface RelationshipTimelineProps {
  relationships: Relationship[];
  people: Record<string, Person>;
  focusPersonId?: string;
  onEditRelationship?: (relationship: Relationship) => void;
  onDeleteRelationship?: (relationshipId: string) => void;
}

export function RelationshipTimeline({
  relationships,
  people,
  focusPersonId,
  onEditRelationship,
  onDeleteRelationship
}: RelationshipTimelineProps) {
  // State for managing expanded items
  const [expandedItems, setExpandedItems] = useState<Record<string, boolean>>({});
  // State for relationship type filter
  const [selectedType, setSelectedType] = useState<string>('');

  // Toggle expanded state for an item
  const toggleExpanded = (id: string) => {
    setExpandedItems(prev => ({
      ...prev,
      [id]: !prev[id]
    }));
  };
  
  // Helper to sort relationships chronologically
  const sortedRelationships = [...relationships].sort((a, b) => {
    // Sort by start date if available
    if (a.startDate && b.startDate) {
      return new Date(a.startDate).getTime() - new Date(b.startDate).getTime();
    }
    if (a.startDate) return -1;
    if (b.startDate) return 1;
    
    // Otherwise sort by relationship type
    return a.type.localeCompare(b.type);
  });

  // Filter relationships by type if a type is selected
  const filteredRelationships = selectedType 
    ? sortedRelationships.filter(rel => rel.type.includes(selectedType.toLowerCase()))
    : sortedRelationships;

  // Group relationships by person from the perspective of the focus person
  const groupedByPerson: Record<string, Relationship[]> = {};
  
  if (focusPersonId) {
    filteredRelationships.forEach(rel => {
      const otherPersonId = rel.person1Id === focusPersonId ? rel.person2Id : rel.person1Id;
      if (!groupedByPerson[otherPersonId]) {
        groupedByPerson[otherPersonId] = [];
      }
      groupedByPerson[otherPersonId].push(rel);
    });
  }

  // Get verification status from custom attributes
  const getVerificationStatus = (relationship: Relationship): 'verified' | 'unverified' | 'disputed' => {
    return (relationship.customAttributes?.verificationStatus as any) || 'unverified';
  };

  // Format date for display
  const formatDate = (dateString?: string): string => {
    if (!dateString) return 'Unknown';
    return new Date(dateString).toLocaleDateString();
  };

  // Color based on relationship type
  const getTypeColor = (type: RelationshipType): string => {
    if (type.includes('parent') || type.includes('child')) {
      return 'bg-blue-100 text-blue-800';
    }
    if (type.includes('spouse') || type === 'partner') {
      return 'bg-pink-100 text-pink-800';
    }
    if (type.includes('sibling')) {
      return 'bg-green-100 text-green-800';
    }
    return 'bg-gray-100 text-gray-800';
  };

  // Status badge color
  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'verified': return 'bg-green-100 text-green-800';
      case 'disputed': return 'bg-red-100 text-red-800';
      default: return 'bg-yellow-100 text-yellow-800';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">
          {focusPersonId && people[focusPersonId] ? 
            `${people[focusPersonId].name}'s Relationships` : 
            'Relationship Timeline'
          }
        </h2>

        {/* Filter dropdown */}
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4" />
          <Select value={selectedType} onValueChange={setSelectedType}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Filter by type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">All types</SelectItem>
              <SelectGroup>
                <SelectLabel>Family</SelectLabel>
                <SelectItem value="parent">Parents</SelectItem>
                <SelectItem value="child">Children</SelectItem>
                <SelectItem value="sibling">Siblings</SelectItem>
              </SelectGroup>
              <SelectGroup>
                <SelectLabel>Partners</SelectLabel>
                <SelectItem value="spouse">Spouses</SelectItem>
                <SelectItem value="partner">Partners</SelectItem>
              </SelectGroup>
              <SelectItem value="other">Other</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
      
      {focusPersonId ? (
        <div className="space-y-6">
          {Object.entries(groupedByPerson).map(([personId, relationships]) => {
            const person = people[personId];
            if (!person) return null;
            
            return (
              <Card key={personId} className="overflow-hidden">
                <CardHeader className="pb-2">
                  <CardTitle>{person.name}</CardTitle>
                  <CardDescription>
                    {relationships.length} relationship{relationships.length !== 1 ? 's' : ''}
                  </CardDescription>
                </CardHeader>
                
                <div className="pl-6 ml-3 border-l-2 border-gray-200 py-2 space-y-4">
                  {relationships.map((relationship, index) => {
                    const status = getVerificationStatus(relationship);
                    const isExpanded = expandedItems[relationship.id] || false;
                    
                    return (
                      <div key={relationship.id} className="relative">
                        {/* Timeline dot */}
                        <div className="absolute -left-[28px] top-1 w-5 h-5 rounded-full bg-white border-2 border-gray-300" />
                        
                        <div className="ml-4 space-y-2 pb-4">
                          <div className="flex flex-wrap gap-2 items-start">
                            <Badge className={getTypeColor(relationship.type)}>
                              {relationshipLabels[relationship.type]}
                            </Badge>
                            
                            <Badge 
                              variant="outline" 
                              className={cn(
                                "capitalize",
                                getStatusColor(status)
                              )}
                            >
                              {status}
                            </Badge>
                          </div>
                          
                          {/* Date info */}
                          {(relationship.startDate || relationship.endDate) && (
                            <div className="flex items-center text-sm text-gray-600">
                              <Clock className="mr-1 h-4 w-4" />
                              {relationship.startDate && 
                                <span>From {formatDate(relationship.startDate)}</span>
                              }
                              {relationship.startDate && relationship.endDate && 
                                <ArrowRight className="mx-1 h-3 w-3" />
                              }
                              {relationship.endDate && 
                                <span>To {formatDate(relationship.endDate)}</span>
                              }
                              {!relationship.startDate && relationship.endDate && 
                                <span>Until {formatDate(relationship.endDate)}</span>
                              }
                            </div>
                          )}
                          
                          {/* Location */}
                          {relationship.location && (
                            <div className="flex items-center text-sm text-gray-600">
                              <MapPin className="mr-1 h-4 w-4" />
                              <span>{relationship.location}</span>
                            </div>
                          )}
                          
                          {/* Description */}
                          {relationship.description && (
                            <div className="flex items-start text-sm text-gray-600">
                              <FileText className="mr-1 h-4 w-4 mt-0.5 flex-shrink-0" />
                              <p>{relationship.description}</p>
                            </div>
                          )}
                          
                          {/* Custom attributes */}
                          {relationship.customAttributes && 
                           Object.entries(relationship.customAttributes)
                             .filter(([key]) => key !== 'verificationStatus')
                             .length > 0 && (
                            <div className="mt-2">
                              <div className="flex items-center justify-between">
                                <h4 className="text-sm font-medium">Additional Information</h4>
                                <Button 
                                  variant="ghost" 
                                  size="sm" 
                                  onClick={() => toggleExpanded(relationship.id)}
                                  className="h-6 px-2"
                                  aria-label={isExpanded ? "Hide details" : "Show details"}
                                >
                                  {isExpanded ? (
                                    <>
                                      <ChevronUp className="h-4 w-4 mr-1" />
                                      <span className="text-xs">Hide details</span>
                                    </>
                                  ) : (
                                    <>
                                      <ChevronDown className="h-4 w-4 mr-1" />
                                      <span className="text-xs">Show details</span>
                                    </>
                                  )}
                                </Button>
                              </div>
                              
                              {isExpanded && (
                                <div className="grid grid-cols-2 gap-1 mt-1">
                                  {Object.entries(relationship.customAttributes)
                                    .filter(([key]) => key !== 'verificationStatus')
                                    .map(([key, value]) => (
                                      <div key={key} className="text-sm">
                                        <span className="font-medium capitalize">{key}: </span>
                                        <span className="text-gray-600">{value}</span>
                                      </div>
                                    ))
                                  }
                                </div>
                              )}
                            </div>
                          )}
                          
                          {/* Actions */}
                          {(onEditRelationship || onDeleteRelationship) && (
                            <div className="flex space-x-2 mt-2">
                              {onEditRelationship && (
                                <Button 
                                  variant="outline" 
                                  size="sm"
                                  onClick={() => onEditRelationship(relationship)}
                                  aria-label="Edit relationship"
                                >
                                  Edit
                                </Button>
                              )}
                              {onDeleteRelationship && (
                                <Button 
                                  variant="outline" 
                                  size="sm"
                                  className="text-red-500 hover:text-red-700"
                                  onClick={() => {
                                    if (confirm('Are you sure you want to delete this relationship?')) {
                                      onDeleteRelationship(relationship.id);
                                    }
                                  }}
                                  aria-label="Delete relationship"
                                >
                                  Delete
                                </Button>
                              )}
                            </div>
                          )}
                        </div>
                        
                        {/* Add separator except for last item */}
                        {index < relationships.length - 1 && (
                          <Separator className="mt-2" />
                        )}
                      </div>
                    );
                  })}
                </div>
              </Card>
            );
          })}
        </div>
      ) : (
        // View for all relationships regardless of focus person
        <div className="space-y-4">
          {filteredRelationships.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              No relationships to display
            </div>
          ) : (
            <div className="pl-6 ml-3 border-l-2 border-gray-200 py-2 space-y-8">
              {filteredRelationships.map((relationship, index) => {
                const person1 = people[relationship.person1Id];
                const person2 = people[relationship.person2Id];
                const status = getVerificationStatus(relationship);
                const isExpanded = expandedItems[relationship.id] || false;
                
                if (!person1 || !person2) return null;
                
                return (
                  <div key={relationship.id} className="relative">
                    {/* Timeline dot */}
                    <div className="absolute -left-[28px] top-1 w-5 h-5 rounded-full bg-white border-2 border-gray-300" />
                    
                    <div className="ml-4 space-y-2">
                      <h3 className="font-bold flex items-center">
                        {person1.name}
                        <ArrowRight className="mx-2 h-4 w-4" />
                        {person2.name}
                      </h3>
                      
                      <div className="flex flex-wrap gap-2 items-start">
                        <Badge className={getTypeColor(relationship.type)}>
                          {relationshipLabels[relationship.type]}
                        </Badge>
                        
                        <Badge 
                          variant="outline" 
                          className={cn(
                            "capitalize",
                            getStatusColor(status)
                          )}
                        >
                          {status}
                        </Badge>
                      </div>
                      
                      {/* Date info */}
                      {(relationship.startDate || relationship.endDate) && (
                        <div className="flex items-center text-sm text-gray-600">
                          <Clock className="mr-1 h-4 w-4" />
                          {relationship.startDate && 
                            <span>From {formatDate(relationship.startDate)}</span>
                          }
                          {relationship.startDate && relationship.endDate && 
                            <ArrowRight className="mx-1 h-3 w-3" />
                          }
                          {relationship.endDate && 
                            <span>To {formatDate(relationship.endDate)}</span>
                          }
                          {!relationship.startDate && relationship.endDate && 
                            <span>Until {formatDate(relationship.endDate)}</span>
                          }
                        </div>
                      )}
                      
                      {/* Location */}
                      {relationship.location && (
                        <div className="flex items-center text-sm text-gray-600">
                          <MapPin className="mr-1 h-4 w-4" />
                          <span>{relationship.location}</span>
                        </div>
                      )}
                      
                      {/* Description */}
                      {relationship.description && (
                        <div className="flex items-start text-sm text-gray-600">
                          <FileText className="mr-1 h-4 w-4 mt-0.5 flex-shrink-0" />
                          <p>{relationship.description}</p>
                        </div>
                      )}
                      
                      {/* Custom attributes */}
                      {relationship.customAttributes && 
                       Object.entries(relationship.customAttributes)
                         .filter(([key]) => key !== 'verificationStatus')
                         .length > 0 && (
                        <div className="mt-2">
                          <div className="flex items-center justify-between">
                            <h4 className="text-sm font-medium">Additional Information</h4>
                            <Button 
                              variant="ghost" 
                              size="sm" 
                              onClick={() => toggleExpanded(relationship.id)}
                              className="h-6 px-2"
                              aria-label={isExpanded ? "Hide details" : "Show details"}
                            >
                              {isExpanded ? (
                                <>
                                  <ChevronUp className="h-4 w-4 mr-1" />
                                  <span className="text-xs">Hide details</span>
                                </>
                              ) : (
                                <>
                                  <ChevronDown className="h-4 w-4 mr-1" />
                                  <span className="text-xs">Show details</span>
                                </>
                              )}
                            </Button>
                          </div>
                          
                          {isExpanded && (
                            <div className="grid grid-cols-2 gap-1 mt-1">
                              {Object.entries(relationship.customAttributes)
                                .filter(([key]) => key !== 'verificationStatus')
                                .map(([key, value]) => (
                                  <div key={key} className="text-sm">
                                    <span className="font-medium capitalize">{key}: </span>
                                    <span className="text-gray-600">{value}</span>
                                  </div>
                                ))
                              }
                            </div>
                          )}
                        </div>
                      )}
                      
                      {/* Actions */}
                      {(onEditRelationship || onDeleteRelationship) && (
                        <div className="flex space-x-2 mt-2">
                          {onEditRelationship && (
                            <Button 
                              variant="outline" 
                              size="sm"
                              onClick={() => onEditRelationship(relationship)}
                              aria-label="Edit relationship"
                            >
                              Edit
                            </Button>
                          )}
                          {onDeleteRelationship && (
                            <Button 
                              variant="outline" 
                              size="sm"
                              className="text-red-500 hover:text-red-700"
                              onClick={() => {
                                if (confirm('Are you sure you want to delete this relationship?')) {
                                  onDeleteRelationship(relationship.id);
                                }
                              }}
                              aria-label="Delete relationship"
                            >
                              Delete
                            </Button>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
