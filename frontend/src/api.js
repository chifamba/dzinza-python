import axios from 'axios';

// Corrected BASE_URL
const BASE_URL = 'http://localhost:8090/api'; // Ensure this matches your backend port

const api = {
  login: async (username, password) => {
    // Added credentials to ensure cookies are sent
    const response = await axios.post(`${BASE_URL}/login`, { username, password }, { withCredentials: true });
    return response.data;
  },

  register: async (username, password) => {
    const response = await axios.post(`${BASE_URL}/register`, { username, password }, { withCredentials: true });
    return response.data;
  },

  // --- Added withCredentials to all authenticated requests ---

  getPerson: async (id) => {
    const response = await axios.get(`${BASE_URL}/people/${id}`, { withCredentials: true });
    return response.data;
  },

  createPerson: async (personData) => {
    const response = await axios.post(`${BASE_URL}/people`, personData, { withCredentials: true });
    return response.data;
  },

  updatePerson: async (id, personData) => {
    const response = await axios.put(`${BASE_URL}/people/${id}`, personData, { withCredentials: true });
    return response.data;
  },

  deletePerson: async (id) => {
    // DELETE requests might not return data, handle accordingly
    await axios.delete(`${BASE_URL}/people/${id}`, { withCredentials: true });
    // Return status or confirmation if needed, axios throws error on non-2xx status
    return { message: 'Person deleted successfully' };
  },

  getAllPeople: async () => {
    const response = await axios.get(`${BASE_URL}/people`, { withCredentials: true });
    return response.data;
  },

  getRelationship: async (id) => {
    const response = await axios.get(`${BASE_URL}/relationships/${id}`, { withCredentials: true });
    return response.data;
  },

  getAllRelationships: async () => {
    const response = await axios.get(`${BASE_URL}/relationships`, { withCredentials: true });
    return response.data;
  },

  createRelationship: async (relationshipData) => {
    const response = await axios.post(`${BASE_URL}/relationships`, relationshipData, { withCredentials: true });
    return response.data;
  },

  updateRelationship: async (id, relationshipData) => {
    const response = await axios.put(`${BASE_URL}/relationships/${id}`, relationshipData, { withCredentials: true });
    return response.data;
  },

  deleteRelationship: async (id) => {
    // DELETE requests might not return data
    await axios.delete(`${BASE_URL}/relationships/${id}`, { withCredentials: true });
    return { message: 'Relationship deleted successfully' };
  },

  // --- Session and Tree Data Endpoints ---
  getSession: async () => {
    const response = await axios.get(`${BASE_URL}/session`, { withCredentials: true });
    return response.data;
  },

  logout: async () => {
    const response = await axios.post(`${BASE_URL}/logout`, {}, { withCredentials: true });
    return response.data;
  },

  getTreeData: async () => {
    const response = await axios.get(`${BASE_URL}/tree_data`, { withCredentials: true });
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

  // --- NEW Password Reset API Calls ---
  requestPasswordReset: async (email) => {
    const response = await axios.post(`${BASE_URL}/request-password-reset`, { email });
    return response.data;
  },

  resetPassword: async (token, newPassword) => {
    const response = await axios.post(`${BASE_URL}/reset-password/${token}`, { new_password: newPassword });
    return response.data;
  }

};

export default api;
