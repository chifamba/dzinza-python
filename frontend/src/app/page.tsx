"use client"; // Required for useState, useEffect

import React, { useState, useEffect, useCallback } from 'react';
import AppHeader from "@/components/AppHeader";
import FamilyDisplay from "@/components/FamilyDisplay";
import AddEditPersonModal from "@/components/modals/AddEditPersonModal";
import AddRelationshipModal from "@/components/modals/AddRelationshipModal";
import AISuggestionsModal from "@/components/modals/AISuggestionsModal";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Person, Relationship, RelationshipType } from "@/lib/types"; // Ensure RelationshipType is imported
import { PersonFormData, RelationshipFormData } from "@/lib/schemas";
import { 
  getAISuggestions,
  AISuggestedRelationshipSchema
} from '@/ai/flows/suggest-relationships';
import { 
  getPeopleAction, 
  addPersonAction, 
  editPersonAction, 
  deletePersonAction,
  addRelationshipAction,
  getRelationshipsAction,
} from '@/app/actions';
import { useToast } from "@/components/ui/use-toast";
import { Loader2 } from 'lucide-react';

const CARD_WIDTH = 320;
const CARD_HEIGHT = 250; // Estimated
const HORIZONTAL_SPACING = 60; // Increased spacing
const VERTICAL_SPACING = 120;   // Increased spacing
const Y_OFFSET = 50;
const CANVAS_WIDTH = 3000; // Assumed canvas width for centering generations

