import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';

// Assuming RelationshipTypeEnum values are needed for the dropdown.
// These could be imported from a shared constants file or defined here.
const relationshipTypes = [
  { value: 'married_to', label: 'Married To' },
  { value: 'parent_of', label: 'Parent Of' },
  { value: 'child_of', label: 'Child Of' },
  { value: 'sibling_of', label: 'Sibling Of' },
  { value: 'engaged_to', label: 'Engaged To' },
  { value: 'divorced_from', label: 'Divorced From' },
  { value: 'partner_of', label: 'Partner Of' },
  { value: 'friend_of', label: 'Friend Of' },
  { value: 'colleague_of', label: 'Colleague Of' },
  { value: 'acquaintance_of', label: 'Acquaintance Of' },
  // Add other types as defined in your RelationshipTypeEnum
];

const RelationshipTypeModal = ({ isOpen, onClose, onSubmit, sourceNode, targetNode }) => {
  const [selectedRelationshipType, setSelectedRelationshipType] = useState('');

  useEffect(() => {
    // Reset selected type when modal is reopened, especially if different nodes
    if (isOpen) {
      setSelectedRelationshipType('');
    }
  }, [isOpen]);

  if (!isOpen) {
    return null;
  }

  const handleSubmit = () => {
    if (selectedRelationshipType) {
      onSubmit({ relationshipType: selectedRelationshipType });
    }
  };

  const sourceLabel = sourceNode?.data?.label || sourceNode?.id || 'Source';
  const targetLabel = targetNode?.data?.label || targetNode?.id || 'Target';

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex justify-center items-center">
      <div className="relative mx-auto p-5 border w-full max-w-md shadow-lg rounded-md bg-white">
        <div className="mt-3 text-center">
          <h3 className="text-lg leading-6 font-medium text-gray-900 mb-2">
            Create Relationship
          </h3>
          <p className="text-sm text-gray-700 mb-1">
            From: <strong>{sourceLabel}</strong>
          </p>
          <p className="text-sm text-gray-700 mb-4">
            To: <strong>{targetLabel}</strong>
          </p>

          <div className="mb-4">
            <label htmlFor="relationshipType" className="block text-sm font-medium text-gray-700 mb-1">
              Relationship Type:
            </label>
            <select
              id="relationshipType"
              name="relationshipType"
              value={selectedRelationshipType}
              onChange={(e) => setSelectedRelationshipType(e.target.value)}
              className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
            >
              <option value="" disabled>Select a type</option>
              {relationshipTypes.map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </div>

          <div className="items-center px-4 py-3 space-x-4">
            <button
              onClick={handleSubmit}
              disabled={!selectedRelationshipType}
              className="px-4 py-2 bg-indigo-600 text-white text-base font-medium rounded-md w-auto hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-gray-300"
            >
              Save Relationship
            </button>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-200 text-gray-800 text-base font-medium rounded-md w-auto hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

RelationshipTypeModal.propTypes = {
  isOpen: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  onSubmit: PropTypes.func.isRequired,
  sourceNode: PropTypes.object, // Can be null initially
  targetNode: PropTypes.object, // Can be null initially
};

export default RelationshipTypeModal;
