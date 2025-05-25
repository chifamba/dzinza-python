import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { useAuth } from '../context/AuthContext';

function AddExistingPersonToTreePage() {
  const { activeTreeId } = useAuth();
  const navigate = useNavigate();
  const [globalPeople, setGlobalPeople] = useState([]);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedPersonId, setSelectedPersonId] = useState('');

  // Fetch all global people not already in this tree
  useEffect(() => {
    const fetchGlobalPeople = async () => {
      if (!activeTreeId) {
        setError("No active tree selected. Please select a tree from the dashboard.");
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);
      
      try {
        // Use the new API method to fetch global people not in the current tree
        const searchParams = searchTerm ? { search_term: searchTerm } : {};
        const data = await api.getGlobalPeopleNotInTree(activeTreeId, searchParams);
        setGlobalPeople(Array.isArray(data.items) ? data.items : []);
      } catch (err) {
        console.error("Failed to fetch global people:", err);
        setError("Failed to load people. Please try again later.");
      } finally {
        setLoading(false);
      }
    };

    fetchGlobalPeople();
  }, [activeTreeId, searchTerm]);

  const handleAddToTree = async () => {
    if (!selectedPersonId || !activeTreeId) {
      setError("Please select a person and ensure you have an active tree.");
      return;
    }

    setAdding(true);
    setError(null);
    setSuccess(null);

    try {
      await api.addPersonToTree(selectedPersonId, activeTreeId);
      setSuccess("Person successfully added to tree!");
      
      // Reset selection
      setSelectedPersonId('');
      
      // Optional: navigate back to tree visualization or refresh global people list
      setTimeout(() => {
        navigate('/dashboard');
      }, 2000);
    } catch (err) {
      console.error("Failed to add person to tree:", err);
      setError(err.response?.data?.message || err.message || "Failed to add person to tree");
    } finally {
      setAdding(false);
    }
  };

  // Filter people based on search term
  const filteredPeople = globalPeople.filter(person => {
    const fullName = `${person.first_name || ''} ${person.last_name || ''}`.toLowerCase();
    return fullName.includes(searchTerm.toLowerCase());
  });

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Add Existing Person to Tree</h1>
      
      {!activeTreeId && (
        <div className="bg-yellow-100 p-4 rounded mb-4">
          <p>Please select an active tree from the dashboard first.</p>
        </div>
      )}
      
      {error && (
        <div className="bg-red-100 p-4 rounded mb-4">
          <p className="text-red-700">{error}</p>
        </div>
      )}
      
      {success && (
        <div className="bg-green-100 p-4 rounded mb-4">
          <p className="text-green-700">{success}</p>
        </div>
      )}
      
      <div className="mb-4">
        <label htmlFor="search" className="block mb-2">Search for People</label>
        <input
          type="text"
          id="search"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Search by name..."
          className="w-full p-2 border rounded"
        />
      </div>
      
      {loading ? (
        <p>Loading people...</p>
      ) : (
        <>
          {filteredPeople.length === 0 ? (
            <p>No people found. Try a different search term.</p>
          ) : (
            <div className="mb-4">
              <label htmlFor="person-select" className="block mb-2">Select Person</label>
              <select
                id="person-select"
                value={selectedPersonId}
                onChange={(e) => setSelectedPersonId(e.target.value)}
                className="w-full p-2 border rounded"
              >
                <option value="">-- Select a Person --</option>
                {filteredPeople.map(person => (
                  <option key={person.id} value={person.id}>
                    {`${person.first_name || ''} ${person.last_name || ''}`}
                  </option>
                ))}
              </select>
            </div>
          )}
          
          <div className="flex justify-end">
            <button
              onClick={() => navigate(-1)}
              className="mr-2 px-4 py-2 bg-gray-200 rounded"
            >
              Cancel
            </button>
            <button
              onClick={handleAddToTree}
              disabled={!selectedPersonId || adding}
              className="px-4 py-2 bg-blue-500 text-white rounded disabled:bg-blue-300"
            >
              {adding ? "Adding..." : "Add to Tree"}
            </button>
          </div>
        </>
      )}
    </div>
  );
}

export default AddExistingPersonToTreePage;