const calculateInitialPositions = (
  peopleToPosition: Person[],
  relationships: Relationship[]
): { [personId: string]: { x: number; y: number } } => {
  if (!peopleToPosition || peopleToPosition.length === 0) {
    return {};
  }

  const positions: { [personId: string]: { x: number; y: number } } = {};
  const childrenMap = new Map<string, string[]>();
  const parentMap = new Map<string, string[]>();
  const personLookup = new Map(peopleToPosition.map(p => [p.id, p]));

  // Initialize maps
  peopleToPosition.forEach(p => {
    childrenMap.set(p.id, []);
    parentMap.set(p.id, []);
  });

  // Populate adjacency maps based on relationships
  relationships.forEach(rel => {
    // Ensure both persons in the relationship exist in the current people list (e.g., current page)
    if (!personLookup.has(rel.person1Id) || !personLookup.has(rel.person2Id)) {
        return; 
    }

    if (rel.type === 'Parent') { // person1 is parent of person2
      childrenMap.get(rel.person1Id)?.push(rel.person2Id);
      parentMap.get(rel.person2Id)?.push(rel.person1Id);
    } else if (rel.type === 'Child') { // person1 is child of person2
      childrenMap.get(rel.person2Id)?.push(rel.person1Id);
      parentMap.get(rel.person1Id)?.push(rel.person2Id);
    }
    // Spouses are handled differently for layout, not strictly parent/child
  });

  // Identify root nodes (those with no parents among the current people)
  const rootNodes = peopleToPosition.filter(p => (parentMap.get(p.id)?.length || 0) === 0);
  if (rootNodes.length === 0 && peopleToPosition.length > 0) {
    // Fallback: if no clear roots (e.g. cycle or all have parents), pick the first person
    // Or, pick people with the fewest incoming parent/child edges if more sophisticated.
    // For now, if all nodes have parents (e.g. a small, fully connected segment or cycle),
    // we might need a more robust root finding or just place them in gen 0.
    // A simple fallback: place all people in gen 0 if no roots found this way. This will lead to a single row.
    // This can happen if the current page of people doesn't include the ultimate ancestors.
    console.warn("No root nodes found. Layout might be suboptimal. Placing all on first row.");
    peopleToPosition.forEach((person, index) => {
        positions[person.id] = {
            x: index * (CARD_WIDTH + HORIZONTAL_SPACING) + Y_OFFSET, // Use Y_OFFSET as X start for consistency
            y: Y_OFFSET,
        };
    });
    return positions;
  }


  const generations = new Map<string, number>();
  const queue: { personId: string; level: number }[] = [];

  rootNodes.forEach(node => {
    generations.set(node.id, 0);
    queue.push({ personId: node.id, level: 0 });
  });

  let maxLevel = 0;
  const visitedInBFS = new Set<string>(); // To handle already processed nodes in BFS

  while (queue.length > 0) {
    const { personId, level } = queue.shift()!;
    if(visitedInBFS.has(personId)) continue; // Should not happen if graph is a tree and roots are correct
    visitedInBFS.add(personId);

    maxLevel = Math.max(maxLevel, level);

    const children = childrenMap.get(personId) || [];
    children.forEach(childId => {
      if (!generations.has(childId) || generations.get(childId)! > level + 1) {
        generations.set(childId, level + 1);
        queue.push({ personId: childId, level: level + 1 });
      }
    });
  }
  
  // Handle people not reached by BFS (e.g. disconnected components or if root finding was partial)
  // Place them in a subsequent generation or a default row.
  let unplacedLevel = maxLevel + 2; // Start unplaced further down
  peopleToPosition.forEach(p => {
      if(!generations.has(p.id)) {
          generations.set(p.id, unplacedLevel);
          maxLevel = Math.max(maxLevel, unplacedLevel);
          unplacedLevel++; // Stagger them if multiple
      }
  });


  const peopleByGeneration = new Map<number, string[]>();
  generations.forEach((level, personId) => {
    if (!peopleByGeneration.has(level)) {
      peopleByGeneration.set(level, []);
    }
    peopleByGeneration.get(level)!.push(personId);
  });

  // Calculate X/Y positions
  for (let i = 0; i <= maxLevel; i++) {
    const genLevelPeopleIds = peopleByGeneration.get(i) || [];
    if (genLevelPeopleIds.length === 0) continue;

    const y = i * (CARD_HEIGHT + VERTICAL_SPACING) + Y_OFFSET;
    const totalWidth = genLevelPeopleIds.length * CARD_WIDTH + (genLevelPeopleIds.length - 1) * HORIZONTAL_SPACING;
    let startX = (CANVAS_WIDTH - totalWidth) / 2;
    if (startX < Y_OFFSET) startX = Y_OFFSET; // Ensure some padding from left

    genLevelPeopleIds.forEach((personId, index) => {
      const x = startX + index * (CARD_WIDTH + HORIZONTAL_SPACING);
      positions[personId] = { x, y };
    });
  }

  // Spouse adjustment (simple version: try to place spouses next to each other)
  // This is a basic pass. More complex logic is needed for optimal spouse placement.
  relationships.forEach(rel => {
    if (rel.type === 'Spouse') {
      const p1Id = rel.person1Id;
      const p2Id = rel.person2Id;

      const pos1 = positions[p1Id];
      const pos2 = positions[p2Id];
      const gen1 = generations.get(p1Id);
      const gen2 = generations.get(p2Id);

      // Ensure both spouses are in the same generation and have positions
      if (pos1 && pos2 && gen1 !== undefined && gen1 === gen2) {
        // If they are not already next to each other (or very close)
        if (Math.abs(pos1.x - pos2.x) > CARD_WIDTH + HORIZONTAL_SPACING * 1.5) { // Allow some gap
          // Attempt to move p2 next to p1
          // This is very naive: it doesn't check for collisions or shift other nodes.
          // A real implementation would need to adjust other nodes in the row.
          // For now, we just place p2 to the right of p1.
          // This simplified approach might lead to overlaps if not careful.
          // const peopleInTheirGeneration = peopleByGeneration.get(gen1) || [];
          // Find p1's index in its generation row
          // const p1Index = peopleInTheirGeneration.findIndex(id => id === p1Id);
          // If p1 exists, try to place p2 next to it.
          // This needs a more robust algorithm to avoid overwriting / ensure space.
          // For this subtask, the subtask stated: "Simplification for this subtask: Initially, don't reorder for spouses."
          // So, we will skip the reordering part for now. The lines will connect them.
        }
      }
    }
  });


  return positions;
};

const ITEMS_PER_PAGE = 12; // Increased to show more people for layout testing

