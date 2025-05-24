import axios from 'axios';

const BASE_URL = 'http://localhost:8090/api';

const api = {
  // --- Tree Management ---
  createTree: async (treeData) => {
    const response = await axios.post(`${BASE_URL}/trees`, treeData, {
      withCredentials: true,
    });
    return response.data;
  },

  updateTree: async (treeId, treeData) => {
    const response = await axios.put(`${BASE_URL}/trees/${treeId}`, treeData, {
      withCredentials: true,
    });
    return response.data;
  },

  getUserTrees: async () => {
    const response = await axios.get(`${BASE_URL}/trees`, {
      withCredentials: true,
    });
    return response.data;
  },

  setActiveTree: async (treeId) => {
    const response = await axios.put(
      `${BASE_URL}/session/active_tree`,
      { tree_id: treeId },
      { withCredentials: true }
    );
    return response.data;
  },

  // --- Media Endpoints ---
  uploadProfilePicture: async (personId, file) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await axios.post(
      `${BASE_URL}/people/${personId}/profile_picture`,
      formData,
      {
        withCredentials: true,
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  },

  deleteProfilePicture: async (personId) => {
    await axios.delete(`${BASE_URL}/people/${personId}/profile_picture`, {
      withCredentials: true,
    });
    return { message: 'Profile picture deleted successfully' };
  },

  // --- Tree Media Endpoints ---
  uploadTreeCoverImage: async (treeId, file) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await axios.post(
      `${BASE_URL}/trees/${treeId}/cover_image`,
      formData,
      {
        withCredentials: true,
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  },

  deleteTreeCoverImage: async (treeId) => {
    await axios.delete(`${BASE_URL}/trees/${treeId}/cover_image`, {
      withCredentials: true,
    });
    return { message: 'Tree cover image deleted successfully' };
  },
}

export default api;