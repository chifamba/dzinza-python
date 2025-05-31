import React, { useState, useEffect } from 'react';
import { Person, FamilyTreeState } from '../types';
import FamilyTreeView from './FamilyTreeView';
import PersonForm from './PersonForm';
import Header from './Header';
import InfoPanel from './InfoPanel';
import LeftNavPanel from './LeftNavPanel';
import { getFamilyTree, addPerson, updatePerson, deletePerson } from '../api/familyTreeService';

const FamilyTreeContainer: React.FC = () => {
  const [state, setState] = useState<FamilyTreeState>({
    persons: [],
    selectedPersonId: null,
  });
  
  const [showForm, setShowForm] = useState(false);
  const [editingPerson, setEditingPerson] = useState<Person | undefined>(undefined);
  
  // Fetch initial data
  useEffect(() => {
    const loadData = async () => {
      const persons = await getFamilyTree();
      setState(prev => ({ ...prev, persons }));
    };
    
    loadData();
  }, []);
  
  const handleAddPerson = (parentId?: string) => {
    setEditingPerson(undefined);
    if (parentId) {
      // Find the parent to get their last name
      const parent = state.persons.find(p => p.id === parentId);
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
    const person = state.persons.find(p => p.id === personId);
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
        setState(prev => ({
          ...prev,
          persons: prev.persons.filter(p => p.id !== personId),
          selectedPersonId: prev.selectedPersonId === personId ? null : prev.selectedPersonId,
        }));
      }
    }
  };
  
  const handleSavePerson = async (data: Partial<Person>) => {
    if (editingPerson?.id) {
      // Update existing person
      const updated = await updatePerson(editingPerson.id, data);
      if (updated) {
        setState(prev => ({
          ...prev,
          persons: prev.persons.map(p => 
            p.id === editingPerson.id ? { ...p, ...data } : p
          ),
        }));
      }
    } else {
      // Add new person
      const newPerson = await addPerson(data as Omit<Person, 'id'>);
      if (newPerson) {
        setState(prev => ({
          ...prev,
          persons: [...prev.persons, newPerson],
        }));
      }
    }
    
    setShowForm(false);
    setEditingPerson(undefined);
  };
  
  const handleSelectPerson = (personId: string) => {
    setState(prev => ({ ...prev, selectedPersonId: personId }));
  };
  
  const selectedPerson = state.selectedPersonId 
    ? state.persons.find(p => p.id === state.selectedPersonId) || null
    : null;
  
  return (
    <div className="flex flex-col h-screen">
      <Header onAddPerson={() => handleAddPerson()} />
      
      <main className="flex-1 flex overflow-hidden">
        <LeftNavPanel
          persons={state.persons}
          onPersonSelect={handleSelectPerson}
          onAddPerson={() => handleAddPerson()}
          selectedPersonId={state.selectedPersonId}
        />
        
        <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
          <div className="md:w-3/4 h-full overflow-hidden relative">
            <FamilyTreeView 
              persons={state.persons}
              onAddPerson={handleAddPerson}
              onEditPerson={handleEditPerson}
              onSelectPerson={handleSelectPerson}
              selectedPersonId={state.selectedPersonId}
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
          availableParents={state.persons.filter(p => 
            !editingPerson || p.id !== editingPerson.id
          )}
        />
      )}
    </div>
  );
};

export default FamilyTreeContainer;