export default function Home() {
  const [people, setPeople] = useState<Person[]>([]);
  const [peoplePositions, setPeoplePositions] = useState<{ [personId: string]: { x: number; y: number } }>({});
  const [relationships, setRelationships] = useState<Relationship[]>([]);
  const [isLoadingData, setIsLoadingData] = useState(true);
  
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editingPerson, setEditingPerson] = useState<Partial<PersonFormData> | null>(null);
  const [isSubmittingPerson, setIsSubmittingPerson] = useState(false);

  const [isDeleteConfirmOpen, setIsDeleteConfirmOpen] = useState(false);
  const [deletingPersonId, setDeletingPersonId] = useState<string | null>(null);
  const [isDeletingPerson, setIsDeletingPerson] = useState(false);

  const [isAddRelationshipModalOpen, setIsAddRelationshipModalOpen] = useState(false);
  const [currentPersonForRelationship, setCurrentPersonForRelationship] = useState<Person | null>(null);
  const [isSubmittingRelationship, setIsSubmittingRelationship] = useState(false);

  const [isAiSuggestionsModalOpen, setIsAiSuggestionsModalOpen] = useState(false);
  const [aiSuggestions, setAiSuggestions] = useState<AISuggestedRelationshipSchema[]>([]);
  const [currentPersonForAiSuggestions, setCurrentPersonForAiSuggestions] = useState<Person | null>(null);
  const [isLoadingAiSuggestions, setIsLoadingAiSuggestions] = useState(false);

  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalPeopleCount, setTotalPeopleCount] = useState(0);

  const { toast } = useToast();

  const loadInitialData = useCallback(async (pageToLoad: number) => {
    setIsLoadingData(true);
    try {
      // Fetch all people for layout calculation, then paginate for display if needed
      // For this subtask, we assume all people are fetched for layout.
      // If only a page of people is fetched, the layout might be incomplete.
      // The subtask implies calculateInitialPositions gets ALL people and relationships.
      // So, we'll fetch all people first for layout, then paginate the result for display.
      
      // Step 1: Fetch ALL people and ALL relationships for layout
      const allPeopleResult = await getPeopleAction(1, 1000); // Fetch all
      const allRelationships = await getRelationshipsAction();
      
      setRelationships(allRelationships); // Set all relationships for line drawing

      // Step 2: Calculate positions based on ALL data
      const allPositions = calculateInitialPositions(allPeopleResult.people, allRelationships);

      // Step 3: Paginate the people list for display
      const totalCount = allPeopleResult.people.length;
      const totalPagesCalc = Math.ceil(totalCount / ITEMS_PER_PAGE);
      setTotalPages(totalPagesCalc);
      setTotalPeopleCount(totalCount);

      let currentPageValidated = pageToLoad;
      if (currentPageValidated < 1) currentPageValidated = 1;
      if (currentPageValidated > totalPagesCalc && totalPagesCalc > 0) currentPageValidated = totalPagesCalc;
      setCurrentPage(currentPageValidated);
      
      const startIndex = (currentPageValidated - 1) * ITEMS_PER_PAGE;
      const endIndex = currentPageValidated * ITEMS_PER_PAGE;
      const paginatedPeopleForDisplay = allPeopleResult.people.slice(startIndex, endIndex);
      
      setPeople(paginatedPeopleForDisplay);

      // Filter positions for the people actually displayed on the current page
      const displayPositions: { [personId: string]: { x: number; y: number } } = {};
      paginatedPeopleForDisplay.forEach(p => {
        if (allPositions[p.id]) {
          displayPositions[p.id] = allPositions[p.id];
        }
      });
      setPeoplePositions(displayPositions);

    } catch (error) {
      console.error("Failed to load initial data:", error);
      toast({
        title: "Error",
        description: "Failed to load family tree data.",
        variant: "destructive",
      });
      setPeople([]);
      setRelationships([]);
      setPeoplePositions({});
      setTotalPages(1);
      setTotalPeopleCount(0);
    } finally {
      setIsLoadingData(false);
    }
  }, [toast]); // toast is stable

  useEffect(() => {
    loadInitialData(currentPage);
  }, [loadInitialData, currentPage]);

  const handlePersonDrag = (personId: string, newPosition: { x: number; y: number }) => {
    // Update position in the context of ALL positions, then filter for display if needed
    // For now, this updates the positions for the currently displayed people.
    // If we drag a card, its position in a hypothetical 'allPositions' map should be updated.
    setPeoplePositions(prev => ({ ...prev, [personId]: newPosition }));
  };

  const handleOpenAddPersonModal = () => {
    setEditingPerson(null);
    setIsAddModalOpen(true);
  };

  const handleAddPersonSubmit = async (data: PersonFormData) => {
    setIsSubmittingPerson(true);
    try {
      const result = await addPersonAction(data);
      if (result.success && result.person) {
        toast({
          title: "Success",
          description: `${result.person.name} added successfully!`,
        });
        // Recalculate layout based on all people, then determine page
        // For simplicity, go to the page that would contain the new total number of people
        const newTotalCount = totalPeopleCount + 1;
        const newTotalPages = Math.ceil(newTotalCount / ITEMS_PER_PAGE);
        await loadInitialData(newTotalPages); 
        setIsAddModalOpen(false);
      } else {
        toast({
          title: "Error",
          description: result.error || "Failed to add person.",
          variant: "destructive",
        });
      }
    } catch (error) {
      console.error("Error submitting form:", error);
      toast({
        title: "Error",
        description: "An unexpected error occurred while adding person.",
        variant: "destructive",
      });
    } finally {
      setIsSubmittingPerson(false);
    }
  };

  const handleOpenEditPersonModal = (person: Person) => {
    const formData: Partial<PersonFormData> = {
      ...person,
      birthDate: person.birthDate ? new Date(person.birthDate) : undefined,
      deathDate: person.deathDate ? new Date(person.deathDate) : undefined,
    };
    setEditingPerson(formData);
    setIsEditModalOpen(true);
  };

  const handleEditPersonSubmit = async (data: PersonFormData) => {
    if (!editingPerson || !(editingPerson as Person).id) { 
      toast({ title: "Error", description: "No person selected for editing.", variant: "destructive" });
      return;
    }
    setIsSubmittingPerson(true);
    try {
      const personIdToEdit = (editingPerson as Person).id;
      const result = await editPersonAction(personIdToEdit, data);
      if (result.success && result.person) {
        toast({
          title: "Success",
          description: `${result.person.name} updated successfully!`,
        });
        await loadInitialData(currentPage);
        setIsEditModalOpen(false);
        setEditingPerson(null);
      } else {
        toast({
          title: "Error",
          description: result.error || "Failed to update person.",
          variant: "destructive",
        });
      }
    } catch (error) {
      console.error("Error submitting edit form:", error);
      toast({
        title: "Error",
        description: "An unexpected error occurred while updating person.",
        variant: "destructive",
      });
    } finally {
      setIsSubmittingPerson(false);
    }
  };

  const handleOpenDeleteConfirm = (personId: string) => {
    setDeletingPersonId(personId);
    setIsDeleteConfirmOpen(true);
  };

  const handleDeletePersonConfirm = async () => {
    if (!deletingPersonId) return;
    setIsDeletingPerson(true);
    try {
      const result = await deletePersonAction(deletingPersonId);
      if (result.success) {
        toast({
          title: "Success",
          description: "Person deleted successfully!",
        });
        const currentTotalPeople = totalPeopleCount -1;
        const newTotalPages = Math.ceil(currentTotalPeople / ITEMS_PER_PAGE);
        let pageToLoad = currentPage;
        if(currentPage > newTotalPages && newTotalPages > 0) {
            pageToLoad = newTotalPages;
        }
        if(currentTotalPeople === 0) pageToLoad = 1;

        await loadInitialData(pageToLoad);
        if(currentPage > newTotalPages && newTotalPages > 0) setCurrentPage(newTotalPages);


      } else {
        toast({
          title: "Error",
          description: result.error || "Failed to delete person.",
          variant: "destructive",
        });
      }
    } catch (error) {
      console.error("Error deleting person:", error);
      toast({
        title: "Error",
        description: "An unexpected error occurred while deleting person.",
        variant: "destructive",
      });
    } finally {
      setIsDeletingPerson(false);
      setIsDeleteConfirmOpen(false);
      setDeletingPersonId(null);
    }
  };
  
  const handleOpenAddRelationshipModal = (person: Person) => {
    setCurrentPersonForRelationship(person);
    setIsAddRelationshipModalOpen(true);
  };

  const handleAddRelationshipSubmit = async (data: RelationshipFormData) => {
    setIsSubmittingRelationship(true);
    try {
      const result = await addRelationshipAction(data);
      if (result.success && result.relationship) {
        toast({
          title: "Success",
          description: `Relationship added successfully! ID: ${result.relationship.id}`,
        });
        await loadInitialData(currentPage); // Reload all data to reflect new relationship for layout
        setIsAddRelationshipModalOpen(false);
        setCurrentPersonForRelationship(null);
      } else {
        toast({
          title: "Error",
          description: result.error || "Failed to add relationship.",
          variant: "destructive",
        });
      }
    } catch (error) {
      console.error("Error submitting relationship form:", error);
      toast({
        title: "Error",
        description: "An unexpected error occurred while adding relationship.",
        variant: "destructive",
      });
    } finally {
      setIsSubmittingRelationship(false);
    }
  };

  const handleOpenAiSuggestionsModal = async (person: Person) => {
    setCurrentPersonForAiSuggestions(person);
    setIsAiSuggestionsModalOpen(true);
    setIsLoadingAiSuggestions(true);
    setAiSuggestions([]);
    try {
      // Fetch all people for AI context, not just current page
      const allPeopleResult = await getPeopleAction(1, 1000); 
      const familyContext = allPeopleResult.people.filter(p => p.id !== person.id);
      const result = await getAISuggestions({ person: person, familyMembers: familyContext });
      setAiSuggestions(result.suggestions);
      if (result.suggestions.length === 0) {
        toast({
          title: "AI Suggestions",
          description: "No new relationship suggestions found at this time.",
        });
      }
    } catch (error) {
      console.error("Error getting AI suggestions:", error);
      toast({
        title: "AI Error",
        description: "Could not fetch AI suggestions.",
        variant: "destructive",
      });
    } finally {
      setIsLoadingAiSuggestions(false);
    }
  };

  const handleAddAiSuggestion = (suggestion: AISuggestedRelationshipSchema) => {
    console.log("TODO: Implement adding AI suggestion:", suggestion);
    toast({
      title: "Not Implemented",
      description: "Adding this AI suggestion is not yet implemented.",
    });
  };

  const addEditModalMode = isEditModalOpen ? 'edit' : 'add';
  const addEditModalIsOpen = isAddModalOpen || isEditModalOpen;
  const addEditModalOnSubmit = isEditModalOpen ? handleEditPersonSubmit : handleAddPersonSubmit;
  const addEditModalInitialData = isEditModalOpen ? editingPerson : undefined;
  const addEditModalOnClose = () => {
    setIsAddModalOpen(false);
    setIsEditModalOpen(false);
    setEditingPerson(null);
  };

  const PaginationControls = () => (
    <div className="flex items-center justify-center space-x-4 p-4">
      <Button
        variant="outline"
        onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
        disabled={currentPage <= 1 || isLoadingData}
      >
        Previous
      </Button>
      <span className="text-sm text-muted-foreground">
        Page {currentPage} of {totalPages} (Total: {totalPeopleCount} people)
      </span>
      <Button
        variant="outline"
        onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
        disabled={currentPage >= totalPages || isLoadingData}
      >
        Next
      </Button>
    </div>
  );

  return (
    <div className="flex flex-col min-h-screen">
      <AppHeader onAddPersonClick={handleOpenAddPersonModal} />
      <main className="flex-grow relative overflow-auto">
        {isLoadingData ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-muted-foreground">Loading family tree...</p>
          </div>
        ) : people.length > 0 && Object.keys(peoplePositions).length > 0 ? (
          <FamilyDisplay
            people={people} // This is now paginated people for display
            peoplePositions={peoplePositions} // These are positions for the paginated people
            relationships={relationships} // All relationships for drawing lines
            onPersonDrag={handlePersonDrag}
            onEditPerson={handleOpenEditPersonModal}
            onDeletePerson={handleOpenDeleteConfirm}
            onAddRelative={handleOpenAddRelationshipModal}
            onAiSuggest={handleOpenAiSuggestionsModal}
            isLoadingAiSuggestions={isLoadingAiSuggestions}
          />
        ) : (
          <div className="flex items-center justify-center h-full">
            <p className="text-muted-foreground">No people found. Start by adding someone.</p>
          </div>
        )}
      </main>
      {!isLoadingData && totalPages > 0 && <PaginationControls />}
      <AddEditPersonModal
        isOpen={addEditModalIsOpen}
        onClose={addEditModalOnClose}
        onSubmit={addEditModalOnSubmit}
        initialData={addEditModalInitialData || undefined}
        isLoading={isSubmittingPerson}
        mode={addEditModalMode}
      />
      <AlertDialog open={isDeleteConfirmOpen} onOpenChange={setIsDeleteConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. This will permanently delete this person
              and all their associated data.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setDeletingPersonId(null)} disabled={isDeletingPerson}>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeletePersonConfirm} disabled={isDeletingPerson}>
              {isDeletingPerson ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              Continue
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      {currentPersonForRelationship && (
        <AddRelationshipModal
          isOpen={isAddRelationshipModalOpen}
          onClose={() => {
            setIsAddRelationshipModalOpen(false);
            setCurrentPersonForRelationship(null);
          }}
          onSubmit={handleAddRelationshipSubmit}
          currentPerson={currentPersonForRelationship}
          selectablePeople={people.filter(p => p.id !== currentPersonForRelationship?.id)} // This should use allPeople for selection ideally
          isLoading={isSubmittingRelationship}
        />
      )}
      {currentPersonForAiSuggestions && (
        <AISuggestionsModal
          isOpen={isAiSuggestionsModalOpen}
          onClose={() => {
            setIsAiSuggestionsModalOpen(false);
            setCurrentPersonForAiSuggestions(null);
            setAiSuggestions([]);
          }}
          suggestions={aiSuggestions}
          targetPersonName={currentPersonForAiSuggestions.name}
          isLoading={isLoadingAiSuggestions}
          onAddSuggestion={handleAddAiSuggestion}
        />
      )}
    </div>
  );
}
