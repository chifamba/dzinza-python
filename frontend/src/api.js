import axios from 'axios';
import { ActivityEvent } from '@/lib/types';

const BASE_URL = 'http://localhost:8090/api';

const api = {
  // --- Authentication Endpoints ---
  login: async (username, password) => {
    const response = await axios.post(
      `${BASE_URL}/auth/login`,
      { username, password },
      { withCredentials: true }
    );
    return response.data;
  },

  logout: async () => {
    const response = await axios.post(
      `${BASE_URL}/auth/logout`,
      {},
      { withCredentials: true }
    );
    return response.data;
  },

  getSession: async () => {
    const response = await axios.get(
      `${BASE_URL}/auth/session`,
      { withCredentials: true }
    );
    return response.data;
  },

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

  getTreePermissions: async (treeId) => {
    const response = await axios.get(
      `${BASE_URL}/trees/${treeId}/permissions`,
      {
        withCredentials: true,
      }
    );
    return response.data;
  },

  shareTree: async (treeId, userData) => {
    const response = await axios.post(
      `${BASE_URL}/trees/${treeId}/share`,
      userData,
      {
        withCredentials: true,
      }
    );
    return response.data;
  },

  updateTreePermission: async (treeId, userId, permissionLevel) => {
    const response = await axios.put(
      `${BASE_URL}/trees/${treeId}/permissions/${userId}`,
      { permission_level: permissionLevel },
      { withCredentials: true }
    );
    return response.data;
  },

  revokeTreeAccess: async (treeId, userId) => {
    const response = await axios.delete(
      `${BASE_URL}/trees/${treeId}/permissions/${userId}`,
      {
        withCredentials: true,
      }
    );
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

  getPersonMedia: async (personId) => {
    const response = await axios.get(
      `${BASE_URL}/people/${personId}/media`,
      { withCredentials: true }
    );
    return response.data;
  },

  uploadPersonMedia: async (personId, file, metadata = {}) => {
    const formData = new FormData();
    formData.append('file', file);

    // Add metadata if provided
    if (metadata.description) {
      formData.append('description', metadata.description);
    }

    if (metadata.tags && Array.isArray(metadata.tags)) {
      formData.append('tags', JSON.stringify(metadata.tags));
    }

    const response = await axios.post(
      `${BASE_URL}/people/${personId}/media`,
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

  deletePersonMedia: async (personId, mediaId) => {
    await axios.delete(`${BASE_URL}/people/${personId}/media/${mediaId}`, {
      withCredentials: true,
    });
    return { message: 'Media deleted successfully' };
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

  // --- Activity Endpoints ---
  getTreeActivities: async (treeId, params = {}) => {
    const response = await axios.get(
      `${BASE_URL}/trees/${treeId}/activities`,
      {
        params,
        withCredentials: true,
      }
    );
    return response.data;
  },

  addActivity: async (treeId, activityData) => {
    const response = await axios.post(
      `${BASE_URL}/trees/${treeId}/activities`,
      activityData,
      {
        withCredentials: true,
      }
    );
    return response.data;
  },

  exportTreeActivities: async (treeId, params = {}) => {
    const response = await axios.get(
      `${BASE_URL}/trees/${treeId}/activities/export`,
      {
        params,
        withCredentials: true,
        responseType: 'blob',
      }
    );
    return response;
  },
};

export default api;