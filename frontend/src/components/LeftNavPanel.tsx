import React, { useState } from 'react';
import { Search, Users, UserPlus, Settings, ChevronLeft, ChevronRight } from 'lucide-react';
import { Person } from '../types';

interface LeftNavPanelProps {
  persons: Person[];
  onPersonSelect: (personId: string) => void;
  onAddPerson: () => void;
  selectedPersonId: string | null;
}

const LeftNavPanel: React.FC<LeftNavPanelProps> = ({
  persons,
  onPersonSelect,
  onAddPerson,
  selectedPersonId,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  const filteredPersons = persons.filter(person => {
    const displayName = person.name || `${person.firstName || ''} ${person.lastName || ''}`.trim();
    return displayName.toLowerCase().includes(searchTerm.toLowerCase());
  });

  return (
    <div 
      className={`bg-white border-r border-gray-200 transition-all duration-300 flex flex-col ${
        isCollapsed ? 'w-16' : 'w-64'
      }`}
    >
      {/* Header */}
      <div className="p-4 border-b border-gray-200 flex items-center justify-between">
        {!isCollapsed && <h2 className="font-semibold text-gray-800">Family Members</h2>}
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="p-1 hover:bg-gray-100 rounded-md"
        >
          {isCollapsed ? <ChevronRight size={20} /> : <ChevronLeft size={20} />}
        </button>
      </div>

      {/* Search and Actions */}
      <div className="p-2 border-b border-gray-200">
        {!isCollapsed && (
          <div className="relative mb-2">
            <input
              type="text"
              placeholder="Search family..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-amber-500"
            />
            <Search className="absolute left-2.5 top-2 text-gray-400" size={16} />
          </div>
        )}
        
        <div className="flex justify-around">
          <button
            className="p-2 hover:bg-gray-100 rounded-md text-gray-600 flex items-center"
            title="View All"
          >
            <Users size={20} />
            {!isCollapsed && <span className="ml-2">View All</span>}
          </button>
          <button
            onClick={onAddPerson}
            className="p-2 hover:bg-gray-100 rounded-md text-gray-600 flex items-center"
            title="Add Person"
          >
            <UserPlus size={20} />
            {!isCollapsed && <span className="ml-2">Add Person</span>}
          </button>
        </div>
      </div>

      {/* Family Members List */}
      <div className="flex-1 overflow-y-auto">
        {!isCollapsed && filteredPersons.length === 0 ? (
          <p className="text-gray-500 text-sm p-4 text-center">No family members found</p>
        ) : (
          <div className="space-y-1 p-2">
            {filteredPersons.map((person) => (
              <button
                key={person.id}
                onClick={() => onPersonSelect(person.id)}
                className={`w-full text-left p-2 rounded-md transition-colors ${
                  selectedPersonId === person.id
                    ? 'bg-amber-50 text-amber-900'
                    : 'hover:bg-gray-100'
                } ${isCollapsed ? 'flex justify-center' : ''}`}
              >
                {isCollapsed ? (
                  <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center">
                    {(person.name || `${person.firstName || ''} ${person.lastName || ''}`.trim()).charAt(0)}
                  </div>
                ) : (
                  <div className="flex items-center">
                    <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center">
                      {(person.name || `${person.firstName || ''} ${person.lastName || ''}`.trim()).charAt(0)}
                    </div>
                    <span className="ml-2 text-sm">
                      {person.name || `${person.firstName || ''} ${person.lastName || ''}`.trim()}
                    </span>
                  </div>
                )}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Settings */}
      <div className="p-2 border-t border-gray-200">
        <button
          className="w-full p-2 hover:bg-gray-100 rounded-md text-gray-600 flex items-center justify-center"
          title="Settings"
        >
          <Settings size={20} />
          {!isCollapsed && <span className="ml-2">Settings</span>}
        </button>
      </div>
    </div>
  );
};

export default LeftNavPanel;