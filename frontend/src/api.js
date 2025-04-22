import axios from 'axios';

const BASE_URL = 'http://localhost:5000/api';

const api = {
  login: async (username, password) => {
    const response = await axios.post(`${BASE_URL}/login`, { username, password });
    return response.data;
  },

  register: async (username, password) => {
    const response = await axios.post(`${BASE_URL}/register`, { username, password });
    return response.data;
  },

  getPerson: async (id) => {
    const response = await axios.get(`${BASE_URL}/people/${id}`);
    return response.data;
  },

  createPerson: async (personData) => {
    const response = await axios.post(`${BASE_URL}/people`, personData);
    return response.data;
  },

  updatePerson: async (id, personData) => {
    const response = await axios.put(`${BASE_URL}/people/${id}`, personData);
    return response.data;
  },

  deletePerson: async (id) => {
    const response = await axios.delete(`${BASE_URL}/people/${id}`);
    return response.data;
  },

  getAllPeople: async () => {
    const response = await axios.get(`${BASE_URL}/people`);
    return response.data;
  },

  getRelationship: async (id) => {
    const response = await axios.get(`${BASE_URL}/relationships/${id}`);
    return response.data;
  },
  
  getAllRelationships: async () => {
    const response = await axios.get(`${BASE_URL}/relationships`);
    return response.data;
  },

  createRelationship: async (relationshipData) => {
    const response = await axios.post(`${BASE_URL}/relationships`, relationshipData);
    return response.data;
  },

  updateRelationship: async (id, relationshipData) => {
    const response = await axios.put(`${BASE_URL}/relationships/${id}`, relationshipData);
    return response.data;
  },

  deleteRelationship: async (id) => {
    const response = await axios.delete(`${BASE_URL}/relationships/${id}`);
    return response.data;
  },
};

export default api;