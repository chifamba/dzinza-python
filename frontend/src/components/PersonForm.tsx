import React, { useState, useEffect, ChangeEvent, FormEvent } from 'react';
import { Person } from '../types';

interface PersonFormProps {
  person?: Person;
  onSave: (data: Partial<Person>) => void;
  onCancel: () => void;
  availableParents: Person[];
}

interface ChildData {
  id: string;
  name: string;
  firstName: string;
  lastName: string;
}

const PersonForm: React.FC<PersonFormProps> = ({
  person,
  onSave,
  onCancel,
  availableParents,
}) => {
  const [formData, setFormData] = useState<Partial<Person>>({
    firstName: '',
    middleNames: '',
    lastName: '',
    gender: '',
    birthDate: '',
    birthPlace: '',
    isLiving: true,
    // Legacy fields
    name: '',
    color: 'blue',
    parentId: undefined,
    hasImage: false,
    category: undefined,
  });

  const [showAdvanced, setShowAdvanced] = useState(false);
  const [children, setChildren] = useState<ChildData[]>([]);
  const [newChildFirstName, setNewChildFirstName] = useState('');
  const [newChildLastName, setNewChildLastName] = useState('');
  const [useCustomLastName, setUseCustomLastName] = useState(false);

  useEffect(() => {
    if (person) {
      setFormData({
        // New fields
        firstName: person.firstName || '',
        middleNames: person.middleNames || '',
        lastName: person.lastName || '',
        maidenName: person.maidenName || '',
        nickname: person.nickname || '',
        gender: person.gender || '',
        birthDate: person.birthDate || '',
        birthDateApprox: person.birthDateApprox || false,
        birthPlace: person.birthPlace || '',
        deathDate: person.deathDate || '',
        deathDateApprox: person.deathDateApprox || false,
        deathPlace: person.deathPlace || '',
        burialPlace: person.burialPlace || '',
        isLiving: person.isLiving !== false, // Default to true if undefined
        notes: person.notes || '',
        biography: person.biography || '',
        
        // Legacy fields
        name: person.name || `${person.firstName || ''} ${person.lastName || ''}`.trim(),
        color: person.color || 'blue',
        parentId: person.parentId,
        hasImage: person.hasImage,
        category: person.category,
      });
      
      // Set the default last name for children
      if (person.lastName) {
        setNewChildLastName(person.lastName);
      }
    }
  }, [person]);

  const handleChange = (
    e: ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const { name, value, type } = e.target;
    
    if (type === 'checkbox') {
      const checkbox = e.target as HTMLInputElement;
      setFormData((prev) => ({
        ...prev,
        [name]: checkbox.checked,
      }));
    } else {
      setFormData((prev) => ({
        ...prev,
        [name]: value,
      }));
    }

    // Keep the legacy name field in sync with first and last names
    if (name === 'firstName' || name === 'lastName') {
      const firstName = name === 'firstName' ? value : formData.firstName;
      const lastName = name === 'lastName' ? value : formData.lastName;
      setFormData((prev) => ({
        ...prev,
        name: `${firstName || ''} ${lastName || ''}`.trim()
      }));
      
      // Also update the default last name for children
      if (name === 'lastName' && !useCustomLastName) {
        setNewChildLastName(value);
      }
    }
    
    // If gender changes, handle maiden name field visibility
    if (name === 'gender' && value === 'female') {
      // No action needed, UI will show the field conditionally
    }
  };

  const handleAddChild = () => {
    if (newChildFirstName.trim()) {
      // Determine the last name to use
      let lastName = newChildLastName.trim();
      if (!useCustomLastName && formData.lastName) {
        lastName = formData.lastName;
      }
      
      const fullName = `${newChildFirstName} ${lastName}`.trim();
      
      setChildren([
        ...children, 
        { 
          id: Date.now().toString(), 
          name: fullName,
          firstName: newChildFirstName.trim(),
          lastName: lastName
        }
      ]);
      
      setNewChildFirstName('');
      setNewChildLastName('');
    }
  };

  const handleRemoveChild = (id: string) => {
    setChildren(children.filter((child) => child.id !== id));
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    
    // Process children data if needed
    // Note: In a real implementation, you'd need to create the children as separate
    // persons and establish the parent-child relationship properly
    
    onSave(formData);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-lg p-6 w-full max-w-3xl max-h-[90vh] overflow-y-auto">
        <h2 className="text-xl font-semibold mb-4">{person ? 'Edit Person' : 'Add New Person'}</h2>
        
        <form onSubmit={handleSubmit}>
          <div className="mb-6 p-4 bg-gray-50 rounded-lg">
            <h3 className="text-lg font-medium mb-4">Essential Information</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">First Name *</label>
                <input
                  type="text"
                  name="firstName"
                  value={formData.firstName || ''}
                  onChange={handleChange}
                  className="w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Middle Names</label>
                <input
                  type="text"
                  name="middleNames"
                  value={formData.middleNames || ''}
                  onChange={handleChange}
                  className="w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Last Name *</label>
                <input
                  type="text"
                  name="lastName"
                  value={formData.lastName || ''}
                  onChange={handleChange}
                  className="w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Gender</label>
                <select
                  name="gender"
                  value={formData.gender || ''}
                  onChange={handleChange}
                  className="w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Select Gender</option>
                  <option value="male">Male</option>
                  <option value="female">Female</option>
                  <option value="other">Other</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Date of Birth</label>
                <input
                  type="date"
                  name="birthDate"
                  value={formData.birthDate || ''}
                  onChange={handleChange}
                  className="w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Place of Birth</label>
                <input
                  type="text"
                  name="birthPlace"
                  value={formData.birthPlace || ''}
                  onChange={handleChange}
                  className="w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              
              <div className="md:col-span-2">
                <div className="flex items-center mb-2">
                  <input
                    type="checkbox"
                    id="isLiving"
                    name="isLiving"
                    checked={formData.isLiving || false}
                    onChange={handleChange}
                    className="mr-2"
                  />
                  <label htmlFor="isLiving" className="text-sm font-medium text-gray-700">
                    Person is Living
                  </label>
                </div>
              </div>
            </div>
          </div>
          
          <div className="mb-4">
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex items-center justify-center w-full py-2 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
            >
              <span className="mr-2">{showAdvanced ? 'Hide' : 'Show'} Advanced Details</span>
              <svg
                className={`w-4 h-4 transition-transform ${showAdvanced ? 'rotate-180' : ''}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path>
              </svg>
            </button>
          </div>
          
          {showAdvanced && (
            <div className="mb-6 p-4 bg-gray-50 rounded-lg">
              <h3 className="text-lg font-medium mb-4">Advanced Information</h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {formData.gender === 'female' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Née (Birth Last Name)
                    </label>
                    <input
                      type="text"
                      name="maidenName"
                      value={formData.maidenName || ''}
                      onChange={handleChange}
                      className="w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      The last name at birth, before marriage
                    </p>
                  </div>
                )}
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Nickname</label>
                  <input
                    type="text"
                    name="nickname"
                    value={formData.nickname || ''}
                    onChange={handleChange}
                    className="w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Date of Death</label>
                  <input
                    type="date"
                    name="deathDate"
                    value={formData.deathDate || ''}
                    onChange={handleChange}
                    disabled={formData.isLiving}
                    className="w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-400"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Place of Death</label>
                  <input
                    type="text"
                    name="deathPlace"
                    value={formData.deathPlace || ''}
                    onChange={handleChange}
                    disabled={formData.isLiving}
                    className="w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-400"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Burial Place</label>
                  <input
                    type="text"
                    name="burialPlace"
                    value={formData.burialPlace || ''}
                    onChange={handleChange}
                    disabled={formData.isLiving}
                    className="w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-400"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Parent</label>
                  <select
                    name="parentId"
                    value={formData.parentId || ''}
                    onChange={handleChange}
                    className="w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">No Parent (Root)</option>
                    {availableParents.map((parent) => (
                      <option key={parent.id} value={parent.id}>
                        {parent.name || `${parent.firstName || ''} ${parent.lastName || ''}`.trim()}
                      </option>
                    ))}
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Spouse</label>
                  <select
                    name="spouseId"
                    value={formData.spouseId || ''}
                    onChange={handleChange}
                    className="w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">No Spouse</option>
                    {availableParents.map((parent) => (
                      <option key={parent.id} value={parent.id}>
                        {parent.name || `${parent.firstName || ''} ${parent.lastName || ''}`.trim()}
                      </option>
                    ))}
                  </select>
                </div>
                
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Children</label>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mb-2">
                    <div className="md:col-span-1">
                      <input
                        type="text"
                        value={newChildFirstName}
                        onChange={(e) => setNewChildFirstName(e.target.value)}
                        placeholder="First name"
                        className="w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <div className="md:col-span-1">
                      <input
                        type="text"
                        value={newChildLastName}
                        onChange={(e) => setNewChildLastName(e.target.value)}
                        placeholder={useCustomLastName ? "Last name" : `Auto: ${formData.lastName || 'Parent\'s last name'}`}
                        disabled={!useCustomLastName}
                        className="w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
                      />
                    </div>
                    <div className="md:col-span-1">
                      <button
                        type="button"
                        onClick={handleAddChild}
                        className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        Add Child
                      </button>
                    </div>
                  </div>
                  
                  <div className="flex items-center mb-3 mt-1">
                    <input
                      type="checkbox"
                      id="useCustomLastName"
                      checked={useCustomLastName}
                      onChange={(e) => setUseCustomLastName(e.target.checked)}
                      className="mr-2"
                    />
                    <label htmlFor="useCustomLastName" className="text-sm text-gray-700">
                      Use custom last name (otherwise inherit from parent)
                    </label>
                  </div>
                  
                  {children.length > 0 && (
                    <ul className="mt-2 border border-gray-200 rounded-md divide-y">
                      {children.map((child) => (
                        <li key={child.id} className="flex justify-between items-center p-2">
                          <span>
                            <strong>{child.firstName}</strong> {child.lastName}
                          </span>
                          <button
                            type="button"
                            onClick={() => handleRemoveChild(child.id)}
                            className="text-red-500 hover:text-red-700"
                          >
                            Remove
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
                
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
                  <textarea
                    name="notes"
                    value={formData.notes || ''}
                    onChange={handleChange}
                    rows={3}
                    className="w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  ></textarea>
                </div>
                
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Biography</label>
                  <textarea
                    name="biography"
                    value={formData.biography || ''}
                    onChange={handleChange}
                    rows={5}
                    className="w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  ></textarea>
                </div>
                
                <div className="md:col-span-2">
                  <div className="flex items-center mb-2">
                    <input
                      type="checkbox"
                      id="hasImage"
                      name="hasImage"
                      checked={formData.hasImage || false}
                      onChange={handleChange}
                      className="mr-2"
                    />
                    <label htmlFor="hasImage" className="text-sm font-medium text-gray-700">
                      Has Custom Profile Image
                    </label>
                  </div>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                  <select
                    name="category"
                    value={formData.category || ''}
                    onChange={handleChange}
                    className="w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">No Category</option>
                    <option value="olderMale">Older Male</option>
                    <option value="olderFemale">Older Female</option>
                    <option value="adultMale">Adult Male</option>
                    <option value="adultFemale">Adult Female</option>
                    <option value="boy">Boy</option>
                    <option value="girl">Girl</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Card Color</label>
                  <select
                    name="color"
                    value={formData.color || 'blue'}
                    onChange={handleChange}
                    className="w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="blue">Blue</option>
                    <option value="green">Green</option>
                    <option value="orange">Orange</option>
                    <option value="pink">Pink</option>
                  </select>
                </div>
              </div>
            </div>
          )}
          
          <div className="flex justify-end space-x-2">
            <button
              type="button"
              onClick={onCancel}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              Save
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default PersonForm;