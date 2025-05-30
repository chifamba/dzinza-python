import axios from 'axios';

// Corrected BASE_URL
const BASE_URL = 'http://localhost:8090/api'; // Use localhost for local development

const api = {
  login: async (username, password) => {
    // Added credentials to ensure cookies are sent
    const response = await axios.post(`${BASE_URL}/login`, { username, password }, { withCredentials: true });
    return response.data;
  },

  register: async (username, password, email, fullName) => {
    // Added email and fullName for registration based on backend requirements
    const response = await axios.post(`${BASE_URL}/register`, { username, password, email, full_name: fullName }, { withCredentials: true });
    return response.data;
  },

  // --- Added withCredentials to all authenticated requests ---

  // Pass activeTreeId to requests that operate within a specific tree
  getPerson: async (id, activeTreeId) => {
    // Ensure tree_id is passed as a query parameter or header if needed by backend,
    // or rely on the active_tree_id being set in the session on the backend
    // based on the /api/session/active_tree endpoint.
    // Assuming backend uses session['active_tree_id'] from set_active_tree endpoint
    const response = await axios.get(`${BASE_URL}/people/${id}`, { withCredentials: true });
    return response.data;
  },

  // --- NEW Person-Tree Association API Calls ---
  addPersonToTree: async (personId, treeId) => {
    const response = await axios.post(`${BASE_URL}/trees/${treeId}/persons`, 
      { person_id: personId }, 
      { withCredentials: true });
    return response.data;
  },

  removePersonFromTree: async (personId, treeId) => {
    await axios.delete(`${BASE_URL}/trees/${treeId}/persons/${personId}`, 
      { withCredentials: true });
    return { message: 'Person removed from tree successfully' };
  },

  createPerson: async (personData, activeTreeId) => {
    // Backend expects tree_id to be associated with the request,
    // likely via the active_tree_id in the session.
    const response = await axios.post(`${BASE_URL}/people`, personData, { withCredentials: true });
    return response.data;
  },

  updatePerson: async (id, personData, activeTreeId) => {
    // Backend expects tree_id via session
    const response = await axios.put(`${BASE_URL}/people/${id}`, personData, { withCredentials: true });
    return response.data;
  },

  deletePerson: async (id, activeTreeId) => {
    // Backend expects tree_id via session
    // DELETE requests might not return data, handle accordingly
    await axios.delete(`${BASE_URL}/people/${id}`, { withCredentials: true });
    // Return status or confirmation if needed, axios throws error on non-2xx status
    return { message: 'Person deleted successfully' };
  },

  getAllPeople: async (activeTreeId) => {
    // Backend expects tree_id via session
    const response = await axios.get(`${BASE_URL}/people`, { withCredentials: true });
    return response.data;
  },

  getRelationship: async (id, activeTreeId) => {
    // Backend expects tree_id via session
    const response = await axios.get(`${BASE_URL}/relationships/${id}`, { withCredentials: true });
    return response.data;
  },

  getAllRelationships: async (activeTreeId) => {
    // Backend expects tree_id via session
    const response = await axios.get(`${BASE_URL}/relationships`, { withCredentials: true });
    return response.data;
  },

  createRelationship: async (relationshipData, activeTreeId) => {
    // Backend expects tree_id via session
    const response = await axios.post(`${BASE_URL}/relationships`, relationshipData, { withCredentials: true });
    return response.data;
  },

  updateRelationship: async (id, relationshipData, activeTreeId) => {
    // Backend expects tree_id via session
    const response = await axios.put(`${BASE_URL}/relationships/${id}`, relationshipData, { withCredentials: true });
    return response.data;
  },

  deleteRelationship: async (id, activeTreeId) => {
    // Backend expects tree_id via session
    // DELETE requests might not return data
    await axios.delete(`${BASE_URL}/relationships/${id}`, { withCredentials: true });
    return { message: 'Relationship deleted successfully' };
  },

  // --- Session and Tree Data Endpoints ---
  getSession: async () => {
    // This endpoint now returns active_tree_id in the user object
    const response = await axios.get(`${BASE_URL}/session`, { withCredentials: true });
    return response.data;
  },

  logout: async () => {
    const response = await axios.post(`${BASE_URL}/logout`, {}, { withCredentials: true });
    return response.data;
  },

  getTreeData: async (activeTreeId, page = 1, perPage = null) => {
    // Backend expects tree_id via session, page and perPage as query params
    // If perPage is null, don't include it in query params to use backend default
    const queryParams = new URLSearchParams({ page });
    if (perPage !== null) {
      queryParams.append('per_page', perPage);
    }
    
    const response = await axios.get(`${BASE_URL}/tree_data?${queryParams}`, { withCredentials: true });
    return response.data;
  },

  // --- NEW Admin API Calls ---
  getAllUsers: async () => {
    const response = await axios.get(`${BASE_URL}/users`, { withCredentials: true });
    return response.data;
  },

  deleteUser: async (userId) => {
    await axios.delete(`${BASE_URL}/users/${userId}`, { withCredentials: true });
    return { message: 'User deleted successfully' };
  },

  setUserRole: async (userId, role) => {
    const response = await axios.put(`${BASE_URL}/users/${userId}/role`, { role }, { withCredentials: true });
    return response.data;
  },

  // --- NEW Global People API Call ---
  getGlobalPeopleNotInTree: async (treeId, searchParams = {}) => {
    // Build query string from searchParams
    const queryParams = new URLSearchParams({
      not_in_tree: treeId,
      ...searchParams
    });
    
    const response = await axios.get(`${BASE_URL}/global-people?${queryParams}`, { withCredentials: true });
    return response.data;
  },

  // --- NEW Password Reset API Calls ---
  requestPasswordReset: async (email) => {
    const response = await axios.post(`${BASE_URL}/request-password-reset`, { email });
    return response.data;
  },

  resetPassword: async (token, newPassword) => {
    const response = await axios.post(`${BASE_URL}/reset-password/${token}`, { new_password: newPassword });
    return response.data;
  },

   // --- NEW Tree Management API Calls ---
   createTree: async (treeData) => {
        const response = await axios.post(`${BASE_URL}/trees`, treeData, { withCredentials: true });
        return response.data;
   },

   getUserTrees: async () => {
        const response = await axios.get(`${BASE_URL}/trees`, { withCredentials: true });
        return response.data;
   },

   setActiveTree: async (treeId) => {
        const response = await axios.put(`${BASE_URL}/session/active_tree`, { tree_id: treeId }, { withCredentials: true });
        return response.data;
   },
    // Add other tree endpoints (get, update, delete) if needed based on backend
    // getTree: async (treeId) => { ... },
    // updateTree: async (treeId, treeData) => { ... },
    // deleteTree: async (treeId) => { ... },
};

export default api;
