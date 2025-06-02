import React, { useState, useEffect, useCallback } from 'react';
import { Person, FamilyTreeState } from '../types';
import FamilyTreeView from './FamilyTreeViewExport';
import PersonForm from './PersonForm';
import Header from './Header';
import InfoPanel from './InfoPanel';
import LeftNavPanel from './LeftNavPanel';
import { getFamilyTree, addPerson, updatePerson, deletePerson, updatePersonOrder } from '../api/familyTreeService';

const FamilyTreeContainer: React.FC = () => {
  const [persons, setPersons] = useState<Person[]>([]);
  const [selectedPersonId, setSelectedPersonId] = useState<string | null>(null);
  
  const [showForm, setShowForm] = useState(false);
  const [editingPerson, setEditingPerson] = useState<Person | undefined>(undefined);
  
  // Fetch initial data
  useEffect(() => {
    const loadData = async () => {
      const fetchedPersons = await getFamilyTree();
      // Sort by displayOrder, handling undefined values
      const sortedPersons = fetchedPersons.sort((a, b) => {
        const orderA = a.displayOrder === undefined ? Infinity : a.displayOrder;
        const orderB = b.displayOrder === undefined ? Infinity : b.displayOrder;
        return orderA - orderB;
      });
      setPersons(sortedPersons);
    };
    
    loadData();
  }, []);

  const handleSetPersons = useCallback((newPersons: Person[] | ((prevPersons: Person[]) => Person[])) => {
    setPersons(prevPersons => {
      const updatedPersons = typeof newPersons === 'function' ? newPersons(prevPersons) : newPersons;
      // Call the function to update backend here
      handleUpdatePersonOrder(updatedPersons);
      return updatedPersons;
    });
  }, []);

  const handleUpdatePersonOrder = async (orderedPersons: Person[]) => {
    const personsWithOrder = orderedPersons.map((person, index) => ({
      ...person,
      displayOrder: index,
    }));
    try {
      await updatePersonOrder(personsWithOrder);
      // Optimistically updated the frontend, backend call confirms or could trigger rollback
      setPersons(personsWithOrder); // Ensure local state reflects the new order immediately
    } catch (error) {
      console.error("Failed to update person order:", error);
      // Optionally: revert to previous order or show error to user
      // For now, we'll keep the optimistic update.
    }
  };
  
  const handleAddPerson = (parentId?: string) => {
    setEditingPerson(undefined);
    if (parentId) {
      // Find the parent to get their last name
      const parent = persons.find(p => p.id === parentId);
      // Create a basic template for the new person with parentId
      setEditingPerson({ 
        id: '', 
        firstName: '',
        lastName: parent?.lastName || '', // Auto-fill parent's last name
        name: '', 
        parentId, 
        color: 'blue',
        isLiving: true 
      } as Person);
    }
    setShowForm(true);
  };
  
  const handleEditPerson = (personId: string) => {
    const person = persons.find(p => p.id === personId);
    if (person) {
      // Make sure firstName and lastName are populated if only name exists
      if (!person.firstName && !person.lastName && person.name) {
        const nameParts = person.name.split(' ');
        if (nameParts.length >= 2) {
          person.firstName = nameParts[0];
          person.lastName = nameParts[nameParts.length - 1];
          if (nameParts.length > 2) {
            person.middleNames = nameParts.slice(1, nameParts.length - 1).join(' ');
          }
        } else if (nameParts.length === 1) {
          person.firstName = nameParts[0];
          person.lastName = '';
        }
      }
      
      setEditingPerson(person);
      setShowForm(true);
    }
  };
  
  const handleDeletePerson = async (personId: string) => {
    if (window.confirm('Are you sure you want to delete this person?')) {
      const success = await deletePerson(personId);
      if (success) {
        setPersons(prevPersons => prevPersons.filter(p => p.id !== personId));
        if (selectedPersonId === personId) {
          setSelectedPersonId(null);
        }
      }
    }
  };
  
  const handleSavePerson = async (data: Partial<Person>) => {
    let savedPerson: Person | null = null;
    if (editingPerson?.id) {
      // Update existing person
      savedPerson = await updatePerson(editingPerson.id, data);
      if (savedPerson) {
        setPersons(prevPersons =>
          prevPersons.map(p => (p.id === editingPerson.id ? { ...p, ...savedPerson } : p))
        );
      }
    } else {
      // Add new person
      // Ensure displayOrder is set for new persons
      const newPersonData = {
        ...data,
        displayOrder: persons.length
      } as Omit<Person, 'id'>;
      savedPerson = await addPerson(newPersonData);
      if (savedPerson) {
        setPersons(prevPersons => [...prevPersons, savedPerson!]);
      }
    }
    
    setShowForm(false);
    setEditingPerson(undefined);
  };
  
  const handleSelectPerson = (personId: string) => {
    setSelectedPersonId(personId);
  };
  
  const selectedPerson = selectedPersonId
    ? persons.find(p => p.id === selectedPersonId) || null
    : null;
  
  return (
    <div className="flex flex-col h-screen">
      <Header onAddPerson={() => handleAddPerson()} />
      
      <main className="flex-1 flex overflow-hidden">
        <LeftNavPanel
          persons={persons}
          onPersonSelect={handleSelectPerson}
          onAddPerson={() => handleAddPerson()}
          selectedPersonId={selectedPersonId}
        />
        
        <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
          <div className="md:w-3/4 h-full overflow-hidden relative">
            <FamilyTreeView 
              persons={persons}
              setPersons={handleSetPersons} // Pass setPersons for dnd-kit updates
              onAddPerson={handleAddPerson}
              onEditPerson={handleEditPerson}
              onSelectPerson={handleSelectPerson}
              selectedPersonId={selectedPersonId}
            />
          </div>
          
          <div className="md:w-1/4 p-4 bg-gray-50 overflow-y-auto">
            <InfoPanel 
              person={selectedPerson}
              onEdit={handleEditPerson}
              onDelete={handleDeletePerson}
            />
          </div>
        </div>
      </main>
      
      {showForm && (
        <PersonForm 
          person={editingPerson}
          onSave={handleSavePerson}
          onCancel={() => {
            setShowForm(false);
            setEditingPerson(undefined);
          }}
          availableParents={persons.filter(p =>
            !editingPerson || p.id !== editingPerson.id
          )}
        />
      )}
    </div>
  );
};

export default FamilyTreeContainer;