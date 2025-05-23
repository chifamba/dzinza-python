"use client"; // Required for useState, useEffect

import React, { useState, useEffect, useCallback } from 'react';
import AppHeader from "@/components/AppHeader";
import FamilyDisplay from "@/components/FamilyDisplay";
import AddEditPersonModal from "@/components/modals/AddEditPersonModal";
import AddRelationshipModal from "@/components/modals/AddRelationshipModal";
import AISuggestionsModal from "@/components/modals/AISuggestionsModal"; // Import AI Suggestions Modal
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
import { Person, Relationship } from "@/lib/types";
import { PersonFormData, RelationshipFormData } from "@/lib/schemas";
import { 
  getAISuggestions, // Import Genkit flow wrapper
  AISuggestedRelationshipSchema // Import type for suggestions
} from '@/ai/flows/suggest-relationships';
import { 
  getPeopleAction, 
  addPersonAction, 
  editPersonAction, 
  deletePersonAction,
  addRelationshipAction,
} from '@/app/actions';
import { useToast } from "@/components/ui/use-toast";
import { Loader2 } from 'lucide-react';

const calculateInitialPositions = (peopleToPosition: Person[]): { [personId: string]: { x: number; y: number } } => {
  const positions: { [personId: string]: { x: number; y: number } } = {};
  const cardWidth = 320;
  const cardSpacing = 40;
  const initialY = 100;

  peopleToPosition.forEach((person, index) => {
    positions[person.id] = {
      x: index * (cardWidth + cardSpacing) + 50,
      y: initialY,
    };
  });
  return positions;
};

const ITEMS_PER_PAGE = 5;

export default function Home() {
  const [people, setPeople] = useState<Person[]>([]);
  const [peoplePositions, setPeoplePositions] = useState<{ [personId: string]: { x: number; y: number } }>({});
  const [isLoadingPeople, setIsLoadingPeople] = useState(true);
  
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

  // AI Suggestions State
  const [isAiSuggestionsModalOpen, setIsAiSuggestionsModalOpen] = useState(false);
  const [aiSuggestions, setAiSuggestions] = useState<AISuggestedRelationshipSchema[]>([]);
  const [currentPersonForAiSuggestions, setCurrentPersonForAiSuggestions] = useState<Person | null>(null);
  const [isLoadingAiSuggestions, setIsLoadingAiSuggestions] = useState(false);

  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalPeopleCount, setTotalPeopleCount] = useState(0);

  const { toast } = useToast();

  const loadPeople = useCallback(async (pageToLoad: number) => {
    setIsLoadingPeople(true);
    try {
      const result = await getPeopleAction(pageToLoad, ITEMS_PER_PAGE);
      setPeople(result.people);
      setCurrentPage(result.currentPage);
      setTotalPages(result.totalPages);
      setTotalPeopleCount(result.totalCount);

      if (result.people.length > 0) {
        setPeoplePositions(calculateInitialPositions(result.people));
      } else {
        setPeoplePositions({});
      }
    } catch (error) {
      console.error("Failed to load people:", error);
      toast({
        title: "Error",
        description: "Failed to load family tree data.",
        variant: "destructive",
      });
      setPeople([]);
      setPeoplePositions({});
      setTotalPages(1);
      setTotalPeopleCount(0);
    } finally {
      setIsLoadingPeople(false);
    }
  }, [toast]);

  useEffect(() => {
    loadPeople(currentPage);
  }, [loadPeople, currentPage]);

  const handlePersonDrag = (personId: string, newPosition: { x: number; y: number }) => {
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
        await loadPeople(currentPage); 
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
        await loadPeople(currentPage);
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
        if (people.length === 1 && currentPage > 1) {
            setCurrentPage(prev => prev - 1);
        } else {
            await loadPeople(currentPage);
        }
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
        console.log("Added relationship:", result.relationship);
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
    setAiSuggestions([]); // Clear previous suggestions
    try {
      // Pass all other *currently displayed* people as family members for context
      const familyContext = people.filter(p => p.id !== person.id);
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
    // Here you would typically:
    // 1. Open AddEditPersonModal to confirm/create the new person (suggestion.person2Name, suggestion.person2Gender)
    // 2. If new person created, then open AddRelationshipModal to link them with suggestion.person1Name (currentPersonForAiSuggestions)
    //    using suggestion.relationshipType.
    // This is a complex flow that requires careful state management and user interaction.
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
        disabled={currentPage <= 1 || isLoadingPeople}
      >
        Previous
      </Button>
      <span className="text-sm text-muted-foreground">
        Page {currentPage} of {totalPages} (Total: {totalPeopleCount} people)
      </span>
      <Button
        variant="outline"
        onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
        disabled={currentPage >= totalPages || isLoadingPeople}
      >
        Next
      </Button>
    </div>
  );

  return (
    <div className="flex flex-col min-h-screen">
      <AppHeader onAddPersonClick={handleOpenAddPersonModal} />
      <main className="flex-grow relative overflow-auto">
        {isLoadingPeople ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-muted-foreground">Loading family tree...</p>
          </div>
        ) : people.length > 0 && Object.keys(peoplePositions).length > 0 ? (
          <FamilyDisplay
            people={people}
            peoplePositions={peoplePositions}
            onPersonDrag={handlePersonDrag}
            onEditPerson={handleOpenEditPersonModal}
            onDeletePerson={handleOpenDeleteConfirm}
            onAddRelative={handleOpenAddRelationshipModal}
            onAiSuggest={handleOpenAiSuggestionsModal} // Pass new handler
            isLoadingAiSuggestions={isLoadingAiSuggestions} // Pass loading state
            // To pass isLoadingAiSuggestions only for the specific card:
            // Pass currentPersonForAiSuggestions?.id and compare in FamilyDisplay/PersonCard
            // For simplicity, global loading state is used for all cards' AI buttons for now.
          />
        ) : (
          <div className="flex items-center justify-center h-full">
            <p className="text-muted-foreground">No people found. Start by adding someone.</p>
          </div>
        )}
      </main>
      {!isLoadingPeople && totalPages > 0 && <PaginationControls />}
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
          selectablePeople={people.filter(p => p.id !== currentPersonForRelationship?.id)}
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
