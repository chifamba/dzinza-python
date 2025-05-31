import React from 'react';
import { Person } from '../types';
import { UserCircle, Edit2, Trash2 } from 'lucide-react';

interface InfoPanelProps {
  person: Person | null;
  onEdit: (personId: string) => void;
  onDelete: (personId: string) => void;
}

const InfoPanel: React.FC<InfoPanelProps> = ({ person, onEdit, onDelete }) => {
  if (!person) {
    return (
      <div className="p-4 bg-white shadow-md rounded-lg">
        <p className="text-gray-500 italic">Select a person to view details</p>
      </div>
    );
  }

  const displayName = person.name || `${person.firstName || ''} ${person.lastName || ''}`.trim();
  
  // Format a more complete display name including maiden name if present
  const fullDisplayName = (() => {
    if (person.gender === 'female' && person.maidenName) {
      return `${person.firstName || ''} ${person.lastName || ''} (née ${person.maidenName})`.trim();
    }
    return displayName;
  })();
  
  return (
    <div className="p-4 bg-white shadow-md rounded-lg">
      <div className="flex items-start space-x-4">
        <div className="flex-shrink-0">
          {person.hasImage ? (
            <div className="w-16 h-16 rounded-full overflow-hidden border border-gray-300">
              <img 
                src={person.photo || person.profilePictureUrl || `https://via.placeholder.com/64?text=${displayName.charAt(0)}`} 
                alt={fullDisplayName}
                className="w-full h-full object-cover"
              />
            </div>
          ) : (
            <UserCircle className="w-16 h-16 text-gray-500" />
          )}
        </div>
        
        <div className="flex-1">
          <div className="flex justify-between">
            <h3 className="text-lg font-semibold">{fullDisplayName}</h3>
            <div className="flex space-x-2">
              <button 
                onClick={() => onEdit(person.id)}
                className="p-1 text-gray-500 hover:text-blue-500"
              >
                <Edit2 className="w-4 h-4" />
              </button>
              <button 
                onClick={() => onDelete(person.id)}
                className="p-1 text-gray-500 hover:text-red-500"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
          
          <div className="mt-4 space-y-2 text-sm text-gray-600">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {person.firstName && (
                <div>
                  <span className="font-medium">First Name:</span> {person.firstName}
                </div>
              )}
              
              {person.middleNames && (
                <div>
                  <span className="font-medium">Middle Names:</span> {person.middleNames}
                </div>
              )}
              
              {person.lastName && (
                <div>
                  <span className="font-medium">Last Name:</span> {person.lastName}
                </div>
              )}
              
              {person.maidenName && (
                <div>
                  <span className="font-medium">Née:</span> {person.maidenName}
                </div>
              )}
              
              {person.nickname && (
                <div>
                  <span className="font-medium">Nickname:</span> {person.nickname}
                </div>
              )}
              
              {person.gender && (
                <div>
                  <span className="font-medium">Gender:</span> {person.gender}
                </div>
              )}
              
              {person.birthDate && (
                <div>
                  <span className="font-medium">Birth Date:</span> {new Date(person.birthDate).toLocaleDateString()}
                  {person.birthDateApprox && ' (approximate)'}
                </div>
              )}
              
              {person.birthPlace && (
                <div>
                  <span className="font-medium">Birth Place:</span> {person.birthPlace}
                </div>
              )}
              
              {!person.isLiving && person.deathDate && (
                <div>
                  <span className="font-medium">Death Date:</span> {new Date(person.deathDate).toLocaleDateString()}
                  {person.deathDateApprox && ' (approximate)'}
                </div>
              )}
              
              {!person.isLiving && person.deathPlace && (
                <div>
                  <span className="font-medium">Death Place:</span> {person.deathPlace}
                </div>
              )}
              
              {!person.isLiving && person.burialPlace && (
                <div>
                  <span className="font-medium">Burial Place:</span> {person.burialPlace}
                </div>
              )}
              
              <div>
                <span className="font-medium">Status:</span> {person.isLiving ? 'Living' : 'Deceased'}
              </div>
              
              {person.parentId && (
                <div>
                  <span className="font-medium">Parent ID:</span> {person.parentId}
                </div>
              )}
              
              {person.spouseId && (
                <div>
                  <span className="font-medium">Spouse ID:</span> {person.spouseId}
                </div>
              )}
            </div>
            
            {person.notes && (
              <div className="mt-3">
                <h4 className="font-medium mb-1">Notes</h4>
                <p className="text-gray-700 whitespace-pre-wrap">{person.notes}</p>
              </div>
            )}
            
            {person.biography && (
              <div className="mt-3">
                <h4 className="font-medium mb-1">Biography</h4>
                <p className="text-gray-700 whitespace-pre-wrap">{person.biography}</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default InfoPanel;