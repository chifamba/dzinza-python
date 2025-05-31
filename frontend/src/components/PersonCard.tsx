import React from 'react';
import { Person } from '../types';
import { UserCircle } from 'lucide-react';
import { getDefaultImage } from '../utils/defaultImages';

interface PersonCardProps {
  person: Person;
  onAddChild?: () => void;
  onEdit?: () => void;
  onSelect?: () => void;
  selected?: boolean;
}

const PersonCard: React.FC<PersonCardProps> = ({ 
  person, 
  onAddChild, 
  onEdit, 
  onSelect,
  selected = false
}) => {
  const colorClasses = {
    blue: 'bg-sky-100 border-sky-300',
    green: 'bg-lime-100 border-lime-300',
    orange: 'bg-amber-100 border-amber-300',
    pink: 'bg-rose-100 border-rose-300',
  };
  
  const colorClass = person.color ? colorClasses[person.color] : 'bg-gray-100 border-gray-300';
  const displayName = person.name || `${person.firstName || ''} ${person.lastName || ''}`.trim();
  
  // Format display name with maiden name for female persons
  const fullDisplayName = (() => {
    if (person.gender === 'female' && person.maidenName) {
      // Only show abbreviated née format on cards due to space constraints
      return `${person.firstName || ''} ${person.lastName || ''} (née ${person.maidenName})`.trim();
    }
    return displayName;
  })();
  
  const getProfileImage = () => {
    if (person.profilePictureUrl) {
      return person.profilePictureUrl;
    }
    if (person.photo) { // Legacy field as fallback
      return person.photo;
    }
    if (person.category) {
      return getDefaultImage(person.category);
    }
    return `https://via.placeholder.com/40?text=${displayName.charAt(0)}`;
  };

  return (
    <div 
      className={`relative w-32 h-16 rounded-md border-2 p-2 cursor-pointer transition-all 
      ${colorClass} ${selected ? 'ring-2 ring-offset-2 ring-blue-500' : ''}`}
      onClick={onSelect}
    >
      <div className="flex items-center space-x-2">
        <div className="relative">
          {person.hasImage || person.category || person.profilePictureUrl ? (
            <div className="w-10 h-10 rounded-full overflow-hidden border border-gray-300">
              <img 
                src={getProfileImage()}
                alt={fullDisplayName}
                className="w-full h-full object-cover"
              />
            </div>
          ) : (
            <UserCircle className="w-10 h-10 text-gray-500" />
          )}
          <span className="absolute bottom-0 right-0 w-3 h-3 bg-white rounded-full flex items-center justify-center cursor-pointer"
                onClick={(e) => { e.stopPropagation(); onEdit?.(); }}>
            <span className="text-xs">✏️</span>
          </span>
        </div>
        <div className="flex-1 overflow-hidden">
          <p className="text-sm font-medium truncate" title={fullDisplayName}>{displayName}</p>
        </div>
      </div>
      
      {!person.isPlaceholder && (
        <button 
          className="absolute bottom-0 left-1/2 transform -translate-x-1/2 translate-y-1/2 w-5 h-5 bg-white rounded-full border border-gray-300 flex items-center justify-center hover:bg-gray-100 transition-colors"
          onClick={(e) => { e.stopPropagation(); onAddChild?.(); }}
        >
          <span className="text-xs">+</span>
        </button>
      )}
    </div>
  );
};

export default PersonCard;